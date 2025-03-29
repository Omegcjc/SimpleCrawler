

PLATFORM = "bilibili"
BASE_URL = "https://www.bilibili.com/"
SEARCH_URL = "https://search.bilibili.com/all?keyword={}"

VIDEO_URL = "https://www.bilibili.com/video/{}"

VIDEO_RES_URL = "https://api.bilibili.com/x/player/playurl?fnval=80&avid={}&cid={}"

MAX_VIDEO_NUM = 10 # 最多在搜索后爬取的视频数

OUTPUT_VIDEOLIST_DIR = "./data/bilibili/search_video_list"
OUTPUT_VIDEOLIST_FILENAME = "search_{}.json"

OUTPUT_VIDEOMP4_DIR = "./data/bilibili/videos"
OUTPUT_VIDEOMP4_FILENAME = "video_{}_src.mp4"

OUTPUT_VIDEOINFO_DIR = "./data/bilibili/videos"
OUTPUT_VIDEOINFO_FILENAME = "video_{}_info.json"

STEALTH_JS_PATH = "stealth.min.js"

# 添加自己的SESSDATA，用于视频爬取
SESSDATA = ""

