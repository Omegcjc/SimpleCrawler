
# 平台基础配置
PLATFORM = "haokan"
BASE_URL = "https://www.haokan.baidu.com"
VIDEO_URL = "https://haokan.baidu.com/v?vid={}"
SEARCH_URL = "https://haokan.baidu.com/web/search/page?query={}"
MAX_VIDEO_NUM = 10  # 最多在搜索后爬取的视频数

# 输出路径配置
OUTPUT_VIDEOLIST_DIR = "./data/haokan/search_video_list"
OUTPUT_VIDEOLIST_FILENAME = "search_{}.json"

OUTPUT_VIDEOMP4_DIR = "./data/haokan/videos"
OUTPUT_VIDEOMP4_FILENAME = "video_{}_src.mp4"

OUTPUT_VIDEOINFO_DIR = "./data/haokan/videos"
OUTPUT_VIDEOINFO_FILENAME = "video_{}_info.json"

# 浏览器配置
STEALTH_JS_PATH = ""

# 添加自己的cookie,保证浏览器登录设置
SESSDATA = ""