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
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
from functools import wraps

from tools.screen_display import ScreenDisplay

class ContentCrawler(object):
    def __init__(self):
        self.platform = None
        self.via = None
        self.url = ''
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        }
        self.cookies = dict()
        self.display = ScreenDisplay()
        self.config = {
            'browser_core': 'chromium',
            'browser_dir': r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        }
        self.playwright_need = {
            'response_handle': None,
        }
        self.mode = None
        self.search_key = None
    @staticmethod
    def pure_domain(url, slash=False):
        url = url.strip(' \n')
        domain = url.split(sep='/')
        # print(domain)
        slash_string = '/' if slash else ''
        if '://' in url:
            result = domain[0] + '//' + domain[2] + slash_string
        else:
            result = 'https://' + domain[0] + slash_string
        return result
    @staticmethod
    def pure_url(url, question_mark=False):
        url = url.strip(' \n')
        ques_mark = r'\?' if question_mark else ''
        try:
            result = re.match(r'(http|https)://[^\?]+' + ques_mark, url).group()
        except:
            result = re.match(r'(http|https)://[^\?]+', url).group()
        return result
    @staticmethod
    def convert_ts_to_mp4(ts_file=None, out_file=None):
        """
        可以进行视频转换
        也可以视频音频合并 (输入文件列表)
        :param ts_file:
        :return:
        """
        command_series = []
        if isinstance(ts_file, list):
            for file in ts_file:
                if not os.path.exists(file):
                    print(f"输入文件 {file} 不存在")
                    return
                command_series.append('-i')
                command_series.append(file)
        else:
            if not os.path.exists(ts_file):
                print(f"输入文件 {ts_file} 不存在")
                return
            command_series.append('-i')
            command_series.append(ts_file)
        # 构建FFmpeg命令
        if out_file is None:
            out_file = ts_file.rsplit('.', 1)[0] + '.mp4'
        command = ['ffmpeg'] + command_series + [
            '-c:v', 'copy',  # 视频编码器设置为复制
            '-c:a', 'copy',  # 音频编码器设置为复制
            '-movflags', '+faststart',  # 优化MP4文件以便于网络播放
            out_file  # 输出文件
        ]
        try:
            # 执行FFmpeg命令
            subprocess.run(command, check=True)
            logging.info(f"成功将 {ts_file} 转换为 {out_file}")
        except subprocess.CalledProcessError as e:
            logging.error(f"转换失败: {e}")
    @staticmethod
    def output(video_list: list, output_path: str = None, mode='json') -> list:
        """
        可以输出一个从原始的信息字典到可以直接输出的字符串字典
        使用 csv mode 时需要输入一个 output_path, 且会转换英文逗号为中文逗号
        :param video_list:
        :param output_path:
        :param mode:
        :return:
        """

        def seconds_to_h_m_s(seconds) -> dict:
            result = dict()
            int_seconds = int(seconds)
            result['hour'] = int_seconds // 3600
            if result['hour'] == 0:
                result['hour'] = None
            result['minute'] = (int_seconds // 60) % 60
            result['second'] = int_seconds % 60
            if type(seconds) == type(int()):
                result['microsecond'] = None
                result['granularity'] = 'second'
            else:
                result['microsecond'] = round((seconds % 1) * 1000000)
                result['granularity'] = 'microsecond'
            return result

        def timestamp_to_y_m_d(date: dict) -> dict:
            beijing_time = datetime.fromtimestamp(date['timestamp'], tz=ZoneInfo('Asia/Shanghai'))
            result = {
                'year': beijing_time.year,
                'month': beijing_time.month,
                'day': beijing_time.day,
                'hour': beijing_time.hour,
                'minute': beijing_time.minute,
                'second': beijing_time.second,
                'microsecond': beijing_time.microsecond,
                'granularity': date['granularity'],
            }
            return result

        def dict_to_timestring(time_dict: dict, mode: str = 'duration') -> str:
            '''
            将年月日时分秒微秒字典 (包含粒度字段) 转换为时间字符串
            :param time_dict: 时间字典
            :param mode: 'duration' 表示时长 (从小时开始输出), 'date' 表示日期 (从年开始输出)
            :return: 输出字符串
            '''
            granularities = ['year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond']
            result = ''
            if mode == 'duration':
                start = 3
            else:
                start = 0
            for i in range(start, 7):
                if time_dict[granularities[i]] is not None:
                    if granularities[i] in ['month', 'day', 'hour', 'minute', 'second']:
                        result += '%02d' % time_dict[granularities[i]]
                    elif granularities[i] == 'microsecond':
                        result += '%06d' % time_dict[granularities[i]]
                    else:
                        result += str(time_dict[granularities[i]])
                if granularities[i] == time_dict['granularity']:
                    if granularities[i] == 'hour':
                        result += '时'
                    break
                if granularities[i] in ['year', 'month']:
                    result += '-'
                elif granularities[i] == 'day':
                    result += ' '
                elif granularities[i] in ['hour', 'minute'] and time_dict[granularities[i]] is not None:
                    result += ':'
                elif granularities[i] == 'second':
                    result += '.'
            return result

        def keywords_to_string(keywords: list) -> str:
            """
            把列表转换为逗号分隔的字符串
            """
            result = ''
            for keyword in keywords:
                result += keyword
                result += ','
            result = result.rstrip(',')
            return result

        result = []
        keys = [
            'platform',
            'via',
            'index',
            'mode',
            'search_key',
            'title',
            'desc',
            'video_ID',
            'author',
            'publish_date',
            'video_url',
            'download_url',
            'channel',
            'keywords',
            'duration',
            'views',
            'like',
            'coins',
            'favs',
            'shares',
            'path',
            'file_path',
        ]
        for index, v in enumerate(video_list):
            v_dict = dict()
            for key in keys:
                if key == 'index':
                    v_dict[key] = str(index)
                else:
                    try:
                        if v[key] is None:
                            v_dict[key] = ''
                        else:
                            if key == 'publish_date':
                                v_dict[key] = dict_to_timestring(timestamp_to_y_m_d(v[key]), 'date')
                            elif key == 'duration':
                                v_dict[key] = dict_to_timestring(seconds_to_h_m_s(v[key]), 'duration')
                            elif isinstance(v[key], list):
                                v_dict[key] = keywords_to_string(v[key])
                            else:
                                v_dict[key] = str(v[key])
                    except KeyError as e:
                        v_dict[key] = ''
            result.append(v_dict)

        def output_csv(v_list: list, output_path: str = output_path) -> None:
            nonlocal keys
            with open(output_path, 'w+', encoding='utf-8') as f:
                for key in keys:
                    f.write(key)
                    f.write(',')
                f.write('\n')
                for v in v_list:
                    for key in keys:
                        try:
                            str = re.sub(r',', '，', v[key])
                            str = re.sub(r'\n', '', str)
                            f.write(re.sub(r',', '，', str))
                        except:
                            f.write('该项数据错误')
                        f.write(',')
                    f.write('\n')

        if mode == 'csv':
            output_csv(v_list=result, output_path=output_path)
        return result
    @staticmethod
    def filename(title: str, mode: str = None, suffix: str  = None, direct = 2, via: str  = None, platform: str  = None) -> dict:
        r"""
        输出 file_name + data_dir = output_path
        :param title: 文件标题的主干
        :param mode: 'search_list' or 'search_id', None 则写到 via 目录下
        :param suffix: 后缀名
        :param direct: 是否直接存在 data 目录下或平台目录下, 0 存在 data 目录, 1 存在 data\via 目录, 2 存在 data\via\mode 目录
        :param via: 经过的平台
        :param platform: 最终的平台
        :return: 字典
        """
        # !!!!!!!!!!!!!!!!!!!!!!!!! 文件输入输出 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # 获取当前工作目录
        current_dir = os.getcwd()
        # 构建输出文件的路径
        data_dir = os.path.join(current_dir, r"data")

        via_dir = None
        if via in ['cctv', 'CCTV', '央视网', '央视']:
            via_dir = 'cctv'
        elif via in ['baisou', 'baisoutv', 'xiaodu', 'xiaodutv', '百搜', '百搜视频', '小度', '小度视频', '小度TV']:
            via_dir = 'xiaodutv'

        path_list = [via_dir, mode]

        while direct > 0:
            if path_list[2 - direct] is not None:
                data_dir = os.path.join(data_dir, path_list[2 - direct])
                direct -= 1
            else:
                break

        os.makedirs(data_dir, exist_ok=True)  # 确保 data 目录存在

        # 文件名
        none_to_emptystring = lambda x: '' if x is None else x
        via_dir = none_to_emptystring(via_dir)
        platform_name = none_to_emptystring(platform)
        file_name = via_dir + '_' + platform_name + '_' + re.sub(r'\\|/|:|\*|\?|"|<|>|\||\[|\]| ', '_', title)[0:100]  + '.' + suffix

        # 输出路径
        output_path = os.path.join(data_dir, file_name)

        return {
            'file_name': file_name,
            'data_dir': data_dir,
            'output_path': output_path,
        }
    @classmethod
    def mode_wrapper(cls, mode):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                set = False
                if args[0].mode is None:
                    args[0].mode = mode
                    set = True
                result = func(*args, **kwargs)
                if set:
                    args[0].mode = None
                return result
            return wrapper
        return decorator
    @classmethod
    def search_key_wrapper(cls, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            set = False
            if args[0].search_key is None:
                args[0].search_key = args[1]
                set = True
            result = func(*args, **kwargs)
            if set:
                args[0].search_key = None
            return result
        return wrapper
    def get_content(self, url=None, xpath=None, decode=True):
        logging.debug('get_content')
        if url is None:
            url = self.url
        try:
            result = self.get_content_requests(url, decode)
        except:
            result = self.get_content_selenium(url, xpath=xpath)
        if xpath:
            result['content'] = etree.HTML(result['content']).xpath(xpath + '/text()')[0]
        return result
    def get_document(self, url=None, decode=True):
        try:
            return self.get_content_requests(url=url, decode=decode)
        except:
            return self.get_content_playwright(url=url, decode=decode)
    def get_content_requests(self, url=None, decode=True):
        logging.debug('get_content_requests')
        if url is None:
            url = self.url
        response = requests.get(url, headers=self.headers, cookies=self.cookies)
        if response.status_code >= 300:
            raise Exception(str(response.status_code))
        # 设置新的 Referer
        self.headers['Referer'] = self.pure_url(url, question_mark=True)
        # 获取文档内容
        if decode:
            result = response.content.decode()
        else:
            result = response.content
        # 获取响应头中的 Set-Cookie 数据
        set_cookie = response.headers.get("Set-Cookie")
        try:
            set_cookie = set_cookie.split(';')
            not_include = [
                'path', 'Path', 'expires', 'Expires', 'max-age', 'Max-Age', 'domain', 'Domain',
                'secure', 'Secure', 'samesite', 'SameSite'
            ]
            for semicolon_item in set_cookie:
                # logging.debug(semicolon_item)
                comma_item = semicolon_item.strip(' ').split(',')
                for item in comma_item:
                    string = item.strip(' ')
                    pair = string.split('=', 1)
                    meaningful = pair[0] not in not_include
                    not_date = re.match(
                        '[0-9][0-9]?-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
                        pair[0]
                    ) is None
                    if meaningful and not_date and len(pair) == 2:
                        self.cookies.update({pair[0]: pair[1]})
        except AttributeError:
            pass
        return {'content': result, 'engine': 'requests', 'url': url}
    def get_content_playwright(self, url=None, decode=True):
        need = []
        global len
        def response(response):
            nonlocal url
            if response.url == url:
                result = {
                    'url': response.url,
                    'status_code': response.status,
                    'body': response.body(),
                    'headers': response.all_headers(),
                }
                # pprint(result)
                need.append(result)
        driver = sync_playwright().start()

        if self.config['browser_core'] == 'chromium':
            browser = driver.chromium.launch(
                headless=False,
                executable_path=self.config['browser_dir']
            )
        elif self.config['browser_core'] == 'firefox':
            browser = driver.firefox.launch(
                headless=False,
                executable_path=self.config['browser_dir']
            )
        elif self.config['browser_core'] == 'webkit':
            browser = driver.webkit.launch(
                headless=False,
                executable_path=self.config['browser_dir']
            )
        else:
            raise ValueError('请使用 playwright 支持的浏览器内核')

        content = browser.new_context()
        page = content.new_page()

        page.set_viewport_size({"width": 1800, "height": 1000})
        page.on('response', response)

        # page.wait_for_timeout(10000)

        response = None
        for i in range(5):
            page.goto(url)
            page.wait_for_selector('//html')
            for res in need:
                if res['status_code'] < 300:
                    response = res
                    break
            else:
                continue
            break
        else:
            raise Exception(str(need[-1]['status_code']))

        driver.stop()

        # 设置新的 Referer
        self.headers['Referer'] = self.pure_url(url, question_mark=True)
        # 获取文档内容
        if decode:
            result = response['body'].decode()
        else:
            result = response['body']
        # 获取响应头中的 Set-Cookie 数据
        set_cookie = response['headers']['set-cookie']
        try:
            set_cookie = set_cookie.split(';')
            not_include = [
                'path', 'Path', 'expires', 'Expires', 'max-age', 'Max-Age', 'domain', 'Domain',
                'secure', 'Secure', 'samesite', 'SameSite'
            ]
            for semicolon_item in set_cookie:
                # logging.debug(semicolon_item)
                comma_item = semicolon_item.strip(' ').split(',')
                for item in comma_item:
                    string = item.strip(' ')
                    pair = string.split('=', 1)
                    meaningful = pair[0] not in not_include
                    not_date = re.match(
                        '[0-9][0-9]?-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
                        pair[0]
                    ) is None
                    if meaningful and not_date and len(pair) == 2:
                        self.cookies.update({pair[0]: pair[1]})
        except AttributeError:
            pass
        return {'content': result, 'engine': 'requests', 'url': url}
    def get_content_selenium(self, url=None, xpath=None, browser='Chrome'):
        logging.debug('get_content_selenium')
        if url is None:
            url = self.url
        xpath = xpath if xpath else '//html'
        driver = webdriver.Chrome() if browser == 'Chrome' else webdriver.Edge()
        page = driver.get(url)
        wait = WebDriverWait(driver, 30, 0.2).until(  # driver, 最长等待时间, 多久测试一次
            EC.presence_of_element_located((By.XPATH, xpath))  # 里面是一个元组
        )
        cookies = driver.get_cookies()
        self.cookies = {cookie['name']: cookie['value'] for cookie in cookies}
        redirect_url = driver.current_url
        self.headers['Referer'] = self.pure_url(redirect_url, question_mark=True)
        content = driver.page_source
        driver.quit()
        return {'content': content, 'engine': 'selenium', 'url': url, 'redirect': redirect_url}
    def _playright_response(self, response) -> None:
        """
        这是一个通用的处理每一个响应.
        需要使用 self.playwright['doc']和['media'], 需先创建这两个管道
        1. 提取视频响应内容, 将请求头和 url 添加到 media
        2. 提取文档响应内容, 将文档内容添加到 doc
        建议使用 windows 的 edge, 而非 playwright 自带的 chromium
        :param response: 捕获的响应数据
        :return: 无
        """
        if self.playwright_need['response_handle'] is not None:
            self.playwright_need['response_handle'](self, response)
        else:
            doc = self.playwright_need['doc']
            media = self.playwright_need['media']
            global len
            headers = response.all_headers()
            try:
                type = headers['content-type'].split(';')[0].strip()
            except:
                type = None

            if type is not None and 'mp4' in type:
                logging.debug(str(response.url))
                logging.debug(str(response.ok))
                logging.debug(str(headers['content-type']))
                try:
                    length = len(response.body(timeout=1000))
                except:
                    length = 0
                media.append({
                    'url': response.url,
                    'headers': response.request.headers,
                    'length': length,
                })
            elif type is not None and 'html' in type:
                logging.debug(str(response.url))
                logging.debug(str(response.ok))
                logging.debug(str(headers['content-type']))
                content = response.body()
                length = len(content)
                doc.append({
                    'url': response.url,
                    'headers': response.request.headers,
                    'content': content,
                    'length': length,
                })
    def get_media_requests_and_playwright(self, url, register_function: dict) -> dict:
        """
        这是一个通用框架, 逻辑是 playwright 捕获 media 响应的请求头, 再用 requests 去请求 media
        因为很多视频是分片传输的, 由于缓存等莫名其妙问题, 直接用 playwright 获取响应体会无法获得响应体
        :param url: 视频页面的 url
        :param register_function: 字典,
                所有字段必须赋值!!!! 如果没有内容则赋值为 None!!!!
                包含如下的字段:
                initial_playwright: 两个任务 1. 在self.playwright_need字典中创建列表传递信息
                                            2. 在self.playwright_need的response_handle字段注册响应处理函数
                                               参数为 self
                click_play: 点击播放按钮, 参数为 browser, context, page
                get_duration: 从播放界面获取时长, 参数为 browser, context, page, 输出字典 {'duration': ...}
                waiting_condition: 停止等待条件, 参数为 self, browser, context, page, 输出真 (等待) 假 (停止等待)
                integreted_handle: 综合整理所有信息, 参数为 self, browser, context, page, 输出字典
                                    !!!! 注意修改 self.headers !!!!
                                   不需要 video_url
                request_for_video: 请求视频, 参数为 self, browser, context, page, 输出类型任意, 自行处理
                                返回字典!!!! 可以修改 'path' 和 "file_path", 不修改返回空字典即可
                path_from_root: 字符串! 根目录下的地址, 默认为 data, 一般需要在 data 下再建一个目录
                write_to_file: 将download_video的结果写到文件, 参数为 data_dir, output_path, dn_result
        :return:
        """
        global len

        # 创建用于传递响应内容的列表, 注册用于处理响应的函数
        # 函数注册在 self.playwright_need['response_handle']
        if register_function['initial_playwright'] is not None:
            register_function['initial_playwright'](self)
        else:
            self.playwright_need['doc'] = dict()
            self.playwright_need['media'] = dict()

        # 启动 node 和浏览器以及页面
        driver = sync_playwright().start()
        try:
            if self.config['browser_core'] == 'chromium':
                browser = driver.chromium.launch(
                    headless=False,
                    executable_path=self.config['browser_dir']
                )
            elif self.config['browser_core'] == 'firefox':
                browser = driver.firefox.launch(
                    headless=False,
                    executable_path=self.config['browser_dir']
                )
            elif self.config['browser_core'] == 'webkit':
                browser = driver.webkit.launch(
                    headless=False,
                    executable_path=self.config['browser_dir']
                )
            else:
                raise ValueError('请使用 playwright 支持的浏览器内核')
            context = browser.new_context()
            page = context.new_page()
            page.set_viewport_size({"width": 1800, "height": 1000})

            # 侦听响应事件
            # 如果在 initial_playwright 中没有指定响应处理函数的话, 自动捕获所有的 html 和 mp4
            context.on('response', self._playright_response)

            page.goto(url)

            page.wait_for_timeout(1000)

            # 点击播放按钮
            if register_function['click_play'] is not None:
                register_function['click_play'](browser, context, page)
            else:
                # 如果不传入点击播放的函数, 视为视频自动播放
                pass

            result = dict()

            # 获取时长
            result['duration'] = None
            if register_function['get_duration'] is not None:
                result.update(register_function['get_duration'](browser, context, page))
            else:
                # 如果不传入获取时长的函数, 视为这里不需要获取时长
                pass

            page.wait_for_timeout(2000)

            # 这里根据传递响应内容的列表的情况得出需要等待的条件
            # 也可以利用 browser, context, page
            while register_function['waiting_condition'](self, browser, context, page):
                pass

            # 从列表和各种地方获取信息
            # 注意这里需要在函数中修改 self.headers
            result['video_url'] = url
            if register_function['integreted_handle'] is not None:
                result.update(register_function['integreted_handle'](self, browser, context, page))
            else:
                # 这里没有注册函数视为下载视频不需要 headers
                self.headers = None

            # 使用 requests 下载视频
            if register_function['request_for_video'] is not None:
                dn_result = register_function['request_for_video'](self, browser, context, page)
            else:
                # 这里没有注册函数视为直接下载整个视频
                dn_url = result['download_url']
                del self.headers['range']
                dn_result = requests.get(dn_url, headers=self.headers)

            logging.debug((str(dn_result.url)))
            logging.debug(str(dn_result.status_code))

            browser.close()
        finally:
            driver.stop()

        self.playwright_need['response_handle'] = None

        # !!!!!!!!!!!!!!!!!!!!!!!!! 文件输入输出 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # 文件名
        try:
            file_name = re.sub(r'\\|/|:|\*|\?|"|<|>|\||\[|\]| ', '_', result['title'])[0:100] + '.mp4'
        except:
            file_name = re.sub(r'\\|/|:|\*|\?|"|<|>|\||\[|\]| ', '_', url)[-100:] + '.mp4'

        path_dict = self.filename(file_name, self.mode, 'mp4', 2, self.via, self.platform)
        # 获取当前工作目录
        current_dir = os.getcwd()
        # 构建输出文件的路径
        try:
            path_dict['data_dir'] = os.path.join(current_dir, register_function['path_from_root'])
            path_dict['output_path'] = os.path.join(path_dict['data_dir'], path_dict['file_name'])
            os.makedirs(path_dict['data_dir'], exist_ok=True)  # 确保 data 目录存在
        except:
            pass

        result.update({
            'path': path_dict['data_dir'],
            'file_path': path_dict['output_path'],
        })

        if register_function['write_to_file'] is not None:
            result.update(register_function['write_to_file'](path_dict['data_dir'], path_dict['output_path'], dn_result))
        else:
            # 没有注册视为直接下载到上述位置
            with open(path_dict['output_path'], 'wb+') as f:
                f.write(dn_result.content)

        return result
    def search_list(self, keyword, number):
        pass
    def search_video_id(self, video_id):
        pass



if __name__ == '__main__':
    pass





































































