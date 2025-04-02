from dataclasses import dataclass

from base.base_config import BaseCrawlerConfig

@dataclass
class HaokanCrawlerConfig(BaseCrawlerConfig):
    """haokan爬虫配置（正确覆盖父类字段）"""
    PLATFORM: str = "haokan"

    BASE_URL: str = "https://www.haokan.baidu.com"
    SEARCH_URL: str = "https://haokan.baidu.com/web/search/page?query={}"
    VIDEO_URL: str = "https://haokan.baidu.com/v?vid={}"

    MAX_VIDEO_NUM: int = 10  # 覆盖默认值

