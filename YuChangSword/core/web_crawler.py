# core/web_crawler.py
import re
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
from config.ai_settings import AI_CONSTANTS
from requests.packages.urllib3.util.connection import allowed_gai_family
from config.log_config import configure_logger
import socket

# 添加DNS缓存
class DNSCacheAdapter(requests.adapters.HTTPAdapter):
    _dns_cache = {}

    def get_connection(self, url, proxies=None):
        parsed = urlparse(url)
        host = parsed.hostname
        if host in self._dns_cache:
            return super().get_connection(
                url.replace(host, self._dns_cache[host]), proxies
            )
        return super().get_connection(url, proxies)

class JSExtractor:
    def __init__(self, timeout=600, max_depth=2):
        self.session = requests.Session()
        # 优先挂载DNS缓存适配器
        self.session.mount('https://', DNSCacheAdapter())
        self.session.mount('http://', DNSCacheAdapter())
        self.timeout = timeout
        self.max_depth = max_depth
        self.visited_urls = set()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.blocklist = {
            'umeng.js', 'ga.js', 'gtm.js',
            'jquery', 'bootstrap', 'toast',
            'qrcode.min.js'
        }
        self.proxies = {
            'http': os.getenv('HTTP_PROXY'),
            'https': os.getenv('HTTPS_PROXY')
        }
        # 优化连接池参数
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=AI_CONSTANTS["MAX_THREADS"]//2,
            pool_maxsize=AI_CONSTANTS["MAX_THREADS"]
        )
        self.session.mount('https://', adapter)
        self.logger = configure_logger('爬虫引擎')
        
        # 配置连接池
        self.session.mount('http://', requests.adapters.HTTPAdapter(
            max_retries=3,
            pool_connections=20,
            pool_maxsize=100
        ))

    def extract_from_url(self, url: str) -> Tuple[str, List[str]]:
        """主入口方法"""
        self.visited_urls.add(url)
        try:
            html = self._fetch_html(url)
            html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
            #print("html",html)
            inline_scripts = self._extract_inline_js(html)
            external_scripts = self._extract_external_js(html, url)
            
            all_js = '\n'.join(inline_scripts + external_scripts)
            return re.sub(r'\s+', ' ', all_js).strip(), list(self.visited_urls)
        except Exception as e:
            raise RuntimeError(f"网页分析失败: {str(e)}")

    def _extract_inline_js(self, html: str) -> List[str]:
        """内联JS提取优化版"""
        soup = BeautifulSoup(html, 'html.parser')
        scripts = []
        for script in soup.find_all('script'):
            if not script.get('src') and not script.get('type', '').startswith('text/template'):
                script_content = ''.join([text for text in script.stripped_strings])
                if script_content:
                    scripts.append(script_content)
        return scripts

    def _extract_external_js(self, html: str, base_url: str) -> List[str]:
        """增强版外部JS提取"""
        soup = BeautifulSoup(html, 'html.parser')
        valid_urls = set()
        
        # 标准script标签
        for script in soup.find_all('script', src=True):
            script_url = urljoin(base_url, script['src'])
            if self._is_valid_script(script_url):
                valid_urls.add(script_url)
        
        # 动态加载模式检测
        dynamic_pattern = re.compile(
            r'document\.write\([\'"]<script\b[^>]*src=[\'"]([^\'"]+)[\'"]',
            re.IGNORECASE
        )
        for match in dynamic_pattern.findall(html):
            script_url = urljoin(base_url, match)
            if self._is_valid_script(script_url):
                valid_urls.add(script_url)
        
        # 并发获取内容
        scripts = []
        with ThreadPoolExecutor(max_workers=min(10, len(valid_urls))) as executor:
            future_to_url = {
                executor.submit(self._fetch_js_content, url): url
                for url in valid_urls
                if url not in self.visited_urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    content = future.result()
                    if content:
                        scripts.append(content)
                        self.visited_urls.add(url)
                except Exception as e:
                    print(f"JS获取失败 [{url}]: {str(e)}")
        
        return scripts

    def _is_valid_script(self, url: str) -> bool:
        """资源有效性验证"""
        # 黑名单过滤
        if any(b in url.lower() for b in self.blocklist):
            return False
        
        # 扩展名验证
        if not urlparse(url).path.lower().endswith(('.js', '.cjs', '.mjs')):
            return False
        
        return True

    def _fetch_html(self, url: str) -> str:
        """智能重定向处理版本"""
        self.logger.info("开始抓取页面 URL: %s", url)
        max_redirects = 5
        current_url = url
        visited = []
        
        for _ in range(max_redirects):
            try:
                # 禁用自动重定向以便手动处理
                resp = self.session.get(
                    current_url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=False
                )
                visited.append(current_url)
                
                # 处理HTTP重定向
                if 300 <= resp.status_code < 400:
                    new_url = urljoin(current_url, resp.headers.get('Location', ''))
                    if new_url in visited:
                        raise RuntimeError(f"重定向循环: {visited}")
                    current_url = new_url
                    continue
                    
                # 处理HTML中的Meta重定向
                if resp.status_code == 200 and 'text/html' in resp.headers.get('Content-Type', ''):
                    html = resp.text
                    redirect_url = self._detect_html_redirect(html, current_url)
                    if redirect_url:
                        if redirect_url in visited:
                            raise RuntimeError(f"HTML重定向循环: {visited}")
                        current_url = redirect_url
                        continue
                    self.logger.debug("HTML获取成功 长度: %d 字符", len(html))
                    return html
                    
                resp.raise_for_status()
                
            except requests.exceptions.RequestException as e:
                self.logger.error("页面抓取异常 URL: %s", url, exc_info=True)
                raise RuntimeError(f"请求失败: {str(e)}")
        
        raise RuntimeError(f"达到最大重定向次数: {max_redirects}")

    def _detect_html_redirect(self, html: str, base_url: str) -> Union[str, None]:
        """检测HTML中的重定向"""
        # Meta标签重定向
        meta_redirect = re.search(
            r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+;url=([^"\']+)["\']',
            html, 
            re.IGNORECASE
        )
        if meta_redirect:
            return urljoin(base_url, meta_redirect.group(1))
            
        # JavaScript立即跳转
        js_redirect = re.search(
            r'window\.location(?:\.href)?\s*=\s*["\']([^"\']+)["\']', 
            html,
            re.IGNORECASE
        )
        if js_redirect:
            return urljoin(base_url, js_redirect.group(1))
            
        return None

    def _fetch_js_content(self, url: str) -> Union[str, None]:
        """带重试机制的JS获取"""
        for attempt in range(3):
            self.logger.debug("获取JS资源 URL: %s 第%d次尝试", url, attempt+1)
            try:
                resp = self.session.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                # 内容类型验证
                content_type = resp.headers.get('Content-Type', '')
                if 'javascript' not in content_type and 'text/plain' not in content_type:
                    return None
                
                resp.raise_for_status()
                self.logger.info("JS获取成功 URL: %s", url)
                return resp.text.strip()
            except (requests.exceptions.RequestException, TimeoutError) as e:
                self.logger.warning("JS获取失败 URL: %s 错误: %s", url, str(e))
                if attempt == 2:
                    raise
                sleep(0.5 * (2 ** attempt))
        return None