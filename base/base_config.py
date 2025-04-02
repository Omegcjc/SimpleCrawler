# BaseConfig.py
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Type


class BaseBrowerConfig:
    """浏览器配置中心"""
    @staticmethod
    def get_chromium_args():
        return [
                "--start-maximized",  # 最大化窗口
                "--autoplay-policy=no-user-gesture-required",  # 允许自动播放
                "--disable-infobars",  # 禁用信息栏
                "--disable-blink-features=AutomationControlled",  # 反自动化检测
                "--disable-dev-shm-usage",  # 共享内存优化
                "--no-sandbox",  # 取消沙盒模式
                "--enable-gpu",  # 启用 GPU 加速
                "--disable-extensions",  # 禁用扩展
        ]
    
    @staticmethod
    def get_headers(Refer:str):
        return {
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
            "extra_http_headers":{
                
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": f"{Refer}",
                # "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        }

# 几乎没用，只是告诉你，采集了些什么值
class VIDEO_INFO_ALL:
    def __init__(self):

        # 平台及其对应url
        self.platform = None        # 平台名
        self.base_url = None        # 平台对应url


        self.title = None           # 视频标题
        self.id = None              # 视频ID
        self.author = None          # 视频作者
        self.video_url = None       # 视频url
        self.download_url = None    # 视频下载具体地址
        self.publish_date = None    # 视频发布日期
        self.channel = None         # 可能是类别，可能是频道，也可能是keywords等

        self.duration = None        # 视频持续时长
        self.views = None           # 视频点击量
        self.desc = None            # 视频简介
        self.likes = None           # 视频点赞数
        self.coins = None           # 视频投币数(bilibili独有)
        self.favs = None            # 视频收藏数
        self.shares = None          # 视频转发数
    
    def dict_info_all(self):
        """将对象属性转换为字典"""
        return {
            "platform": self.platform,
            "base_url": self.base_url,
            "title": self.title,
            "id": self.id,
            "author": self.author,
            "duration": self.duration,
            "channel":self.channel,
            "video_url": self.video_url,
            "download_url": self.download_url,
            "publish_date": self.publish_date,
            "views": self.views,
            "desc": self.desc,
            "likes": self.likes,
            "coins": self.coins,
            "favs": self.favs,
            "shares": self.shares
        }
    
    def refresh_info(self, mode):
        """
        重置所有属性为None,
        只有当mode == "all" 的时候更新所有内容
        """
        if mode == "all":
            self.platform = None
            self.base_url = None
        
        self.title = None
        self.id = None
        self.author = None
        self.video_url = None
        self.download_url = None
        self.publish_date = None
        self.views = None
        self.desc = None
        self.likes = None
        self.coins = None
        self.favs = None
        self.shares = None
        self.duration = None
        self.channel = None
    
    def get_info(self, info_key):
        """根据键名返回对应属性值"""
        valid_keys = {
            'platform', 'base_url', 'title', 'id', 'author', 
            'video_url', 'download_url', 'publish_date', 'views',
            'desc', 'likes', 'coins', 'favs', 'shares', "duration",
            "channel"
        }
        
        if info_key.lower() not in valid_keys:
            raise KeyError(f"Invalid info key: {info_key}")
        
        return getattr(self, info_key, None)

@dataclass
class BaseCrawlerConfig:
    """爬虫配置基类（使用数据类正确实现）"""
    # 平台配置
    PLATFORM: str = "generic"
    BASE_URL: str = ""
    SEARCH_URL: str = "{}"
    VIDEO_URL: str = "{}"
    VIDEO_RES_URL: str = "{}"
    
    # 限制配置
    MAX_VIDEO_NUM: int = 10
    MAX_RETRIES: int = 3
    
    # 动态路径（通过__post_init__初始化）
    OUTPUT_VIDEOLIST_DIR: str = field(init=False)
    OUTPUT_VIDEOMP4_DIR: str = field(init=False)
    OUTPUT_VIDEOINFO_DIR: str = field(init=False)
    
    # 固定文件名模板
    OUTPUT_VIDEOLIST_FILENAME: str = "search_{}.json"
    OUTPUT_VIDEOMP4_FILENAME: str = "video_{}_src.mp4"
    OUTPUT_VIDEOINFO_FILENAME: str = "video_{}_info.json"
    
    # 其他配置
    STEALTH_JS_PATH: str = ""
    SESSDATA: str = ""

    def __post_init__(self):
        """动态初始化路径"""
        base_dir = f"./data/{self.PLATFORM}"
        self.OUTPUT_VIDEOLIST_DIR = f"{base_dir}/search_video_list"
        self.OUTPUT_VIDEOMP4_DIR = f"{base_dir}/videos"
        self.OUTPUT_VIDEOINFO_DIR = f"{base_dir}/videos"

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

