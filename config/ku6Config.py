

PLATFORM = "ku6"
BASE_URL = "https://www.ku6.com/"

VIDEO_URL = "https://www.ku6.com/video/detail?id={}"
SEARCH_URL = "" # ku6不支持search

VIDEO_RES_URL= ""

MAX_VIDEO_NUM = 10 # 最多在搜索后爬取的视频数

# 保存文件路径配置
OUTPUT_VIDEOLIST_DIR = ""
OUTPUT_VIDEOLIST_FILENAME = ""

OUTPUT_VIDEOMP4_DIR = "./data/ku6/videos"
OUTPUT_VIDEOMP4_FILENAME = "video_{}_src.mp4"

OUTPUT_VIDEOINFO_DIR = "./data/ku6/videos"
OUTPUT_VIDEOINFO_FILENAME = "video_{}_info.json"

# ku6 没有采用浏览器的方式进行爬取。
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


