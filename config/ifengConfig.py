

PLATFORM = "ifeng"
BASE_URL = "https://v.ifeng.com/"

VIDEO_URL = "https://v.ifeng.com/c/{}"
SEARCH_URL = "https://so.ifeng.com/?q={}"

VIDEO_RES_URL= ""

MAX_VIDEO_NUM = 10 # 最多在搜索后爬取的视频数

OUTPUT_VIDEOLIST_DIR = "./data/ifeng/search_video_list"
OUTPUT_VIDEOLIST_FILENAME = "search_{}.json"

OUTPUT_VIDEOMP4_DIR = "./data/ifeng/videos"
OUTPUT_VIDEOMP4_FILENAME = "video_{}_src.mp4"

OUTPUT_VIDEOINFO_DIR = "./data/ifeng/videos"
OUTPUT_VIDEOINFO_FILENAME = "video_{}_info.json"

STEALTH_JS_PATH = ""

# 添加自己的SESSDATA，用于登录
SESSDATA = ""

