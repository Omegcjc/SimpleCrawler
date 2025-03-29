import os
import json
from tqdm import tqdm  # 进度条支持
from time import sleep
from pathlib import Path
from typing import Optional, Dict, List

import time
import requests
from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError
from bs4 import BeautifulSoup, Tag

from base.base_client import baseClient

from tools.video_down_wget import VideoDownloader
from tools.scraper_utils import dynamic_scroll
from tools.file_tools import save_to_json, debug_help

from config.config import *
from config.BaseConfig import BrowerConfig, VIDEO_INFO_ALL
from config.thepaperConfig import * # 大写常量

logger = logging.getLogger(__name__)

class thepapercrawel:
    def __init__(self, headless: bool = True):

        self.client = baseClient(headless=headless)
        self.video_downloader = VideoDownloader()
        self.max_retries = 3  # 最大重试次数
        self.max_video_num = MAX_VIDEO_NUM #search后爬取最大视频数
        self.page : Page

    def crawl(self, mode: str, target: str):
        """统一入口方法，增加参数校验"""
        mode = mode.lower()
        if mode not in ["search", "video"]:
            raise ValueError(f"无效模式: {mode}，支持模式: 'search'/'video'")
        
        target = target.strip()
        if not target:
            raise ValueError(f"无效target: {target}，请输入与模式对应的target")
        
        self.client.start_browser(BASE_URL)
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

    def _pre_page_handle(self, url, scroll_times = 5):
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
                raise

    def _process_search(self, target: str):
        try:
            # 根据target进行搜索
            search_url = SEARCH_URL.format(target)
            self._pre_page_handle(search_url) # 默认澎湃新闻网增加了自动滑动屏幕的次数 -> 5次

            result_list =  self._process_search_to_list(target)

            video_num = 0
            for idex, result in enumerate(result_list):

                if video_num >= self.max_video_num:
                    break
                logger.info(f"======第{idex+1}个视频/新闻开始处理======")
                try:
                    target_ID = result['ID']
                    is_video = self._process_video(target_ID)
                    if not is_video:
                        logger.info(f"======第{idex+1}个不是视频，停止处理======")
                    else:
                        logger.info(f"======第{idex+1}个是视频，处理完成======")
                        video_num += 1
                except Exception as e:
                    logger.error(f"======第{idex+1}个视频/新闻处理异常======")
                    pass
        except Exception as e:
            logger.error(f"发生错误：{e}")
            raise            
        
    def _process_search_to_list(self, target):

        result_list = []
        list_items = self.page.query_selector_all('[class*="index_searchresult"] ul li')  # 模糊匹配包含关键字的class
        for li in list_items:
            try:
                # 提取链接元素
                card = li.query_selector('.mdCard')
                if not card:
                    continue
                
                a_tag = card.query_selector('a[href]')
                if not a_tag:
                    continue

                # 处理相对路径
                raw_href = a_tag.get_attribute('href').strip()
                ID = raw_href.split("_")[2]
                
                # 提取标题文本并清理格式
                h2 = a_tag.query_selector('h2')
                if h2:
                    # 移除所有HTML标签只保留文本
                    title = h2.inner_text().strip()
                    # 合并连续空格和换行符
                    title = ' '.join(title.split())
                else:
                    title = "无标题"

                result_list.append({
                    'ID': ID,
                    'title': title
                })
            except Exception as e:
                print(f"解析元素时出错: {str(e)}")
                continue

        file_name = OUTPUT_VIDEOINFO_FILENAME.format(target)
        file_path = Path(OUTPUT_VIDEOLIST_DIR) / file_name

        save_to_json(result_list, file_path)
        logger.info(f"搜索关键词为：{target}, 总共得到{len(result_list)}条数据")
        return result_list
    
    def _process_video(self, target: str):
        video_info = VIDEO_INFO_ALL()
        video_info.refresh_info(mode = 'all')       #重置所有内容

        # 固定内容赋值
        video_info.platform = PLATFORM              # [视频信息] 平台 - ifengConfig          
        video_info.base_url = BASE_URL              # [视频信息] base_url - ifengConfig
        video_info.id = target                      # [视频信息] id = target

        try:
            # 初始化页面
            video_url = VIDEO_URL.format(target)
            self._pre_page_handle(video_url)  # 确保包含页面加载等待逻辑

            all_data = self.page.evaluate('''() => {
                return window.__NEXT_DATA__ || {};
            }''')

            if not all_data:
                logger.error("未找到页面数据")
                raise

            ContentDetail = all_data["props"]["pageProps"]["detailData"]["contentDetail"]

            videos = ContentDetail["videos"] if "videos" in ContentDetail else {}

            if not videos:
                return False
            
            ID = ContentDetail["contId"] if "contId" in ContentDetail else target
            title = ContentDetail["name"] if "name" in ContentDetail else "无标题"
            desc = ContentDetail["summary"] if "summary" in ContentDetail else None
            keywords = ContentDetail["trackKeyword"] if "trackKeyword" in ContentDetail else None
            author = ContentDetail["author"] if "author" in ContentDetail else None
            time = ContentDetail["pubTime"] if "pubTime" in ContentDetail else None
            channel = ContentDetail["tags"] if "tags" in ContentDetail else None

            video_src = videos["url"] if "url" in videos else None
            duration = videos["duration"] if "duration" in videos else None

            html_content = self.page.content()
            
            # 获取点赞数
            video_data_parts = self._parse_video_data(html_content)


            if not video_src:
                raise ValueError("视频源地址为空")
            
            # 保存信息
            video_info.video_url = video_url                # [视频信息] video_url - 直达视频的URL
            video_info.download_url = video_src             # [视频信息] download_url - 视频源地址
            # video_info.views = video_data_parts['views']    # [视频信息] views - 播放量
            video_info.likes = video_data_parts['likes']    # [视频信息] likes - 支持数 / 点赞数 / 热度值
            video_info.title = title                        # [视频信息] title - 视频标题
            video_info.desc = desc                          # [视频信息] brief - 简介，可以为None
            video_info.author = author                      # [视频信息] source - 可能为作者，可能为来源地
            video_info.duration = duration                  # [视频信息] duration - 视频时长
            video_info.publish_date = time                  # [视频信息] createdate - 发布时间
            video_info.channel = channel                   # [视频信息] keywords

            file_path = Path(OUTPUT_VIDEOINFO_DIR) / OUTPUT_VIDEOINFO_FILENAME.format(target)
            save_to_json(video_info.dict_info_all(), file_path)

            # 视频下载
            self._download_video(target ,video_src)

        except Exception as e:
            logger.exception(f"视频处理异常:{e}")
            raise 

        return True

    def _parse_video_data(self, html_content):
        '''获取点赞数'''
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 获取点赞数
            likes_tag = soup.find("div", lambda x: x and "praiseNum" in x)
            likes = likes_tag.text.strip() if likes_tag else "0"

            return {
                "likes":likes
            }


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


if __name__ == "__main__":
    def test_search():
        """正常搜索测试"""
        try:
            crawler = thepapercrawel(headless = True)
            crawler.crawl("search", "特朗普")
            print("搜索测试成功完成")
            return True
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            return False

    # 执行测试
    print("--- 执行正常搜索测试 ---")
    test_search()