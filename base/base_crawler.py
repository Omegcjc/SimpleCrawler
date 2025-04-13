# base_crawler.py
from abc import ABC, abstractmethod
from pathlib import Path
import requests
import logging
from typing import Optional
from playwright.sync_api import Page
from time import sleep

from base.base_client import BaseClient
from base.base_config import BaseCrawlerConfig, DownloadTask

from tools.video_down_wget import VideoDownloader
from tools.scraper_utils import dynamic_scroll
from tools.file_tools import save_to_json
from tools.download_manager import DownloadManager



# 日志处理
from config.config import *
logger = logging.getLogger(__name__)

class BaseCrawler(ABC):
    """爬虫基类，定义通用爬取流程和扩展点"""

    def __init__(self, 
                 headless: bool = True,
                 config: BaseCrawlerConfig = None,
                 mulithreaded_download: bool = False):
        
        self.config = config or BaseCrawlerConfig() # 默认配置

        self.client = BaseClient(headless=headless) # 客户端组件 
        self.video_downloader = VideoDownloader() # 视频下载wget组件，单线程
        self.mulithreaded_download = mulithreaded_download
        if self.mulithreaded_download:
            self.download_manager = DownloadManager(max_workers = 4) # 下载管理器，支持多线程下载

        self.max_retries = self.config.MAX_RETRIES
        self.max_video_num = self.config.MAX_VIDEO_NUM
        self.page: Optional[Page] = None

    def crawl(self, mode: str, target: str):
        """统一入口方法（基类实现流程控制）"""
        mode = mode.lower()
        if mode not in ["search", "video"]:
            raise ValueError(f"无效模式: {mode}，支持模式: 'search'/'video'")
        
        target = target.strip() if isinstance(target, str) else target
        if not target:
            raise ValueError(f"无效target: {target}")
        
        self.client.start_browser(base_url=self.config.BASE_URL)
        self.page = self.client.page

        try:
            if mode == "search":
                if not self.config.OUTPUT_VIDEOINFO_DIR.endswith('/search'):
                    self.config.OUTPUT_VIDEOINFO_DIR = self.config.OUTPUT_VIDEOINFO_DIR + '/search'
                    self.config.OUTPUT_VIDEOMP4_DIR = self.config.OUTPUT_VIDEOMP4_DIR + '/search'

                self._process_search(target)
            elif mode == "video":
                if not self.config.OUTPUT_VIDEOINFO_DIR.endswith('/use_id'):
                    self.config.OUTPUT_VIDEOINFO_DIR = self.config.OUTPUT_VIDEOINFO_DIR + '/use_id'
                    self.config.OUTPUT_VIDEOMP4_DIR = self.config.OUTPUT_VIDEOMP4_DIR + '/use_id'

                if isinstance(target, (list, tuple)):  # 检测是否为列表或元组
                    for video_id in target:
                        self._process_video(video_id.strip())
                else:
                    self._process_video(target)
            
            self.client.end_browser()
        except Exception as e:
            logger.error(f"{mode}模式爬取失败: {str(e)}")
            self.client.end_browser()
            raise

    @abstractmethod
    def _process_search(self, target: str):
        """搜索模式处理逻辑（子类必须实现）"""
        pass

    @abstractmethod
    def _process_video(self, target: str):
        """视频模式处理逻辑（子类必须实现）"""
        pass

    def _pre_page_handle(self, url, scroll_times = 3):
        ''' 重试机制 '''
        retries = 0
        while retries < self.max_retries:
            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # close_popups(self.page)
                sleep(2)
                dynamic_scroll(self.page, scroll_times = scroll_times)
                break
            except TimeoutError:
                logger.warning(f"页面加载超时，第{retries+1}次重试")
                retries += 1
                if retries >= self.max_retries:
                    raise
                self.page.reload()
            except Exception as e:
                logger.error(f"页面处理异常: {str(e)}")
                retries += 1
                if retries >= self.max_retries:
                    raise
                self.page.reload()

    def _save_videolist(self, results: list, target: str):
        """保存视频列表数据"""
        file_path = Path(self.config.OUTPUT_VIDEOLIST_DIR) / self.config.OUTPUT_VIDEOLIST_FILENAME.format(target)
        save_to_json(results, file_path)

    def _save_videoinfo(self, data: dict, target: str):
        """保存视频元数据"""
        file_path = Path(self.config.OUTPUT_VIDEOINFO_DIR) / self.config.OUTPUT_VIDEOINFO_FILENAME.format(target)
        save_to_json(data, file_path)

    def _download_video(self, target: str, download_url: str, referer: str = None):
        """通用视频下载方法"""

        file_name = self.config.OUTPUT_VIDEOMP4_FILENAME.format(target)
        file_dir = self.config.OUTPUT_VIDEOMP4_DIR

        try:
            logger.info(f"开始下载视频: {download_url}")
            self.video_downloader.download_video_stealth(
                download_url, 
                file_dir, 
                file_name, 
                referer=referer or self.config.BASE_URL
            )
            logger.info(f"视频 {target} 下载完成！")
        except requests.exceptions.RequestException as e:
            logger.error(f"下载失败: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"视频下载异常: {e}")
            raise

