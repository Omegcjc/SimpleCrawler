import os
import json
from tqdm import tqdm  # 进度条支持
from time import sleep
from pathlib import Path
from typing import Optional, Dict, List
import subprocess

import re
import time
import requests
from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError
from bs4 import BeautifulSoup

from tools.video_down_wget import VideoDownloader
from tools.scraper_utils import dynamic_scroll
from tools.file_tools import save_to_json, debug_help

from config.config import *
from config.BaseConfig import BrowerConfig, VIDEO_INFO_ALL
from config.ifengConfig import * # 大写常量

logger = logging.getLogger(__name__)


DEBUG = 1

class ifengClient:
    def __init__(self, headless: bool = True):
        self.headless = headless

        self.p: Optional[sync_playwright] = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def start_browser(self):
        try:
            self.p = sync_playwright().start() 
            self.browser = self.p.chromium.launch(
                channel="chrome",
                headless= self.headless,
                args=BrowerConfig.get_chromium_args()
            )
            headers = BrowerConfig.get_headers(BASE_URL)
            self.context = self.browser.new_context(
                accept_downloads = True,
                user_agent=headers["User-Agent"],
                extra_http_headers=headers["extra_http_headers"]
            )

            # 反反爬对应的JavaScript
            if STEALTH_JS_PATH:
                self.context.add_init_script(path = STEALTH_JS_PATH)
            
            self.page = self.context.new_page()
            # self.page.evaluate("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            logger.error(f"浏览器启动失败，错误: {str(e)}")
    
    def end_browser(self):
            # 按逆序关闭资源
        if self.page is not None:
            self.page.close()
        if self.context is not None:
            self.context.close()
        if self.browser is not None:
            self.browser.close()
        if self.p is not None:
            self.p.stop()

