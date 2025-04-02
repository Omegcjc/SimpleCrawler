from dataclasses import dataclass

from base.base_config import BaseCrawlerConfig

@dataclass
class IfengCrawlerConfig(BaseCrawlerConfig):
    """ifeng爬虫配置（正确覆盖父类字段）"""
    PLATFORM: str = "ifeng"

    BASE_URL: str = "https://v.ifeng.com/"
    SEARCH_URL: str = "https://so.ifeng.com/?q={}"
    VIDEO_URL: str = "https://v.ifeng.com/c/{}"

    MAX_VIDEO_NUM: int = 10  # 覆盖默认值




