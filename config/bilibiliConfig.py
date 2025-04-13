from dataclasses import dataclass

from base.base_config import BaseCrawlerConfig

@dataclass
class BilibiliCrawlerConfig(BaseCrawlerConfig):
    """Bilibili爬虫配置（正确覆盖父类字段）"""
    PLATFORM: str = "bilibili"

    BASE_URL: str = "https://www.bilibili.com/"
    SEARCH_URL: str = "https://search.bilibili.com/all?keyword={}"
    VIDEO_URL: str = "https://www.bilibili.com/video/{}"
    VIDEO_RES_URL: str = "https://api.bilibili.com/x/player/playurl?fnval=80&avid={}&cid={}"

    MAX_VIDEO_NUM: int = 10  # 覆盖默认值

    STEALTH_JS_PATH: str = "stealth.min.js"

    SESSDATA: str = ""


