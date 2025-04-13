from dataclasses import dataclass

from base.base_config import BaseCrawlerConfig

@dataclass
class Ku6CrawlerConfig(BaseCrawlerConfig):
    """haokan爬虫配置（正确覆盖父类字段）"""
    PLATFORM: str = "ku6"

    BASE_URL: str = "https://www.ku6.com/"
    SEARCH_URL: str = "" # ku6不支持search
    VIDEO_URL: str = "https://www.ku6.com/video/detail?id={}"

    MAX_VIDEO_NUM: int = 10  # 覆盖默认值

# ku6 副本没有采用浏览器的方式进行爬取。
# 直接使用request进行视频的爬取与下载
# 增加的网络配置

# =================以下属于ku6_v1.0.py需要的配置，运行ku6_v1.0时请将其注释解除=================

# from fake_useragent import UserAgent

# HEADERS={
#     'User-Agent': UserAgent().random,
#     'referer': BASE_URL
# }


# # 请添加自己的cookies
# COOKIES = {}

# DOWNLOAD_METHOD = 'auto' # 'single'单线程, 'chunked'多线程, or 'auto'自动选择下载方式


