import requests
import re
from lxml import etree
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from multiprocessing import Pool, Queue, Lock
import multiprocessing
import random
import time
import subprocess
import os
from playwright.sync_api import sync_playwright
from pprint import pprint
import logging

from datetime import datetime
from zoneinfo import ZoneInfo

from tools.screen_display import ScreenDisplay
from tools.file_tools import save_to_json
from base.base_config import VIDEO_INFO_ALL
from base.base_contentcrawler import ContentCrawler
from .xiaodu.baijiahao import baijiahao as bai_jia_hao
from .xiaodu.zhihu import zhihu as zhi_hu
from .xiaodu.xigua import xigua as xi_gua
from .xiaodu.haokan import haokan as hao_kan
from .xiaodu.bilibili import bilibili as bzhan
from .xiaodu.weibo import weibo as sina_weibo
from .xiaodu.sina_news import sina_news as xinlang_xinwen

class Baisou(ContentCrawler):
    def __init__(self, via='xiaodutv'):
        super().__init__();
        self.platform = '百搜视频'
        self.via = via
        self.url = 'https://v.xiaodutv.com'
        self.headers.update({'Referer': 'https://v.xiaodutv.com/'})
        self.sources = dict()
        self.using_browser = True
        self.browser = 'Chrome'
        self.url_platform = [
            {
                'platform': '百家号',
                'url': 'mbd.baidu.com',
                'method': self.baijiahao,
            },
            {
                'platform': '知乎',
                'url': 'zhihu.com',
                'method': self.zhihu,
            },
            {
                'platform': '西瓜视频',
                'url': 'ixigua.com',
                'method': self.xigua,
            },
            {
                'platform': '好看视频',
                'url': 'haokan.baidu.com',
                'method': self.haokan,
            },
            {
                'platform': 'Bilibili',
                'url': 'bilibili.com',
                'method': self.bilibili,
            },
            {
                'platform': '微博',
                'url': 'weibo.com',
                'method': self.weibo,
            },
            {
                'platform': '新浪新闻',
                'url': 'video.sina.cn',
                'method': self.sina_news,
            },
            {
                'platform': '百度文章',
                'url': 'baijiahao.baidu.com',
                'method': self.baidu_wenzhang,
            },
            {
                'platform': '百搜视频',
                'url': 'xiaodutv.com',
                'method': self.xiaodutv,
            },
        ]
    def __collect_source(self, source, url, writeToFile):
        logging.debug(f'add new: {source}')
        if source not in self.sources:
            self.sources.update({source: url})
        if writeToFile:
            file_sources = dict()
            try:
                file_sources = json.load(open('baisou_source.txt', 'r', encoding='utf-8'))
            except FileNotFoundError:
                pass
            self.sources.update(file_sources)
            json.dump(self.sources, open('baisou_source.txt', 'w+', encoding='utf-8'), ensure_ascii=False, indent=4)
    def get_content(self, url=None, xpath=None):
        logging.debug('get_content_baisou')
        if url is None:
            url = self.url
        if not self.using_browser:
            result = super().get_content(url, xpath)
            if xpath:
                result['content'] = etree.HTML(result['content']).xpath(xpath + '/text()')[0]
        else:
            result = self.get_content_selenium(url, xpath)
        self.using_browser = False
        if random.random() < 0.2:
            self.using_browser = True
        return result
    def async_get_redirect(self, url, index, number, queue, queue_jindu, lock):
        logging.debug('async_get_redirect')
        browser = ['Chrome', 'Edge']
        result = self.get_content_selenium(url, None, browser[index % 2])
        result.update({'index': index})
        queue.put(result)
        # 输出进度条 !!!!!!!!!
        with lock:
            display = queue_jindu.get()
            display.progress('正在爬取视频地址')
            queue_jindu.put(display)
    def async_change_dict(self, queue, queue_vd, queue_jindu, lock):
        logging.debug('async_change_dict')
        global len
        vd = []
        while True:
            if not queue_vd.empty():
                new_vd = queue_vd.get()
                if new_vd == 'end':
                    logging.debug(f'!!!!!!!!! get end !!!')
                    break
                vd = vd + new_vd[len(vd):]
            if not queue.empty():
                new_result = queue.get()
                try:
                    vd[new_result['index']].update({'redirect': new_result['redirect']})
                    logging.debug(f"!!!!!!!!! change videos by child !!! {new_result['index']}")
                    # 输出进度条 !!!!!!!!!
                    with lock:
                        display = queue_jindu.get()
                        display.progress('正在数据整理')
                        queue_jindu.put(display)
                except:
                    logging.error(f'!!!!!!!!! change videos error by child !!! {new_result}')
                    queue.put(new_result)
        queue_vd.put(vd)
    def url_to_platform(self, url: str) -> dict:
        for u_p in self.url_platform:
            if u_p['url'] in url:
                return u_p
        raise Exception('尚不支持搜索该平台视频')
    @ContentCrawler.mode_wrapper('search_list')
    @ContentCrawler.search_key_wrapper
    def search_list(self, keyword=None, number=10):
        # 平台太多, 防止失败, 乘 2 保险
        number *= 2
        global len
        accumulate = 0
        page_size = 10; page_number = 0
        videos = []
        # 进程池
        pool = Pool(8)
        queue = multiprocessing.Manager().Queue()
        queue_jindu = multiprocessing.Manager().Queue()   # 用于显示进度条
        lock = multiprocessing.Manager().Lock()           # 用于显示进度条
        queue_vd = None
        # if number > 3:         # 实际使用发现视频数超过 100 时该收集数据进程会起作用
        #     queue_vd = multiprocessing.Manager().Queue()
        #     pool.apply_async(self.async_change_dict, args=(queue, queue_vd, queue_jindu, lock))
        # 百度的网页太快了, 没法并行爬虫, 会被反爬
        smooth_time = 0.5
        product_factor = page_number * page_size / 60
        # 输出进度条 !!!!!!!!!
        self.display.progress('正在爬取视频列表', total=number / page_size + (number % page_size != 0), fixed=True)
        self.display.progress('正在爬取视频地址', total=number, fixed=True)
        queue_jindu.put(self.display)
        while accumulate < number:
            url = f'https://www.baidu.com/sf/vsearch?pd=video&tn=vsearch&ie=utf-8&wd={keyword}&async=1&pn={page_number * page_size}'
            if page_number == 0:
                url = f'https://www.baidu.com/sf/vsearch?pd=video&tn=vsearch&ie=utf-8&wd={keyword}'
            logging.info(f'Search URL: {url}')
            while True:
                logging.debug(f'!!!!!!!!!!!!!!!! smooth_time: {smooth_time}')
                result_dict = self.get_content(url)
                if '百度安全验证' not in result_dict['content'] and '网络不给力' not in result_dict['content']:
                    smooth_time = smooth_time * 0.8 if smooth_time * 0.8 > 0.3 else 0.3
                    break
                else:
                    smooth_time *= product_factor
                    logging.warning('!!!! 警告! 警告! 被百度反爬了! !!!!')
                    logging.warning(f'!!!! smooth_time = {smooth_time} !!!!')
                    self.using_browser = True
                    self.get_content(f'https://www.baidu.com/sf/vsearch?pd=video&tn=vsearch&ie=utf-8&wd={keyword}')
                    time.sleep(smooth_time)
            if '没有更多内容了' in result_dict['content']:
                break
            try:
                result = etree.HTML(result_dict['content'])
            except:
                logging.error(result_dict['url'])
            # 输出进度条 !!!!!!!!!
            with lock:
                self.display = queue_jindu.get()
                self.display.progress('正在爬取视频列表')
                queue_jindu.put(self.display)
            for offset, div in enumerate(result.xpath('//div[@class="video_list video_short"]')):
                wwwURL = div.xpath('.//div//a/@href')[0].strip(' \n')
                title = etree.tostring(div.xpath('.//div//a[1]')[0], pretty_print=True, encoding='unicode')
                title = re.sub('<[^>]*>|&nbsp;|\n', '', title).strip(' ')
                source_pair = div.xpath('./div//span[1]/text()')[0].split('：')
                source = source_pair[1] if source_pair[0] == '来源' else 'unknown' + str(random.randint(0,65535))
                self.__collect_source(source, wwwURL, False)
                # logging.debug(f'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!{title}, {source}, {wwwURL}')
                videos.append({
                    'index': accumulate,
                    'title': title,
                    'wwwURL': wwwURL,
                    'source': source
                })
                # if number > 3:
                #     queue_vd.put(videos)
                pool.apply_async(self.async_get_redirect, args=(wwwURL, accumulate, number, queue, queue_jindu, lock))
                accumulate += 1
                if accumulate == number:
                    break
            page_number += 1
            time.sleep(smooth_time)
        # 输出进度条 !!!!!!!!!
        self.display.progress('正在数据整理', total=number, fixed=True)
        with lock:
            self.display = queue_jindu.get()
            self.display.progress('正在爬取视频列表', ok=True)
            queue_jindu.put(self.display)
        self.__collect_source(source, wwwURL, True)
        pool.close()
        # if number > 3:
        #     queue_vd.put('end')
        #     logging.debug('!!!!!!!!! sent end !!!')
        #     videos = queue_vd.get()
        pool.join()
        self.display = queue_jindu.get()
        while not queue.empty():
            new_result = queue.get()
            # print(len(videos), new_result['index'])
            try:
                videos[new_result['index']].update({'redirect': new_result['redirect']})
                logging.debug(f"!!!!!!!!! change videos by parent !!! {new_result['index']}")
            except:
                logging.error(f'!!!!!!!!! change videos error by parent {new_result}', exc_info=True)
            # 输出进度条 !!!!!!!!!
            self.display.progress('正在数据整理', total=len(videos))
        # logging.debug(f'!!!!!!!!!!{videos}')
        # 输出进度条 !!!!!!!!!
        self.display.progress('正在数据整理', ok=True)
        # print(len(videos))
        result = []
        count = 0
        self.display.progress('正在下载视频', total=number / 2, fixed=True)
        for video in videos:
            time.sleep(2)
            try:
                handle = self.url_to_platform(video['redirect'])['method']
                video.update(handle(url=video['redirect']))
                video['status'] = 'success'
                video['index'] = count
                result.append(video)
                count += 1
                self.display.progress('正在下载视频')
            except Exception as e:
                logging.error(f'{e}\n该视频爬取失败')
                video['status'] = 'fail'
            if count == number / 2:
                break
        self.display.progress('正在下载视频', ok=True)
        return result
    @ContentCrawler.mode_wrapper('search_id')
    @ContentCrawler.search_key_wrapper
    def search_video_id(self, video_id):
        result = self.xiaodutv(url=None, title=None, videoID=video_id)
        result['index'] = None
        result['mode'] = self.mode
        result['search_key'] = self.search_key
        return result
    def xiaodutv(self, url: str = None, title: str = None, videoID: str = None) -> dict:
        """
        这里可以使用 url 或者 videoID (url 中的 ID) 进行查询
        该函数本意是使用 ID 进行查询, 因为 xiaodutv 没有搜索功能, 所以给 title 没用
        :param url: 视频播放 url
        :param title: 没用, 保持为 None
        :param videoID: url 中的 ID
        :return: 字典
        """
        yuanlai_platform = self.platform
        self.platform = '百搜视频'
        if url is not None and not isinstance(url, str):
            raise TypeError("url 必须是字符串或 None")
        if title is not None:
            raise TypeError("title 必须是 None")
        if videoID is not None and not isinstance(videoID, str):
            raise TypeError("videoID 必须是字符串或 None")
        if url is None and videoID is None:
            raise ValueError("url 和 videoID 不能同时为空")

        if url is None:
            url = 'https://baishi.xiaodutv.com/watch/' + videoID + '.html'

        def initial_playwright(this_object):
            this_object.playwright_need['doc'] = list()
            this_object.playwright_need['media'] = list()

        def click_play(browser, context, page):
            video_block = page.locator('//*[@id="playerSection"]')
            play_button = page.locator('//*[@class="play-icon"]')
            video_block.hover(timeout=500)
            try:
                play_button.click(timeout=5000)
            except:
                pass

        def get_duration(browser, context, page):
            time_count_elem = page.locator('//*[@class="time"]')
            time_count = time_count_elem.inner_html().split('/')
            t = []
            for time in time_count:
                h_m_s = time.split(':')
                s = int(h_m_s[-1])
                m = int(h_m_s[-2])
                try:
                    h = int(h_m_s[-3])
                except:
                    h = 0
                t.append(h * 3600 + m * 60 + s)
                # print(h_m_s)
            time_count = t
            self.platform = yuanlai_platform
            return {
                'duration': time_count[1]
            }

        def waiting_condition(this_object, browser, context, page):
            global len
            return len(this_object.playwright_need['doc']) < 2 or len(this_object.playwright_need['media']) < 1

        def integreted_handle(this_object, browser, context, page):
            media = sorted(
                this_object.playwright_need['media'],
                key=lambda x: x['length'] if x['length'] is not None else 0, reverse=True)
            doc = sorted(
                this_object.playwright_need['doc'],
                key=lambda x: x['length'] if x['length'] is not None else 0, reverse=True
            )

            this_object.headers = media[0]['headers']

            title_elem = page.locator('//h2[@title]')
            title = title_elem.inner_html()
            logging.info('title: ' + title)
            # 获取其他信息
            json_string = re.findall(r'"videos":\s*(\[.*\])\s*\}', doc[0]['content'].decode())[0]
            # print(json_string)
            json_data = json.loads(json_string)
            # pprint(json_data)
            desc = None
            video_ID = json_data[0]['play_link_sign64']
            author = re.findall(r"scope.uname\s*=\s*'(.*?)';", doc[1]['content'].decode())[0]
            # print(author)
            date_string = json_data[0]['date'].split('-')
            date = []
            # 时间记录的粒度 0: h, 1: m, 2, d, 3: h, 4: min, 5: s, 6: ms
            granularity = None

            def index_to_granularity(index: int) -> str:
                granularities = ['year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond']
                return granularities[index]

            for index, i in enumerate(date_string):
                date.append(int(i.strip()))
                granularity = index_to_granularity(index)
            beijing_time = datetime(year=date[0], month=date[1], day=date[2], tzinfo=ZoneInfo('Asia/Shanghai'))
            publish_date = {
                'timestamp': beijing_time.timestamp(),
                'granularity': granularity
            }
            video_url = url
            channel = None
            views = json_data[0]['play_num']
            likes = None
            platform = '百搜视频'
            via = '百搜视频'

            result = {
                'title': title,
                'desc': desc,
                # url 里面的 ID, 也是 guid
                'video_ID': video_ID,
                'author': author,
                # 一个字典
                'publish_date': publish_date,
                'video_url': video_url,
                'download_url': media[0]['url'],
                'channel': channel,
                'views': views,
                'like': likes,
                'platform': platform,
                'via': via,
                'index': None,
            }
            return result

        register_function = {
            'initial_playwright': initial_playwright,
            'click_play': click_play,
            'get_duration': get_duration,
            'waiting_condition': waiting_condition,
            'integreted_handle': integreted_handle,
            'request_for_video': None,
            'path_from_root': r'data\xiaodutv\search_id',
            'write_to_file': None,
        }

        return self.get_media_requests_and_playwright(url, register_function)
    def baidu_wenzhang(self, url):
        # 百度文章
        yuanlai_platform = self.platform
        self.platform = '百度文章'
        try:
            result = self.get_content_selenium(url, None, 'Edge')
            html = etree.HTML(result['content'])
            scripts = html.xpath('//script/text()')
            script = None
            for scr in scripts:
                if scr.find('window.jsonData') == 0:
                    script = scr
            json_str = re.findall(r'window.jsonData\s*=\s*(\{.*\})\s*;', script)[0]
            json_data = json.loads(json_str)
        except:
            try:
                result = self.get_content_selenium(url, None, 'Chrome')
                html = etree.HTML(result['content'])
                scripts = html.xpath('//script/text()')
                script = None
                for scr in scripts:
                    if scr.find('window.jsonData') == 0:
                        script = scr
                json_str = re.findall(r'window.jsonData\s*=\s*(\{.*\})\s*;', script)[0]
                json_data = json.loads(json_str)
            except:
                driver = sync_playwright().start()
                try:
                    if self.config['browser_core'] == 'chromium':
                        browser = driver.chromium.launch(
                            headless=True,
                            executable_path=self.config['browser_dir']
                        )
                    elif self.config['browser_core'] == 'firefox':
                        browser = driver.firefox.launch(
                            headless=True,
                            executable_path=self.config['browser_dir']
                        )
                    elif self.config['browser_core'] == 'webkit':
                        browser = driver.webkit.launch(
                            headless=True,
                            executable_path=self.config['browser_dir']
                        )
                    else:
                        raise ValueError('请使用 playwright 支持的浏览器内核')
                    page = browser.new_page()
                    page.goto(url)
                    html = page.content()
                    browser.close()
                finally:
                    driver.stop()
                html = etree.HTML(html)
                scripts = html.xpath('//script/text()')
                script = None
                for scr in scripts:
                    if scr.find('window.jsonData') == 0:
                        script = scr
                json_str = re.findall(r'window.jsonData\s*=\s*(\{.*\})\s*;', script)[0]
                json_data = json.loads(json_str)
        # pprint(json_data)
        title = json_data['bsData']['title']
        desc = None
        author = json_data['bsData']['superlanding'][1]['itemData']['name']
        page_url = json_data['bsData']['profitLog']['contentUrl']
        items = page_url.split('?')[1].split('%')
        video_ID = None
        for item in items:
            pair = item.split('=')
            if pair[0] == 'id':
                video_ID = pair[1]
        publish_date = {
            'timestamp': int(json_data['bsData']['timestamp']) / 1000,
            'granularity': 'microsecond',
        }
        channel = None
        keywords = None
        duration_time = json_data['bsData']['superlanding'][0]['itemData']['sections'][0]['content']['base'][
            'long'].split(':')
        duration = int(duration_time[0]) * 60 + int(duration_time[1])
        views = None
        like = int(re.sub(r',|\.| ', '', json_data['bsData']['like']['count']))

        path_dict = self.filename(title, self.mode, 'mp4', 2, self.via, self.platform)

        video_url = html.xpath('//video/@src')[0]
        result = self.get_content_requests(video_url, False)['content']
        with open(path_dict['output_path'], 'wb+') as f:
            f.write(result)

        result = {
            'platform': self.platform,
            'via': self.via,
            'index': None,
            'mode': self.mode,
            'search_key': self.search_key,
            'title': title,
            'desc': desc,
            'video_ID': video_ID,
            'author': author,
            'publish_date': publish_date,
            'video_url': page_url,
            'download_url': video_url,
            'channel': channel,
            'keywords': keywords,
            'duration': duration,
            'views': views,
            'like': like,
            'path': path_dict['data_dir'],
            'file_path': path_dict['output_path'],
        }
        self.platform = yuanlai_platform
        return result
    def xigua(self, url: str) -> dict:
        yuanlai_platform = self.platform
        self.platform = '西瓜视频'
        register_function = xi_gua(url)
        result = self.get_media_requests_and_playwright(url, register_function)
        self.platform = yuanlai_platform
        return result
    def baijiahao(self, url: str) -> dict:
        yuanlai_platform = self.platform
        self.platform = '百家号'
        result = bai_jia_hao(self, url=url)
        self.platform = yuanlai_platform
        return result
    def zhihu(self, url: str) -> dict:
        yuanlai_platform = self.platform
        self.platform = '知乎'
        result = zhi_hu(self, url=url)
        self.platform = yuanlai_platform
        return result
    def haokan(self, url: str) -> dict:
        yuanlai_platform = self.platform
        self.platform = '好看视频'
        result = hao_kan(self, url)
        self.platform = yuanlai_platform
        return result
    def bilibili(self, url: str) -> dict:
        yuanlai_platform = self.platform
        self.platform = 'bilibili'
        result = bzhan(self, url)
        self.platform = yuanlai_platform
        return result
    def weibo(self, url: str) -> dict:
        yuanlai_platform = self.platform
        self.platform = '微博'
        result = sina_weibo(self, url)
        self.platform = yuanlai_platform
        return result
    def sina_news(self, url: str) -> dict:
        yuanlai_platform = self.platform
        self.platform = '新浪新闻'
        result = xinlang_xinwen(self, url)
        self.platform = yuanlai_platform
        return result


