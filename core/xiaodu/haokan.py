import requests
import re
from lxml import etree
import json
from pprint import pprint
import os
import time

from playwright.sync_api import sync_playwright

def haokan(self, url):

    # url = 'https://haokan.baidu.com/v?vid=7375883721630294995'

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

        page = [browser.new_page()]
        page[0].set_viewport_size({"width": 1800, "height": 1000})
        try:
            page[0].goto(url, timeout=10000)
        except:
            pass

        page[0].wait_for_timeout(3000)

        self.display.info('正在获取视频地址和信息', fixed=False)

        try:
            page[0].locator('//video[@class="art-video"]').hover(timeout=500)
        except:
            pass

        html = page[0].content()

        browser.close()
    finally:
        driver.stop()

    dom_tree = etree.HTML(html)
    download_url = dom_tree.xpath('//video[@class="art-video"]/@src')[0]
    title = dom_tree.xpath('//h1[@class="videoinfo-title"]/text()')[0]
    desc = dom_tree.xpath('//meta[@name="description"]/@content')[0]
    author = dom_tree.xpath('//div[@class="videoinfo-author-detail"]//a/text()')[0]
    keywords = dom_tree.xpath('//meta[@name="keywords"]/@content')[0].split(',')
    trash_keywords = ['资料', '咨询','电影', '电视剧','综艺','话题','帖子','mv','视频','在线','下载','观看','直播']
    for key in trash_keywords:
        if key in keywords:
            index = keywords.index(key)
            del keywords[index]
    duration_time = dom_tree.xpath('//*[@class="durationTime"]/text()')[0].split(':')
    duration = 60 * int(duration_time[0]) + int(duration_time[1])
    publish_date = int(re.sub(r',|\.| ', '', dom_tree.xpath('//*[@itemprop="datePublished"]/@content')[0]))
    publish_date = {
        'timestamp': publish_date,
        'granularity': 'second',
    }
    like = int(re.sub(r',|\.| ', '', dom_tree.xpath('//*[@class="extrainfo-zan like-0"]/text()')[0]))
    views = int(re.sub(r',|\.| ', '', re.findall(',([0-9]*)次', desc)[0]))
    index = None

    video_ID = re.findall('vid=([0-9]*)', url)[0]
    channel = keywords[0]

    self.display.info('正在下载视频', fixed=False)

    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
    }
    response = requests.get(download_url, headers=headers)

    path_dict = self.filename(title, self.mode, 'mp4', 2, self.via, self.platform)
    with open(path_dict['output_path'], 'wb+') as f:
        f.write(response.content)

    return {
        'platform': self.platform,
        'via': self.via,
        'index': index,
        'mode': self.mode,
        'search_key': self.search_key,
        'title': title,
        'desc': desc,
        'video_ID': video_ID,
        'author': author,
        'publish_date': publish_date,
        'video_url': url,
        'download_url': download_url,
        'channel': channel,
        'keywords': keywords,
        'duration': duration,
        'views': views,
        'like': like,
        'path': path_dict['data_dir'],
        'file_path': path_dict['output_path'],
    }











































