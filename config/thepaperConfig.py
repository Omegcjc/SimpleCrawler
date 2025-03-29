

PLATFORM = "thepaper"
BASE_URL = "https://www.thepaper.cn"

VIDEO_URL = "https://www.thepaper.cn/newsDetail_forward_{}"
SEARCH_URL = "https://www.thepaper.cn/searchResult?id={}"

VIDEO_RES_URL= ""

MAX_VIDEO_NUM = 10 # 最多在搜索后爬取的视频数

OUTPUT_VIDEOLIST_DIR = "./data/thepaper/search_video_list"
OUTPUT_VIDEOLIST_FILENAME = "search_{}.json"

OUTPUT_VIDEOMP4_DIR = "./data/thepaper/videos"
OUTPUT_VIDEOMP4_FILENAME = "video_{}_src.mp4"

OUTPUT_VIDEOINFO_DIR = "./data/thepaper/videos"
OUTPUT_VIDEOINFO_FILENAME = "video_{}_info.json"

STEALTH_JS_PATH = ""

# 添加自己的SESSDATA，用于登录
SESSDATA = ""