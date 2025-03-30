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
from config.BaseConfig import BrowerConfig
from config.bilibiliConfig import * # 大写常量

from tools.scraper_utils import dynamic_scroll, close_popups

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
        """处理搜索逻辑，增加重试机制"""
        # 初始化页面
        search_url = SEARCH_URL.format(target)
        self._pre_page_handle(search_url)

        sleep(200)

        try:
            video_divs = self.page.query_selector_all('xpath=//div[contains(@class, "search-all-list")]')
            if not video_divs:
                raise ValueError("未找到视频列表元素，可能页面结构已变更")
            html_content = "\n".join([div.evaluate('elem => elem.outerHTML') for div in video_divs])

            # 提取有效数据
            search_list = self._parse_search_data(html_content)
            self._save_list_json(search_list, OUTPUT_VIDEOLIST_FILENAME.format(target), OUTPUT_VIDEOLIST_DIR)

            # 对每一个视频提取有效数据并且下载视频
            for index, item in enumerate(search_list):
                if index >= self.max_video_num:
                    return
                id = item['id']
                self._process_video(id)
                logger.info(f"search-{target} - 第{index+1}个视频爬取完成")
                
        except Exception as e:
            logger.error(f"视频列表解析失败: {str(e)}")
            raise

    def _process_video(self, target: str):
        try:
            # 初始化页面
            video_url = VIDEO_URL.format(target)
            self._pre_page_handle(video_url)

            # 旧方法 _parse_video_data 使用 code
            # html_content = self.page.content()
            # video_info_list = self._parse_video_data(html_content)
            # self._save_list_json(video_info_list, OUTPUT_VIDEOINFO_FILENAME.format(target), OUTPUT_VIDEOINFO_DIR)

            
            # 安全获取参数
            initial_state = self.page.evaluate('''() => {
                return window.__INITIAL_STATE__ || {};
            }''')

            video_info_list = self._parse_video_data(initial_state)
            self._save_list_json(video_info_list, OUTPUT_VIDEOINFO_FILENAME.format(target), OUTPUT_VIDEOINFO_DIR)


            # # DEBUG 专用部分 code 
            # with open("initial_data.txt","w",encoding="utf_8") as f:
            #     for item in initial_state.items():
            #         f.write(str(item) + "\n\n")


            # 双重验证机制
            if not (cid := initial_state.get('cid')) or not (aid := initial_state.get('aid')):
                # 备用API获取方式
                api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={target}"
                resp = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                video_data = resp.json()['data']
                cid = video_data['cid']
                aid = video_data['aid']

            # 构造下载请求
            download_url = VIDEO_RES_URL.format(aid, cid)
            # 下载并保存视频
            self._download_video(target, download_url,OUTPUT_VIDEOMP4_DIR)

        except KeyError as e:
            print(f"解析错误，请检查B站API变更: {str(e)}")
        except requests.exceptions.RequestException as e:
            print(f"下载失败: {str(e)}")
    
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

            print(f"视频已保存至：{file_path}")

        except KeyError as e:
            print(f"解析错误，请检查B站API变更: {str(e)}")
        except requests.exceptions.RequestException as e:
            print(f"下载失败: {str(e)}")

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
            return search_data_list
        except Exception as e:
            logger.error(f"解析过程发生严重错误: {str(e)}")
            raise

    def _parse_video_data(self, initial_state: Dict) -> List[Dict]:
        video_data_list = []

        videodata = initial_state['videoData']

        # 视频对应ID
        bvid = videodata['bvid'] if 'bvid' in videodata else "NULL"                   
        
        # 视频频道(类别)
        channel_1 = videodata['tname'] if 'tname' in videodata else "NULL"            
        channel_2 = videodata['tname_v2'] if 'tname_v2' in videodata else "NULL"
        channel = channel_1 + '.' + channel_2 if channel_2 != 'NULL' else channel_1
        
        title = videodata['title'] if 'title' in videodata else "NULL"  
        desc = videodata['desc'] if 'desc' in videodata else "NULL"
        owner = videodata['owner']['name'] if 'owner' in videodata and 'name' in videodata['owner'] else 'NULL'

        statdata = videodata['stat'] if 'stat' in videodata else 'NULL'
        if statdata != "NULL":
            view = statdata['view'] if 'view' in statdata else 'NULL'
            danmu = statdata['danmaku'] if 'danmaku' in statdata else 'NULL'
            like = statdata['like'] if 'like' in statdata else 'NULL'
            coin = statdata['coin'] if 'coin' in statdata else 'NULL'
            favorite = statdata['favorite'] if 'favorite' in statdata else 'NULL'
            share = statdata['share'] if 'share' in statdata else 'NULL'

        video_data = {
                        "platform":PLATFORM,
                        "base_url":BASE_URL,
                        'title': title,
                        "bvid": bvid,
                        "channel":channel,
                        'owner':owner,
                        "desc": desc,

                        'views': view,
                        'danmu':danmu,
                        'likes': like,
                        'coins': coin,
                        'favs': favorite,
                        'shares': share
                    }
        video_data_list.append(video_data)
        return video_data

    ''' 视频处理旧方法
    def _parse_video_data(self, html_content: str) -> List[Dict]:
        """解析视频数据并返回结构化列表"""
        video_data_list = []
        
        try:
            # 创建解析对象
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找所有视频项容器（需根据实际HTML结构调整选择器）
            video_items = soup.find_all('div', class_='app-v1')  # 示例选择器，需替换实际class
            
            if not video_items:
                logging.warning("未找到视频数据容器")
                return []
                
            for item in video_items:
                if not isinstance(item, Tag):  # 确保是Tag对象
                    continue
                    
                try:
                    # 提取标题（添加默认值防止崩溃）
                    title_tag = item.find('h1', class_='video-title')
                    title = title_tag.text.strip() if title_tag else "无标题"
                    
                    # 提取播放量（添加类型检查）
                    views_tag = item.find('div', class_='view-text')
                    views = views_tag.text.strip() if isinstance(views_tag, Tag) else "0"
                    
                    # 结构化提取数字信息（使用辅助函数）
                    def get_item(tag_name: str, class_name: str) -> str:
                        tag = item.find(tag_name, class_=class_name)
                        return tag.text.strip() if tag else "NULL"
                    
                    video_data = {
                        "platform":PLATFORM,
                        "base_url":BASE_URL,
                        'title': title,
                        'views': views,
                        "desc": get_item('span', "desc-info-text"),
                        'likes': get_item('span', 'video-like-info'),
                        'coins': get_item('span', 'video-coin-info'),
                        'favs': get_item('span', 'video-fav-info'),
                        'shares': get_item('span', 'video-share-info-text')
                    }
                    
                    video_data_list.append(video_data)
                    
                except AttributeError as e:
                    logging.error(f"元素提取错误: {str(e)}")
                    continue
                except Exception as e:
                    logging.error(f"数据处理异常: {str(e)}")
                    continue
                    
        except Exception as e:
            logging.critical(f"解析器初始化失败: {str(e)}")
            return []
        
        return video_data_list
    '''

    def _save_list_json(self, data_list: List, filename: str, save_dir: str = "./data") -> None:

        try:
            # 路径处理（跨平台兼容）
            save_path = Path(save_dir)
            output_path = save_path / filename
            
            # 创建父目录（自动处理多级目录）
            save_path.mkdir(parents=True, exist_ok=True)
            
            # 执行保存操作
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data_list, f, 
                        ensure_ascii=False,  # 支持非ASCII字符[2,4
                        indent=2)         # 处理不可序列化对象
            
            logging.info(f"成功保存{len(data_list)}条数据到{output_path}")
            
        except (IOError, PermissionError) as e:
            error_msg = f"文件操作失败: {str(e)}"
            logging.error(error_msg)
            raise IOError(error_msg)

        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)


# 测试实例
if __name__ == "__main__":
    def test_search():
        """正常搜索测试"""
        try:
            crawler = BilibiliCrawler(headless=False)
            crawler.crawl("search", "特朗普")
            print("搜索测试成功完成")
            return True
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            return False

    # 执行测试
    print("--- 执行正常搜索测试 ---")
    test_search()
