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


def sina_news(self, url):
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'referer': 'https://weibo.com/',
    }
    response = requests.get(url, headers=headers)

    html = response.content.decode()

    json_str = re.findall(r'var\s*SM\s*=\s*(\{.*?\})\s*;', html)[0]
    json_data = json.loads(json_str)
    # pprint(json_data)

    title = json_data['doc']['title']
    desc = json_data['doc']['content']
    desc = re.sub(r'(<[^>\n]*?>)', '', desc)
    author = json_data['doc']['media']['name']
    video_ID = json_data['doc']['docid']
    duration = json_data['doc']['videoInfo']['timeLength']
    publish_date = json_data['doc']['ctime']
    date_obj = datetime.strptime(publish_date, '%Y-%m-%d %H:%M:%S')
    date_obj = date_obj.replace(tzinfo=ZoneInfo('Asia/Shanghai'))
    timestamp = date_obj.timestamp()
    publish_date = {
        'timestamp': timestamp,
        'granularity': 'second',
    }
    keywords = json_data['doc']['seoData']['keywords'].split(',')
    views = None
    likes = None
    channel = None
    index = None

    dn_url = json_data['doc']['videoInfo']['playUrl']

    response = requests.get(dn_url, headers=headers)
    download_url = response.url

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
        'video_url': download_url,
        'download_url': url,
        'channel': channel,
        'keywords': keywords,
        'duration': duration,
        'views': views,
        'like': likes,
        'path': path_dict['data_dir'],
        'file_path': path_dict['output_path'],
    }



if __name__ == '__main__':
    sina_news(None, url=r'https://video.sina.cn/finance/2025-04-11/detail-inesuhfw5044498.d.html')