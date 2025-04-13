import argparse

class CLIParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="SimpleCrawler 命令行解析器")
        self._setup_arguments()

    def _setup_arguments(self):
        self.parser.add_argument(
            "-p", "--platform",
            type=str,
            help="指定爬取平台（bilibili, ku6, haokan, ifeng, thepaper, cctv, baisou）"
        )
        self.parser.add_argument(
            "-m", "--mode",
            type=str,
            choices=["search", "video"],
            help="指定爬取类型（search 或 video）"
        )
        self.parser.add_argument(
            "-t", "--target",
            type=str,
            help="指定目标（搜索关键词或视频ID，多个ID用英文逗号分隔）"
        )
        self.parser.add_argument(
            "--multithreaded",
            action="store_true",
            help="是否启用多线程下载（默认不启用）"
        )

    def parse_args(self):
        if len(vars(self.parser.parse_args())) == 0:
            return None  # 如果没有任何参数输入，返回 None
        args = self.parser.parse_args()
        return {
            "platform": args.platform.strip().lower() if args.platform else None,
            "mode": args.mode.strip().lower() if args.mode else None,
            "target": tuple(id.strip() for id in args.target.split(",") if id.strip()) if args.target else None,
            "multithreaded": args.multithreaded
        }
