

from dataclasses import dataclass

from base.base_config import BaseCrawlerConfig

@dataclass
class ThepaperCrawlerConfig(BaseCrawlerConfig):
    """Thepaper爬虫配置（正确覆盖父类字段）"""
    PLATFORM: str = "thepaper"

    BASE_URL: str = "https://www.thepaper.cn"
    SEARCH_URL: str = "https://www.thepaper.cn/searchResult?id={}"
    VIDEO_URL: str = "https://www.thepaper.cn/newsDetail_forward_{}"

    MAX_VIDEO_NUM: int = 10  # 覆盖默认值

