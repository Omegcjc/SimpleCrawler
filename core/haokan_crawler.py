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
from fake_useragent import UserAgent

from base.base_client import baseClient

from tools.video_down_wget import VideoDownloader
from tools.scraper_utils import dynamic_scroll
from tools.file_tools import save_to_json, debug_help

from config.config import *
from config.BaseConfig import BrowerConfig, VIDEO_INFO_ALL
from config.haokanConfig import * # 大写常量,注意在copy时其修改为正确的配置文件

# 配置日志
logger = logging.getLogger(__name__)

class HaokanCrawler:
    """好看网爬虫"""
    def __init__(self, headless: bool = True):
        self.client = baseClient(headless=headless)
        self.video_downloader = VideoDownloader()

        self.max_retries = 3
        self.max_video_num = MAX_VIDEO_NUM
        self.page: Page = None
        self.user_agents = UserAgent().random
    
    def crawl(self, mode: str, target: str):
        """统一入口方法"""
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

    def _pre_page_handle(self, url, scroll_times = 2):
        """页面预处理与重试机制"""
        retries = 0
        while retries < self.max_retries:
            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(2)
                dynamic_scroll(self.page, scroll_times=scroll_times)
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
        """处理搜索流程"""
        try:
            search_url = SEARCH_URL.format(target)
            self._pre_page_handle(search_url)

            result_list = self._process_search_to_list(target)

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
        """处理搜索结果为列表"""
        try:
            result_list = []
            list_items = self.page.query_selector_all('.list-container.videolist')
            
            for item in list_items:
                try:
                    href = item.get_attribute('href')
                    if not href:
                        continue
                    
                    vid = href.split('vid=')[-1]
                    title_element = item.query_selector('.list-body strong')
                    title = title_element.inner_text().strip() if title_element else "无标题"
                    title = ' '.join(title.split())

                    result_list.append({
                        'ID': vid,
                        'title': title
                    })
                except Exception as e:
                    logger.error(f"解析视频项时出错: {str(e)}")
                    continue

            file_name = OUTPUT_VIDEOLIST_FILENAME.format(target)
            file_path = Path(OUTPUT_VIDEOLIST_DIR) / file_name
            save_to_json(result_list, file_path)

            logger.info(f"搜索关键词为：{target}, 总共得到{len(result_list)}条数据")
            return result_list
            
        except Exception as e:
            logger.error(f"处理搜索结果列表时出错: {str(e)}")
            raise
     
    def _process_video(self, target: str):
        """处理视频详情页"""
        video_info = VIDEO_INFO_ALL()
        video_info.refresh_info(mode='all')

        video_info.platform = PLATFORM
        video_info.base_url = BASE_URL
        video_info.id = target

        try:
            video_url = VIDEO_URL.format(target)
            self._pre_page_handle(video_url)

            html_content = self.page.content()
            
            # debug_file = Path("./debug") / f"haokanvideo_{target}.html"
            # debug_file.parent.mkdir(parents=True, exist_ok=True)
            # with open(debug_file, "w", encoding="utf-8") as f:
            #     f.write(html_content)
                
            soup = BeautifulSoup(html_content, "html.parser")
            
            video_element = soup.find("video")
            if not video_element:
                logger.warning("未找到视频元素,可能不是视频页面")
                return False
                
            video_src = video_element.get("src")
            if not video_src:
                raise ValueError("视频源地址为空")
                
            title_element = soup.find("meta", {"itemprop": "name"})
            title = title_element.text.strip() if title_element else "无标题"
            
            desc_element = soup.find("meta", {"itemprop": "description"})
            desc = desc_element.text.strip() if desc_element else None
            
            author_element = soup.find("div", class_="videoinfo-author-name")
            author = author_element.text.strip() if author_element else None
            
            time_element = soup.find("span", class_="videoinfo-playtime")
            publish_time = time_element.text.strip() if time_element else None
            
            duration_element = soup.find("span", class_="duration")
            duration = duration_element.text.strip() if duration_element else None
            
            keywords_meta = soup.find("meta", {"itemprop": "keywords"})
            channel = keywords_meta["content"].split(',')[0].strip() if keywords_meta else None
            
            video_data = self._parse_video_data(html_content)
            
            video_info.video_url = video_url
            video_info.download_url = video_src
            video_info.title = title
            video_info.desc = desc
            video_info.author = author
            video_info.duration = duration
            video_info.publish_date = publish_time
            video_info.channel = channel
            video_info.likes = video_data['likes']
            video_info.views = video_data['views']

            file_path = Path(OUTPUT_VIDEOINFO_DIR) / OUTPUT_VIDEOINFO_FILENAME.format(target)
            save_to_json(video_info.dict_info_all(), file_path)

            self._download_video(target, video_src)

        except Exception as e:
            logger.exception(f"视频处理异常:{e}")
            raise 

        return True

    def _parse_video_data(self, html_content):
        """从HTML中解析视频数据"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            extrainfo = soup.find("div", class_="extrainfo")
            
            if extrainfo:
                playnums_div = extrainfo.find("div", class_="extrainfo-playnums")
                views = "0"
                if playnums_div:
                    import re
                    views_match = re.search(r'(\d+(?:\.\d+)?)(万)?次播放', playnums_div.text)
                    if views_match:
                        number = float(views_match.group(1))
                        if views_match.group(2) == "万":
                            number = number * 10000
                        views = str(int(number))

                likes_div = extrainfo.find("div", class_="extrainfo-zan")
                likes = "0"
                if likes_div:
                    likes_text = likes_div.text.strip()
                    likes_match = re.search(r'(\d+(?:\.\d+)?)(万)?', likes_text)
                    if likes_match:
                        number = float(likes_match.group(1))
                        if likes_match.group(2) == "万":
                            number = number * 10000
                        likes = str(int(number))

                return {"likes": likes, "views": views}

            return {"likes": "0", "views": "0"}

        except Exception as e:
            logger.error(f"解析视频数据失败: {str(e)}")
            return {"likes": "0", "views": "0"}

    def _download_video(self, target, download_url: str):
        """下载视频"""
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

# 测试实例
# 命令行输入：python -m core.haokan_crawler

if __name__ == "__main__":
    def test_search():
        """正常搜索测试"""
        try:
            crawler = HaokanCrawler()
            crawler.crawl("search", "特朗普")
            print("搜索测试成功完成")
            return True
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            return False

    # 执行测试
    print("--- 执行正常搜索测试 ---")
    test_search()