class ifengcrawel:
    def __init__(self, headless: bool = True):

        self.client = ifengClient(headless=headless)
        self.video_downloader = VideoDownloader()  # 初始化视频下载器

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
        
        self.client.start_browser()
        self.page = self.client.page

        try:
            if mode == "search":
                self._process_search(target)
                
            elif mode == "video":
                self._process_video_has_ID(target)
            
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

                # 访问单个视频对应链接
                href_link = video['href']
                self._pre_page_handle(href_link)

                element = self.page.evaluate("allData()")
                with open("1.txt", "w", encoding="utf_8") as f:
                    f.write(element)

                debug_help(True)

                html_content = self.page.content()
                # 使用正则表达式，在当前page的html中精确匹配对应的ID
                target_ID =  self._extract_ID_with_re_in_htmlcontent(html_content)

                # 有ID则使用_process_video_has_ID进行信息提取，直接通过ID对视频信息提取
                # 无ID则使用_process_video_no_ID进行信息提取，直接对当前界面进行信息提取
                if target_ID:
                    self._process_video_has_ID(target_ID)
                else:
                    fake_ID = f"Unknown{idex + 1}ID_{target}"
                    self._process_video_no_ID(fake_ID)
                
                
                # print(f'{href_link}\nID:{target_ID}\n\n')
                # video_elements = self.page.query_selector_all('video[id^="player"][src]')
                # if video_elements:
                #     main_video = self.page.query_selector('div.index_ifeoCore_ >> video#player[src]')
                #     if main_video:
                #         raw_src = main_video.get_attribute('src')
                #         clean_src = f"https:{raw_src}" if not raw_src.startswith("http") else raw_src
                #     else:
                #         # 备用方案：正则表达式提取
                #         page_content = self.page.content()
                #         src_match = re.search(r'src="(https?://video[\d/\.]+[^"]+)"', page_content)
                #         clean_src = src_match.group(1) if src_match else None
                # else:
                #     clean_src = None
                #     logger.debug("视频src提取异常，请检查代码")
                
            debug_help(True)


        except Exception as e:
            logger.error(f"发生错误：{e}")
            raise
      
    def _extract_ID_with_re_in_htmlcontent(html_content: str, pattern: str = None):
        pattern_inner = r"""
                var\s+articelBase62Id   # 变量声明
                \s*=\s*                 # 等号及可能存在的空格
                ["']                    # 引号开始
                ([a-zA-Z0-9]{11})       # 精确匹配11位字母数字
                ["']                    # 引号结束
            """
        if not pattern:
            pattern = pattern_inner

        try:
            match = re.search(pattern, html_content, re.VERBOSE)
            target_ID =  match.group(1) if match else None
            return target_ID
        except Exception as e:
            logger.error(f"ID提取异常: {str(e)}")
            raise

    def _extract_src_with_re_in_htmlcontent(html_content: str, pattern: str = None):
        
        pattern_inner = r'src="(https?://video[\d/\.]+[^"]+)"'
        if not pattern:
            pattern = pattern_inner
        
        try:
            src_match = re.search(pattern, html_content)
            clean_src = src_match.group(1) if src_match else None
            return clean_src
        except Exception as e:
            logger.error(f"src提取异常: {str(e)}")
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
        
    def _process_video_has_ID(self, target: str):

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
                print("未找到页面数据")
            

            with open('output.json', 'w', encoding='utf-8') as f:
                # f.write(str(all_data))
                json.dump(all_data, f, ensure_ascii=False, indent=2)

            debug_help(True)

            html_content = self.page.content()
            video_data_parts = self._parse_video_data_has_ID(html_content)

            # 以下为获取视频下载src对应的URL，并且使用wget下载视频
            ## 使用组合选择器提高稳定性（class选择器+标签选择器）
            selector = "video.vjs-tech"
            ## 显式等待元素加载
            self.page.wait_for_selector(
                selector,
                state="attached",
                timeout=15000
            )
            
            ## 获取视频元素并验证属性存在性
            video_element = self.page.query_selector(selector)
            if not video_element:
                raise ValueError("视频元素未找到")
                
            ## 提取src属性（带空值检查）
            video_src = video_element.get_attribute("src")
            if not video_src:
                raise ValueError("视频源地址为空")
            
            ## 视频下载
            self._download_video(target ,video_src)

            # 保存信息
            video_info.video_url = video_url                # [视频信息] video_url - 直达视频的URL
            video_info.download_url = video_src             # [视频信息] download_url - 视频源地址
            video_info.views = video_data_parts['views']    # [视频信息] views - 播放量
            video_info.likes = video_data_parts['likes']    # [视频信息] likes - 支持数 / 点赞数 / 热度值
            video_info.title = video_data_parts['title']    # [视频信息] title - 视频标题
            video_info.desc = video_data_parts['brief']     # [视频信息] brief - 简介，可以为None
            video_info.author = video_data_parts['source']  # [视频信息] source - 可能为作者，可能为来源地
            video_info.duration = video_data_parts['duration']# [视频信息] duration - 视频时长
            video_info.publish_date = video_data_parts['createdate']# [视频信息] createdate - 发布时间

            file_path = Path(OUTPUT_VIDEOINFO_DIR) / OUTPUT_VIDEOINFO_FILENAME.format(target)
            save_to_json(video_info.dict_info_all(), file_path)
        except Exception as e:
            logger.exception("视频处理异常:{e}")
            raise 

    def _process_video_no_ID(self, target:str):

        video_info = VIDEO_INFO_ALL()
        video_info.refresh_info(mode = 'all')       #重置所有内容

        # 固定内容赋值
        video_info.platform = PLATFORM              # [视频信息] 平台 - ifengConfig          
        video_info.base_url = BASE_URL              # [视频信息] base_url - ifengConfig
        video_info.id = None                        # [视频信息] id = None
        video_info.video_url = None                 # [视频信息] 因为id = None,所以video_url = None

        html_content = self.page.content()
        self._parse_video_data_no_ID(html_content)
        
        # 以下为获取视频下载src对应的URL，并且使用wget下载视频
        video_src = self._extract_src_with_re_in_htmlcontent(html_content)
        if not video_src:
                raise ValueError("视频源地址为空")
        
        ## 视频下载
        self._download_video(target ,video_src)

    def _parse_video_data_has_ID(self, html_content):
        """解析 HTML 提取标题、点赞数、播放量等"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 获取标题
            title_tag = soup.find("title")
            title = title_tag.text.strip() if title_tag else "未知标题"

            # 获取视频简介
            brief_tag = soup.find("div", class_ = lambda x: x and "index_brief" in x)
            video_brief = brief_tag.text.strip() if brief_tag else None

            # 获取点赞数
            support_count_tag = soup.find("em", id="js_supportCount")
            support_count = support_count_tag.text.strip() if support_count_tag else "0"

            # 获取播放量
            info_tag = soup.find("div", class_=lambda x: x and "index_info" in x)
            if info_tag:
                create_tag = info_tag.find("span", class_=lambda x: x and "index_creatDate" in x)
                create_date = create_tag.text.strip() if create_tag else None

                duration_tag = info_tag.find('span', class_=lambda x: x and "index_duration" in x)
                duration_time = duration_tag.text.strip() if duration_tag else None

                play_count_tag = info_tag.find('span', class_=lambda x: x and "index_playNum" in x)
                play_count = play_count_tag.text.strip() if play_count_tag else "0"

                source = [span.get_text(strip=True) for span in info_tag.find_all("span") 
                         if not span.get("class")][0] 

            # 输出提取的信息
            video_data = {
                "title": title,
                "brief": video_brief,
                "createdate": create_date,
                "duration": duration_time,
                "source":source,
                "likes": support_count,
                "views": play_count
            }

            logger.info(f"视频信息提取成功")
            return video_data

        except Exception as e:
            logger.error(f"解析 HTML 失败: {e}")
            return None

    def _parse_video_data_no_ID(self, html_content):
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 获取标题
            title_tag = soup.find("title")
            title = title_tag.text.strip() if title_tag else "未知标题"

            author_tag = soup.find("div", class_ = lambda x: x and "index_videoInfoName" in x)
            author = author_tag.text.strip() if author_tag else None

            playnum_tag = soup.find("div", class_ = lambda x: x and "index_readNum" in x)


        except Exception as e:
            logger.error(f"解析 HTML 失败: {e}")
            return None        

    def _download_video(self, target, download_url: str):
        try:
            file_name = OUTPUT_VIDEOMP4_FILENAME.format(target)
            file_dir = OUTPUT_VIDEOMP4_DIR

            # 调用 VideoDownloader 下载视频
            logger.info(f"开始下载视频: {download_url}")
            self.video_downloader.download_video_wget(download_url, file_dir, file_name)
            logger.info(f"视频 {target} 下载完成！")

        except requests.exceptions.RequestException as e:
            logger.error(f"下载失败: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"视频下载异常: {e}")
            raise



# 测试实例
if __name__ == "__main__":
    def test_search():
        """正常搜索测试"""
        try:
            crawler = ifengcrawel(headless=False)
            crawler.crawl("video", "8i4RkJ6WgdM")
            print("搜索测试成功完成")
            return True
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            return False

    # 执行测试
    print("--- 执行正常搜索测试 ---")
    test_search()




