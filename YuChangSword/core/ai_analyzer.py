import hashlib
import re
import requests
import json
from pathlib import Path
from time import sleep
from typing import Dict, List, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from config.ai_settings import AI_CONSTANTS
from config.log_config import configure_logger

from config.ai_settings import AI_PROMPTS, AI_SETTINGS, DEEPSEEK_API, AI_STRATEGY
from core.cache_manager import AnalysisCache

class AIAnalyzer:
    def __init__(self):
        self.base_url = f"{DEEPSEEK_API['base_url']}/chat/completions"
        self.config_dir = Path(__file__).parent.parent / "config"
        self.algorithm_map = self._load_algorithm_map()
        self.api_key = DEEPSEEK_API["api_key"]
        self.enabled = AI_STRATEGY["enable"] and bool(self.api_key.strip())
        self.logger = configure_logger('AI分析器')
        self.logger.info(f"AI服务初始化完成，启用状态: {self.enabled}")
        self.cache = AnalysisCache()
        self.logger.info("AI服务状态: %s", "已启用" if self.enabled else "已禁用")
        if self.enabled and not self.api_key.startswith("sk-"):
            print("[警告] API密钥格式可能不正确")

    def _load_algorithm_map(self) -> Dict:
        try:
            with open(self.config_dir / "algorithm_features.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(e)
            return {}

    def analyze_code(self, code: str) -> Dict:  # 统一入口参数
        result = {
            "algorithm_analysis": {"ai": {}, "local": []},
            "key_analysis": {},
            "custom_analysis": {},
            "errors": []
        }

        # 本地特征分析
        try:
            result["algorithm_analysis"]["local"] = self._match_local_features(code)
        except Exception as e:
            result["errors"].append(f"local_analysis: {str(e)}")

        # AI分析流程
        analysis_flow = [
            ("algorithm_analysis", self._analyze_algorithm),
            ("key_analysis", self._analyze_key),
            ("custom_analysis", self._analyze_custom)
        ]
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(func, code): name 
                for name, func in analysis_flow
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result[name] = future.result()
                except Exception as e:
                    result["errors"].append(f"{name}_error: {str(e)}")
        return result

    def _match_local_features(self, code: str) -> List[Dict]:
        risk_level_map = {
            "RSA": lambda x: 3 if re.search(r"RSA\.generate\(1024", x) else 1,
            "ECC": lambda x: 2 if "secp112r1" in x else 1
        }
        findings = []
        for category, algorithms in self.algorithm_map.items():
            for algo, config in algorithms.items():
                for pattern in config.get("patterns", []):
                    try:
                        if re.search(pattern, code, re.IGNORECASE):
                            # 计算风险等级
                            risk_level = risk_level_map.get(algo, lambda _:1)(code)
                            
                            findings.append({
                                "category": category,
                                "algorithm": algo,
                                "confidence": 0.85,
                                "risk_level": risk_level  # 新增风险分级
                            })
                    except re.error:
                        continue
        print("01-findings", findings)
        return findings

    def _analyze_algorithm(self, code: str) -> Dict:
        for _ in range(3):
            try:
                #print("code",code)
                response = self._call_api("algorithm", code)
                print("02-算法识别：", response)
                return self._parse_response(response)
            except Exception as e:
                print(f"[Algorithm Retry] {str(e)}")
        return {"error": "MAX_RETRIES"}

    def _analyze_key(self, code: str) -> Dict:
        try:
            response = self._call_api("key", code)
            print("03-key识别：", response)
            return self._parse_response(response)
        except Exception as e:
            return {"error": str(e)}

    def _analyze_custom(self, code: str) -> Dict:
        cache_key = hashlib.sha256(code.encode()).hexdigest()
        if cached := self.cache.get(cache_key):
            self.logger.debug(f"缓存命中: {cache_key}")
            return cached
        try:
            response = self._call_api("custom", code)
            parsed = self._parse_response(response)
            print("05-自定义函数识别：", parsed)
            self.cache.set(cache_key, parsed)
            return parsed
        except Exception as e:
            return {"error": str(e)}

    def _call_api(self, prompt_type: str, code: str) -> Dict:
        self.logger.debug(f"开始API调用 [{prompt_type}] 代码长度: {len(code)}")
        for attempt in range(AI_CONSTANTS["MAX_RETRIES"]):
            try:
                # 检查1：确保prompt_type存在于AI_PROMPTS中
                if prompt_type not in AI_PROMPTS:
                    raise ValueError(f"无效的prompt_type: {prompt_type}，可用类型: {list(AI_PROMPTS.keys())}")

                # 检查2：确保模板包含{code}占位符
                template = AI_PROMPTS[prompt_type]
                if "{code}" not in template:
                    raise ValueError(f"AI_PROMPTS['{prompt_type}']模板缺少{{code}}占位符")
                prompt = AI_PROMPTS[prompt_type].format(code=code[:AI_SETTINGS["max_code_length"]])
                print(f"[API Request] Type: {prompt_type} Length: {len(code)}")
                
                response = requests.post(
                    self.base_url,
                    json={
                        "model": DEEPSEEK_API["model"],
                        "messages": [
                            {"role": "system", "content": "严格按JSON格式响应"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 8192
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=600
                )
                print("123")
                response.raise_for_status()
                self.logger.info(f"API请求成功 类型: {prompt_type} 耗时: {response.elapsed.total_seconds():.2f}s")
                return response.json()
            except requests.exceptions.RequestException as e:
                error_detail = {
                    "error_type": "network_error",
                    "attempt": attempt + 1,
                    "exception": str(e),
                    "status_code": getattr(e.response, 'status_code', None)
                }
                self.logger.error("API请求失败详情: %s", error_detail)
            except json.JSONDecodeError as e:
                error_detail = {
                    "error_type": "invalid_json",
                    "response_text": response.text[:200]
                }
                self.logger.error("JSON解析失败: %s", error_detail)
            except Exception as e:
                self.logger.error(
                    "API请求失败 HTTP状态码: %d 响应内容: %s",
                    e.response.status_code,
                    e.response.text[:200],
                    exc_info=True
                )
                print(f"[API Error] Attempt {attempt+1}: {str(e)}\n")
                print(response.text)
                sleep(2 ** attempt)
        raise Exception("API request failed")

    def _parse_response(self, response: Dict) -> Dict:
        try:
            content = response["choices"][0]["message"]["content"]
            print(f"[Raw Response]\n{content}\n{'-'*40}")

            # 原有正则匹配逻辑保持不变
            json_match = re.search(r'\{((?:[^{}]|(?:\{[^{}]*\}))*)\}', content, re.DOTALL)
            if not json_match:
                raise ValueError("未找到有效JSON结构")

            json_str = json_match.group(0)
            print(f"[Matched JSON]\n{json_str}\n{'-'*40}")

            # 原有字符清理逻辑保持不变
            json_str = (
                json_str
                .replace('“', '"').replace('”', '"')
                .replace("'", '"')
                .replace("，", ",")
                .replace("：", ":")
            )

            # 原有自动补全逻辑保持不变
            if json_str.count('{') != json_str.count('}'):
                if json_str[-1] != '}':
                    json_str += '}' * (json_str.count('{') - json_str.count('}'))

            # ----------------- 新增非对称加密校验 -----------------
            parsed_data = json.loads(json_str)  # 原有解析逻辑
            
            # 仅在检测到非对称加密字段时进行校验
            if "非对称加密" in parsed_data:
                required_keys = ["算法", "密钥长度"]
                if not all(k in parsed_data["非对称加密"] for k in required_keys):
                    self.logger.warning("非对称加密参数缺失: %s", parsed_data)
                    parsed_data["非对称加密"]["error"] = "MISSING_FIELDS"
            
            return parsed_data  # 保持原有返回结构

        except Exception as e:
            # 原有异常处理逻辑保持不变
            print(f"[Parse Error] {str(e)}")
            print(f"[Invalid JSON]\n{json_str}")
            self.logger.error(
                "JSON解析失败 错误位置: %d 原始内容: %s...",
                e.pos,
                json_str[:200],
                exc_info=True
            )
            return {"error": "INVALID_RESPONSE"}