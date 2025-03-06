import argparse
import asyncio
from core.ai_analyzer import AIAnalyzer
from core.web_crawler import JSExtractor
from config.log_config import configure_logger
logger = configure_logger('主程序')

def show_banner():
    logger.info("程序启动 版本:1.0.0")
    cyan = "\033[96m"    # 青色
    yellow = "\033[93m"  # 黄色
    green = "\033[92m"   # 绿色
    reset = "\033[0m"    # 重置颜色

    print(f"""
{cyan} _     _       _______ _                        ______                      _ 
{cyan} | |   | |     (_______) |                      / _____)                    | |
{cyan} | |___| |_   _ _      | |__  _____ ____   ____( (____  _ _ _  ___   ____ __| |
{cyan} |_____  | | | | |     |  _ \(____ |  _ \ / _  |\____ \| | | |/ _ \ / ___) _  |
{cyan}  _____| | |_| | |_____| | | / ___ | | | ( (_| |_____) ) | | | |_| | |  ( (_| |
{cyan} (_______|____/ \______)_| |_\_____|_| |_|\___ (______/ \___/ \___/|_|   \____|
                                        (_____|                               
{green}╔═══════════════════════════╗
{green}║ JS加密算法识别工具 v1.0.0 ║
{green}╠═══════════════════════════╣
{green}║   鱼肠出鞘 · 暗流涌动     ║
{green}║   东方隐侠安全团队出品    ║
{green}╚═══════════════════════════╝
                                        {reset}""")


def main():
    parser = argparse.ArgumentParser(description='JS加密算法识别工具')
    parser.add_argument('-u', '--url', help='待分析的网页URL')
    parser.add_argument('-f', '--file', help='本地JS文件路径')
    args = parser.parse_args()

    analyzer = AIAnalyzer()
    extractor = JSExtractor()
    logger.info("命令行参数 URL:%s FILE:%s", args.url, args.file)
    if args.url:
        print(f"\n开始分析URL: {args.url}")
        logger.debug("开始分析URL:%s", args.url)
        try:
            js_code, crawled_urls = extractor.extract_from_url(args.url)
            print(f"抓取到{len(crawled_urls)}个JS资源")
            
            result = analyzer.analyze_code(js_code)
            print("\n[最终分析报告]")
            print(result)
            """
            print("\n[分析结果]")
            print("AI识别结果:", result["algorithm_analysis"]["ai"])
            print("本地规则命中:", [f["algorithm"] for f in result["algorithm_analysis"]["local"]])
            """
            if result["errors"]:
                print("\n警告信息:", result["errors"])
                
        except KeyboardInterrupt:
            logger.warning("用户中断执行")
        
        except Exception as e:
            print(f"分析失败: {str(e)}")
            
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                code = f.read()
            result = analyzer.analyze_code(code)
            print("本地文件分析结果:", result)
        except Exception as e:
            print(f"分析失败: {str(e)}")


if __name__ == "__main__":
    show_banner()
    main()