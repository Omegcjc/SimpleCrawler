import os
import json
from tqdm import tqdm  # 进度条支持
from time import sleep
from pathlib import Path
from typing import Optional, Dict, List

import requests
from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError
from bs4 import BeautifulSoup, Tag

from base.base_client import baseClient

from config.config import *
from config.BaseConfig import BrowerConfig, VIDEO_INFO_ALL
from config.bilibiliConfig import * # 大写常量

from tools.scraper_utils import dynamic_scroll, close_popups
from tools.file_tools import save_to_json, debug_help

logger = logging.getLogger(__name__)

class BilibiliCrawler:
    def __init__(self, headless: bool = True):

        self.client = baseClient(headless=headless)

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
        
        self.client.start_browser(BASE_URL, js_path="stealth.min.js", sessdata=SESSDATA)
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
                close_popups(self.page)
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
        """处理搜索逻辑"""
        try:
            # 初始化页面
            search_url = SEARCH_URL.format(target)
            self._pre_page_handle(search_url)

            # 找到搜索到的所有视频资源
            video_divs = self.page.query_selector_all('xpath=//div[contains(@class, "search-all-list")]')
            if not video_divs:
                raise ValueError("未找到视频列表元素，可能页面结构已变更")
            html_content = "\n".join([div.evaluate('elem => elem.outerHTML') for div in video_divs])

            # 提取并保存有效数据
            search_list, length = self._parse_search_data(html_content)
            file_path = Path(OUTPUT_VIDEOLIST_DIR) / OUTPUT_VIDEOLIST_FILENAME.format(target)
            save_to_json(search_list, file_path)

            if length > self.max_video_num:
                search_list = search_list[:self.max_video_num]

            # 对每一个视频提取有效数据并且下载视频
            for index, item in enumerate(search_list):

                logger.info(f"======[{PLATFORM}]第{index+1}个视频开始处理======")
                ID = item['id']
                if ID:
                    self._process_video(ID)
                    logger.info(f"======[{PLATFORM}]第{index+1}个视频处理完成======")
                else:
                    logger.error(f"******[{PLATFORM}]第{index+1}个视频处理异常******")
                    continue # 等全部处理完
        except Exception as e:
            logger.error(f"视频列表解析失败: {str(e)}")
            raise

    def _parse_search_data(self, html_content: str) -> List[Dict]:
        """数据解析模块，增加更详细的错误处理"""
        search_data_list = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            target_divs = soup.select('div.bili-video-card__info')
            if not target_divs: 
                raise ValueError("未找到视频卡片元素，可能页面结构已变更")

            for idx, video_info in enumerate(target_divs):
                try:
                    # 提取标题
                    title_tag = video_info.find('h3', class_='bili-video-card__info--tit')
                    if not title_tag:
                        logger.warning(f"第{idx+1}个视频未找到标题元素")
                        continue
                    title = title_tag.get('title', title_tag.get_text(strip=True)).replace('\n', ' ')
                    
                    # 提取URL
                    url_tag = video_info.find('a', href=True)
                    if not url_tag or not url_tag.get('href'):
                        logger.warning(f"第{idx+1}个视频未找到有效链接")
                        continue
                    url = f"https:{url_tag['href']}" if url_tag['href'].startswith('//') else url_tag['href']
                    
                    # 提取视频ID
                    try:
                        id = url.split('/')[-2]
                    except IndexError:
                        logger.warning(f"第{idx+1}个视频URL格式异常: {url}")
                        id = "unknown"

                    # 提取作者
                    author_tag = video_info.select_one('span.bili-video-card__info--author')
                    author = author_tag.get_text(strip=True) if author_tag else "未知作者"
                    
                    # 提取发布时间
                    date_tag = video_info.select_one('span.bili-video-card__info--date')
                    date = date_tag.get_text(strip=True).replace('·', '').strip() if date_tag else "未知时间"

                    video_data = {
                        "title": title,
                        "id": id,
                        "url": url,
                        "author": author,
                        "publish_date": date
                    }
                    search_data_list.append(video_data)
                except Exception as e:
                    logger.error(f"第{idx+1}个视频解析异常: {str(e)}")
                    continue
            return search_data_list, len(search_data_list)
        except Exception as e:
            logger.error(f"解析过程发生严重错误: {str(e)}")
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
            self._pre_page_handle(video_url)

            # 安全获取参数
            initial_state = self.page.evaluate('''() => {
                return window.__INITIAL_STATE__ || {};
            }''')

            if not initial_state:
                logger.error("未找到页面数据")
                raise

            # 获取aid和cid
            cid = initial_state.get('cid')
            aid = initial_state.get('aid')
            if not cid or not aid:
                raise ValueError("视频源地址为空")
            
            # 构造下载请求
            download_url = VIDEO_RES_URL.format(aid, cid)

            # 预处理initial_state
            video_data_parts = self._parse_video_data(initial_state) 

            # 保存信息
            video_info.video_url = video_url                        # [视频信息] video_url - 直达视频的URL
            video_info.download_url = download_url                  # [视频信息] download_url - 视频源地址

            video_info.likes = video_data_parts['likes']            # [视频信息] likes - 支持数 / 点赞数 / 热度值
            video_info.title = video_data_parts['title']            # [视频信息] title - 视频标题
            video_info.desc = video_data_parts['desc']              # [视频信息] brief - 简介，可以为None
            video_info.author = video_data_parts['owner']           # [视频信息] author - 可能为作者，可能为来源地
            video_info.duration = video_data_parts['duration']      # [视频信息] duration - 视频时长
            video_info.channel = video_data_parts['channel']        # [视频信息] channel - 频道，可能为keywords
            
            video_info.views = video_data_parts['views']            # [视频信息] views - 播放量
            video_info.likes = video_data_parts['likes']            # [视频信息] likes - 点赞量
            video_info.coins = video_data_parts['coins']            # [视频信息] coins - 投币量
            video_info.favs = video_data_parts['favs']              # [视频信息] favs - 收藏量
            video_info.shares = video_data_parts['shares']          # [视频信息] shares - 转发量

            json_file_path = Path(OUTPUT_VIDEOINFO_DIR) / OUTPUT_VIDEOINFO_FILENAME.format(target)
            save_to_json(video_info.dict_info_all(), json_file_path)

            # 下载并保存视频
            self._download_video(target, download_url,OUTPUT_VIDEOMP4_DIR)

        except KeyError as e:
            print(f"解析错误，请检查B站API变更: {str(e)}")
        except requests.exceptions.RequestException as e:
            print(f"下载失败: {str(e)}")
    
    def _parse_video_data(self, initial_state: Dict) -> List[Dict]:

        videodata = initial_state['videoData']

        if not videodata:
            logger.error(f"不是视频，请检查网页{self.page.url()}")
            raise

        # 视频对应ID
        bvid = videodata['bvid'] if 'bvid' in videodata else "NULL"                   
        
        # 视频频道(类别)
        channel_1 = videodata['tname'] if 'tname' in videodata else "NULL"            
        channel_2 = videodata['tname_v2'] if 'tname_v2' in videodata else "NULL"
        channel = channel_1 + '.' + channel_2 if channel_2 != 'NULL' else channel_1
        
        title = videodata['title'] if 'title' in videodata else "NULL"  
        desc = videodata['desc'] if 'desc' in videodata else "NULL"
        owner = videodata['owner']['name'] if 'owner' in videodata and 'name' in videodata['owner'] else 'NULL'
        duration = videodata['duration'] if 'duration' in videodata else "NULL"

        statdata = videodata['stat'] if 'stat' in videodata else 'NULL'
        if statdata != "NULL":
            view = statdata['view'] if 'view' in statdata else 'NULL'
            danmu = statdata['danmaku'] if 'danmaku' in statdata else 'NULL'
            like = statdata['like'] if 'like' in statdata else 'NULL'
            coin = statdata['coin'] if 'coin' in statdata else 'NULL'
            favorite = statdata['favorite'] if 'favorite' in statdata else 'NULL'
            share = statdata['share'] if 'share' in statdata else 'NULL'

        video_data = {
                        'title': title,
                        "bvid": bvid,
                        "channel":channel,
                        'owner':owner,
                        "desc": desc,
                        "duration":duration,

                        'views': view,
                        'danmu':danmu,
                        'likes': like,
                        'coins': coin,
                        'favs': favorite,
                        'shares': share
                    }
        return video_data

    def _download_video(self, target, download_url: str, save_dir: str = "./videos"):
        try:
            # 创建保存目录
            Path(save_dir).mkdir(exist_ok=True)

            # 获取视频信息
            self.page.goto(download_url)
            self.page.wait_for_selector('pre', timeout=10000)
            full_html = self.page.evaluate('''() => {
                const pre = document.querySelector('pre');
                return pre ? pre.textContent : '';
            }''')

            # 解析视频信息
            video_info = json.loads(full_html)
            video_data = video_info['data']
            
            # 选择最高清视频流
            video_url = video_data['dash']['video'][0]['baseUrl']

            # 设置下载头
            headers = {
                "Referer": video_url,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Origin": "https://www.bilibili.com"
            }

            # 流式下载实现
            response = requests.get(video_url, headers=headers, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            # 生成保存路径
            file_name = OUTPUT_VIDEOMP4_FILENAME.format(target)
            file_path = Path(save_dir) / file_name

            # 带进度条的下载
            with open(file_path, 'wb') as f, tqdm(
                desc=file_name,
                total=total_size,
                unit='iB',
                unit_scale=True
            ) as bar:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    size = f.write(chunk)
                    bar.update(size)

            logger.info(f"视频已保存至：{file_path}")

        except KeyError as e:
            logger.error(f"解析错误，请检查B站API变更: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"下载失败: {str(e)}")




# 测试实例
# 对于视频的下载还是存在问题，请谨慎使用
# 命令行输入：python -m core.bili_crawler
if __name__ == "__main__":
    def test_search():
        """正常搜索测试"""
        try:
            crawler = BilibiliCrawler(headless=True)
            crawler.crawl("search", "特朗普")
            print("搜索测试成功完成")
            return True
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            return False


    # 执行测试
    # print("--- 执行正常搜索测试 ---")
    # test_search()

    def crawler_use_id():

        all_id=[ 
            "BV1pooRYkEWx",
            "BV1zTQPYLEE4",
            "BV1RsZVYjEXr",
            "BV1D7ZtY7Er9",
            "BV16NNneZEB6",
            "BV1FBZjYNEYj",
            "BV1wM9RYvEWK",
            "BV1FaQtY7Eji",
            "BV1it9mYBEXV",
            "BV1aL92YoEEe"
        ]# 总共十个视频

        for index, item in enumerate(all_id):
            try:
                print(f"第{index + 1}个video:{item}开始处理")
                crawler = BilibiliCrawler(headless=True)
                crawler.crawl("video", item)
                print(f"第{index + 1}个video:{item}成功完成")
            except Exception as e:
                print(f"第{index + 1}个video:{item}处理异常")
                pass
        
    crawler_use_id()





