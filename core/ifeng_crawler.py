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
from config.ifengConfig import * # 大写常量

logger = logging.getLogger(__name__)

class IfengCrawel:
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
        try:
            # 根据target进行搜索
            search_url = SEARCH_URL.format(target)
            self._pre_page_handle(search_url)

            # 转到视频界面，并提取所有视频src,返回List[results]和视频数量
            results, length = self._process_search_to_videolist(target)

            # 爬取视频数量，
            if length > self.max_video_num:
                results = results[:self.max_video_num]
            
            for idex, video in enumerate(results):
                logger.info(f"======第{idex+1}个视频开始处理======")
                # 访问单个视频对应链接
                href_link = video['href']
                self._pre_page_handle(href_link)

                all_data = self.page.evaluate('''() => {
                    return allData || {};
                }''')

                ID = all_data['docData']['base62Id']
                if ID:
                    self._process_video(ID)
                    logger.info(f"======第{idex+1}个视频处理完成======")
                else:
                    logger.error(f"******第{idex+1}个视频处理异常******")
                    continue # 等全部处理完
        except Exception as e:
            logger.error(f"发生错误：{e}")
            raise
      
    def _process_search_to_videolist(self, target: str):
        '''
        self._process_search函数的增加模块,
        主要用于凤凰网搜索视频初步提取和保存
        返回提取内容列表和提取内容数

        results, len(results)
        '''
        try:
            # 等待 "视频" Tab 元素加载, 转到视频搜索结果界面
            video_tab_selector = "span:has-text('视频')"  # 选择器
            self.page.wait_for_selector(video_tab_selector, timeout=10000)  # 等待元素出现
            self.page.click(video_tab_selector)
            dynamic_scroll(self.page, 1)
            #  self.page.wait_for_load_state("networkidle")  # 等待页面加载完成
            if "视频" in self.page.inner_text("div.index_tabBoxInner_kSu3K"):
                logger.info("成功切换到 '视频' 页面")
            
            # 新增提取逻辑
            results = []
            
            # 基于图片结构的精准定位器
            container_selector = "div.news-stream-newsStream-news-item-infor"
            link_selector = f"{container_selector} h2 a[href]"
            
            # 提取所有目标元素
            elements = self.page.query_selector_all(link_selector)
            
            for idx, element in enumerate(elements, 1):
                # 处理特殊编码的href
                raw_href = element.get_attribute("href")
                
                # 智能补全URL
                if raw_href.startswith("//"):
                    full_href = f"https:{raw_href}" if not raw_href.startswith("//") else f"https://{raw_href[2:]}"
                else:
                    logger.error(f"错误url:{raw_href}")
                    continue
                
                # 清理title中的HTML标签
                dirty_title = element.get_attribute("title") or ""
                clean_title = "".join(dirty_title.split("<em>")).replace("</em>", "").strip()
                
                results.append({
                    "href": full_href,  
                    "title": clean_title
                })

            logger.info(f"提取到 {len(results)} 个视频资源 | 示例：{results[:1] if results else '无结果'}")

            file_path = Path(OUTPUT_VIDEOLIST_DIR) / OUTPUT_VIDEOLIST_FILENAME.format(target)
            save_to_json(results, file_path)
            return results, len(results)
        except Exception as e:
            logger.error(f"发生错误parse_search_addtion:{e}")
            raise
        
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
                return allData || {};
            }''')

            if not all_data:
                logger.error("未找到页面数据")
                raise

            docData = all_data['docData'] if "docData" in all_data else {}
            title = docData['title'] if 'title' in docData else "无标题"
            time = docData['newsTime'] if 'newsTime' in docData else None
            video_src = docData['videoPlayUrl'] if 'videoPlayUrl' in docData else None
            author = docData['subscribe']['catename'] if 'subscribe' in docData and 'catename' in docData['subscribe'] else None
            desc = docData['summary'] if 'summary' in docData else None
            duration = docData['duration'] if "duration" in docData else None
            keywords = docData['keywords'] if 'keywords' in docData else None

            # 得到播放量和点赞量
            html_content = self.page.content()
            video_data_parts = self._parse_video_data(html_content)

            video_src = docData['videoPlayUrl']
            if not video_src:
                raise ValueError("视频源地址为空")

            # 保存信息
            video_info.video_url = video_url                # [视频信息] video_url - 直达视频的URL
            video_info.download_url = video_src             # [视频信息] download_url - 视频源地址
            video_info.views = video_data_parts['views']    # [视频信息] views - 播放量
            video_info.likes = video_data_parts['likes']    # [视频信息] likes - 支持数 / 点赞数 / 热度值
            video_info.title = title                        # [视频信息] title - 视频标题
            video_info.desc = desc                          # [视频信息] brief - 简介，可以为None
            video_info.author = author                      # [视频信息] source - 可能为作者，可能为来源地
            video_info.duration = duration                  # [视频信息] duration - 视频时长
            video_info.publish_date = time                  # [视频信息] createdate - 发布时间
            video_info.channel = keywords                   # [视频信息] keywords

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
            # 获取点赞数
            support_count_tag = soup.find("em", id="js_supportCount")
            support_count = support_count_tag.text.strip() if support_count_tag else "0"

            # 获取播放量
            info_tag = soup.find("div", class_=lambda x: x and "index_info" in x)
            if info_tag:
                play_count_tag = info_tag.find('span', class_=lambda x: x and "index_playNum" in x)
                play_count = play_count_tag.text.strip() if play_count_tag else "0"


            # 输出提取的信息
            video_data = {
                "likes": support_count,
                "views": play_count
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


# 该文件有一个旧版本备份，路径为beifen_ifeng_1.py

# 测试实例
# 命令行输入：python -m core.ifeng_crawler

if __name__ == "__main__":
    def test_search():
        """正常搜索测试"""
        try:
            crawler = IfengCrawel()
            crawler.crawl("search", "中东")
            print("搜索测试成功完成")
            return True
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            return False

    # 执行测试
    print("--- 执行正常搜索测试 ---")
    test_search()