def res_to_video_info(res):
    video_info = VIDEO_INFO_ALL()
    video_info.refresh_info(mode = "all")

    video_info.platform = res['platform']
    video_info.base_url = "htts://v.cctv.cn/"

    video_info.title = res['title'] if 'title' in res else None
    video_info.id = res['video_ID'] if 'video_ID' in res else None
    video_info.video_url = res['video_url'] if 'video_url' in res else None
    video_info.download_url = res['download_url'] if 'download_url' in res else None
    video_info.author = res['author'] if 'author' in res else None
    video_info.publish_date = res['publish_date'] if 'publish_date' in res else None
    video_info.desc = res['desc'] if 'desc' in res else None
    video_info.channel = res['channel'] if 'channel' in res else None
    video_info.keywords = res['keywords'] if 'keywords' in res else None
    video_info.duration = res['duration'] if 'duration' in res else None
    video_info.likes = res['like'] if 'like' in res else None
    video_info.views = res['views'] if 'views' in res else None
    
    video_info.coins = res['coins'] if 'coins' in res else None
    video_info.favs = res['favs'] if 'favs' in res else None
    video_info.shares = res['shares'] if 'shares' in res else None
    
    return video_info.dict_info_all()


def BaisouCrawler(mode: str, target:str, number: int = 10):
    """
    百搜视频爬虫

    :param mode: 模式, 'search' 或 'video'
    :param target: 搜索关键词或视频ID
    :param number: 搜索模式下的结果数量, 默认为10
    """
    baisou = Baisou()

    mode = mode.lower()
    if mode not in ["search", "video"]:
        raise ValueError(f"无效模式: {mode}，支持模式: 'search'/'video'")
        
    target = target.strip() if isinstance(target, str) else target
    if not target:
        raise ValueError(f"无效target: {target}")
    
    result = []


    try:
        if mode == "search":
            result = baisou.search_list(target, number)
        elif mode == "video":
            if isinstance(target, (list, tuple)):  # 检测是否为列表或元组
                for video_id in target:
                    result.append(baisou.search_video_id(video_id.strip()))
            else:
                result.append(baisou.search_video_id(target))
    except Exception as e:
        logging.error(f"{mode}模式爬取失败: {str(e)}")
        raise

    parsed_result = baisou.output(result)

    for item in parsed_result:
        if mode == "search":
            output_path = "data/xiaodutv/search_list/video_{}_info.json".format(item['video_ID'])
        elif mode == "video":
            output_path = "data/xiaodutv/search_id/video_{}_info.json".format(item['video_ID'])

        video_info = res_to_video_info(item)
        save_to_json(video_info, output_path)





if __name__ == '__main__':
    pass
    # baisou = Baisou()
    # baisou.baidu_wenzhang('https://baijiahao.baidu.com/s?id=1827726025703567377&rcptid=11443693627548456500')

    baisou = Baisou()
    baisou.search_list('叶童', 10)
