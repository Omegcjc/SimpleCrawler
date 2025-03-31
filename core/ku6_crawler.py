import os
import json
from tqdm import tqdm  # 进度条支持
from time import sleep
from pathlib import Path
from typing import Optional, Dict, List

import re
import time
import requests
from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError
from bs4 import BeautifulSoup

from base.base_client import baseClient

from tools.video_down_wget import VideoDownloader
from tools.scraper_utils import dynamic_scroll
from tools.file_tools import save_to_json, debug_help

from config.config import *
from config.BaseConfig import BrowerConfig, VIDEO_INFO_ALL
from config.ku6Config import * # 大写常量

logger = logging.getLogger(__name__)

class ku6Crawel:
    def __init__(self, headless: bool = True):

        self.client = baseClient(headless=headless)
        self.video_downloader = VideoDownloader()  # 初始化视频下载器

        self.max_retries = 3  # 最大重试次数
        self.max_video_num = MAX_VIDEO_NUM #search后爬取最大视频数
        self.page : Page
        # self.cur_url = self.page.url()

    def crawl(self, mode: str, target: str):
        """统一入口方法，增加参数校验"""
        mode = mode.lower()
        if mode not in ["search", "video"]:
            raise ValueError(f"无效模式: {mode}，支持模式: 'search'/'video'")
        
        target = target.strip()
        if not target:
            raise ValueError(f"无效target: {target}，请输入与模式对应的target")
        
        self.client.start_browser(base_url = BASE_URL)
        self.page = self.client.page

        try:
            if mode == "search":
                self._process_search(target)
                
            elif mode == "video":
                self._process_video(target)
            
            self.client.end_browser()
        except Exception as e:
            logger.error(f"{mode}模式爬取失败: {str(e)}")
            self.client.end_browser()
            raise

    def _pre_page_handle(self, url):
        ''' 重试机制 '''
        retries = 0
        while retries < self.max_retries:
            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # close_popups(self.page)
                sleep(2)
                dynamic_scroll(self.page)
                break
            except TimeoutError:
                logger.warning(f"页面加载超时，第{retries+1}次重试")
                retries += 1
                if retries >= self.max_retries:
                    raise
                self.page.reload()
            except Exception as e:
                logger.error(f"页面处理异常: {str(e)}")
                raise

    def _process_search(self, target: str):
        logger.info("ku6网站无法search,请直接输入视频ID")
        return
        
    def _process_video(self, target: str):

        video_info = VIDEO_INFO_ALL()
        video_info.refresh_info(mode = 'all')       #重置所有内容

        # 固定内容赋值
        video_info.platform = PLATFORM              # [视频信息] 平台 - ku6Config          
        video_info.base_url = BASE_URL              # [视频信息] base_url - ku6Config
        video_info.id = target                      # [视频信息] id = target

        try:
            # 初始化页面
            video_url = VIDEO_URL.format(target)
            self._pre_page_handle(video_url)  # 确保包含页面加载等待逻辑

            # 得到title, channel, video_url
            html_content = self.page.content()
            video_data_parts = self._parse_video_data(html_content)

            video_src = video_data_parts['video_url']
            if not video_src:
                logger.error("视频源地址为空")
                raise

            video_info.video_url = video_url                    # [视频信息] video_url - 直达视频的URL
            video_info.download_url = video_src                 # [视频信息] download_url - 视频下载地址
            video_info.title = video_data_parts["title"]        # [视频信息] title - 视频标题
            video_info.channel = video_data_parts['channel']    # [视频信息] keywords

            file_path = Path(OUTPUT_VIDEOINFO_DIR) / OUTPUT_VIDEOINFO_FILENAME.format(target)
            save_to_json(video_info.dict_info_all(), file_path)

            # 视频下载
            self._download_video(target ,video_src)

        except Exception as e:
            logger.exception(f"视频处理异常:{e}")
            raise 

    def _parse_video_data(self, html_content):
        """解析 HTML 提取标题、点赞数、播放量等"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            # 获取title
            title_tag = soup.find("title")
            title  = title_tag.text.strip() if title_tag else "无标题"

            # 获取channel
            channel_tag = soup.find('a', class_='li-on')
            channel = channel_tag.get_text() if channel_tag else "未知频道"

            # 获取视频链接
            video_tag = soup.find('video', class_='vjs-tech')
            video_src = video_tag['src'] if video_tag else None

            # 输出提取的信息
            video_data = {
                "title":title,
                "channel":channel,
                "video_url":video_src
            }

            logger.info(f"视频信息提取成功")
            return video_data

        except Exception as e:
            logger.error(f"解析 HTML 失败: {e}")
            return None

    def _download_video(self, target, download_url: str):
        try:
            file_name = OUTPUT_VIDEOMP4_FILENAME.format(target)
            file_dir = OUTPUT_VIDEOMP4_DIR

            refer = download_url

            # 调用 VideoDownloader 下载视频
            logger.info(f"开始下载视频: {download_url}")
            self.video_downloader.download_video_stealth(download_url, file_dir, file_name, referer=refer)
            logger.info(f"视频 {target} 下载完成！")

        except requests.exceptions.RequestException as e:
            logger.error(f"下载失败: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"视频下载异常: {e}")
            raise


# 该文件有一个旧版本备份，路径为ku6_crawler_v1.0.py

# 测试实例
# ku6 网没有search功能，因此必须提供视频ID
# ku6 视频网网速较慢，视频下载需要等待
# 命令行输入：python -m core.ku6_crawler

if __name__ == "__main__":
    def test_search():
        """正常搜索测试"""
        try:
            crawler = ku6Crawel()
            crawler.crawl("video", "ni0ugYAYIldNml76-_y8x-W8Hjk")
            print("测试成功完成")
            return True
        except Exception as e:
            print(f"测试失败: {str(e)}")
            return False

    # 执行测试
    print("--- 执行正常搜索测试 ---")
    test_search()




