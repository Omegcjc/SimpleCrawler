# main.py
# -*- coding: utf-8 -*-

from core.bili_crawler import BilibiliCrawlerConfig, BilibiliCrawler
from core.ku6_crawler import Ku6CrawlerConfig, Ku6Crawler
from core.haokan_crawler import HaokanCrawlerConfig, HaokanCrawler
from core.ifeng_crawler import IfengCrawlerConfig, IfengCrawler
from core.thepaper_crawler import ThepaperCrawlerConfig, ThepaperCrawler

from core.cctv_crawler import CCTVCrawler

from cli_parser import CLIParser

class InputParser:
    def __init__(self):
        self.mapping = {
            "bilibili": "bili",
            "bili": "bili",
            "ku6": "ku6",
            "haokan": "haokan",
            "ifeng": "ifeng",
            "thepaper": "thepaper",
            "cctv": "cctv",
            "baisou": "baisou"
        }

    def get_valid_platform(self):
        while True:
            user_input = input("请输入平台名称（bilibili, bili, ku6, haokan, ifeng, thepaper, cctv, baisou）：").strip()
            if user_input:
                normalized_input = user_input.strip().lower()
                platform = self.mapping.get(normalized_input, None)
                if platform:
                    return platform
                else:
                    print("无效输入。请选择以下平台之一：bilibili, bili, ku6, haokan, ifeng, thepaper, cctv, baisou。")
            else:
                print("无效输入。请选择以下平台之一：bilibili, bili, ku6, haokan, ifeng, thepaper, cctv, baisou。")
    
    def get_valid_mode(self):
        while True:
            mode = input("请输入爬取类型（搜索：search / 视频：video）：").strip().lower()
            if mode in ["search", "video"]:
                return mode
            else:
                print("无效的爬取类型。请选择：search 或 video。")
    
    def get_valid_target_search(self):
        while True:
            target = input("请输入搜索关键词：").strip()
            if target:
                return target
            else:
                print("无效的关键词。请输入有效的搜索关键词。")

    def get_valid_target_video(self):
        while True:
            target = input("请输入视频ID（多个ID请用英文逗号分隔）：").strip()
            if target:
                video_ids = tuple(id.strip() for id in target.split(",") if id.strip())
                if video_ids:
                    return video_ids
                else:
                    print("无效的视频ID。请输入有效的视频ID。")
            else:
                print("无效的视频ID。请输入有效的视频ID。")
    
    def get_valid_mulithreaded(self):
        while True:
            user_input = input("是否启用多线程下载？（y/n，默认n）：").strip().lower()
            if not user_input:  # 如果用户未输入，默认返回 False
                return False
            if user_input in ["y", "n"]:
                return user_input == "y"
            else:
                print("无效输入。请输入 y 或 n，或直接按回车默认选择 n。")

class CrawlerManager:
    def __init__(self):
        self.crawlers = {
            "bili": (BilibiliCrawlerConfig, BilibiliCrawler),
            "ku6": (Ku6CrawlerConfig, Ku6Crawler),
            "haokan": (HaokanCrawlerConfig, HaokanCrawler),
            "ifeng": (IfengCrawlerConfig, IfengCrawler),
            "thepaper": (ThepaperCrawlerConfig, ThepaperCrawler),
            "cctv": ("cctv", CCTVCrawler)
        }

    def _run_crawler(self, config_class, crawler_class, crawl_type, target, mulithreaded:bool = False):
        """运行爬虫"""
        if config_class == "cctv":
            CCTVCrawler(crawl_type, target)
            return 


        config = config_class()
        crawler = crawler_class(config = config, mulithreaded_download=mulithreaded)
        crawler.crawl(crawl_type, target)
        if hasattr(crawler, "download_manager"):
            crawler.download_manager.finish_adding_tasks()
            crawler.download_manager.wait_for_all_and_stop()

    def select_crawler_to_run(self):
        input_parser = InputParser()
        platform = input_parser.get_valid_platform()
        crawl_type = input_parser.get_valid_mode()
        target = None
        if crawl_type == "search":
            target = input_parser.get_valid_target_search()
        elif crawl_type == "video":
            target = input_parser.get_valid_target_video()
        
        mulithreaded = input_parser.get_valid_mulithreaded()
        
        if platform in self.crawlers:
            config_class, crawler_class = self.crawlers[platform]
            self._run_crawler(config_class, crawler_class, crawl_type, target, mulithreaded)

def main():
    cli_parser = CLIParser()
    args = cli_parser.parse_args()
    manager = CrawlerManager()

    if args is not None and args["platform"] and args["mode"] and args["target"]:
        # 命令行输入模式
        platform = args["platform"]
        mode = args["mode"]
        target = args["target"]
        multithreaded = args["multithreaded"]

        # 打印解析后的参数
        print("* 命令行参数解析结果：")
        print(f"  - 平台: {platform}")
        print(f"  - 爬取类型: {mode}")
        print(f"  - 目标: {target}")
        print(f"  - 多线程下载: {'启用' if multithreaded else '未启用'}")

        if platform in manager.crawlers:
            config_class, crawler_class = manager.crawlers[platform]
            manager._run_crawler(config_class, crawler_class, mode, target, multithreaded)
        else:
            print("无效的平台名称。")
    else:
        # 手动终端输入模式
        print("未检测到命令行参数，切换到手动输入模式...")
        manager.select_crawler_to_run()

if __name__ == "__main__":

    print("* 欢迎使用 SimpleCrawler！")
    print("* 请根据提示输入参数，或使用命令行参数。(python main.py --help 查看帮助信息)")
    print("* 注意事项: ")
    print("  - bilibili不支持multithreaded下载视频")
    print("  - ku6不支持search,且单个视频因文件较大，下载较慢，建议启用多线程")
    print("  - thepaper搜索得到的结果包含视频和新闻，只爬取视频")
    print("  - thepaper搜索得到的结果包含视频和新闻，只爬取视频")
    
    main()



# SimpleCrawler 命令行解析器
# options:
#   -h, --help            show this help message and exit
#   -p PLATFORM, --platform PLATFORM
#                         指定爬取平台（bilibili, ku6, haokan, ifeng, thepaper, cctv, baisou）
#   -m {search,video}, --mode {search,video}
#                         指定爬取类型（search 或 video）
#   -t TARGET, --target TARGET
#                         指定目标（搜索关键词或视频ID，多个ID用英文逗号分隔）
#   --multithreaded       是否启用多线程下载（默认不启用）

# 示例命令行输入：
# python main.py -p bilibili -m search -t "python爬虫"
# python main.py -p ku6 -m video -t "QdRTpiXkNC6iPrVnhaN5_tCg5UI." --multithreaded  # 启用多线程下载

# python main.py --help # 查看帮助信息
# python main.py # 进入手动输入模式

# 手动输入模式示例：

# 未检测到命令行参数，切换到手动输入模式...
# 请输入平台名称（bilibili, bili, ku6, haokan, ifeng, thepaper, cctv, baisou）：ku6
# 请输入爬取类型（搜索：search / 视频：video）：search
# 请输入搜索关键词：特朗普
# 是否启用多线程下载？（y/n，默认n）：n
# 2025-04-10 16:38:52,895 - core.ku6_crawler - INFO - ku6网站无法搜索，请直接输入视频ID
