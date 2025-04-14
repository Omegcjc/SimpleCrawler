import requests
import re
from lxml import etree
import json
from pprint import pprint
import os

def baijiahao(self, url):
    # 百家号
    try:
        url = url.replace('https', 'http')
    except:
        pass
    response = self.get_content_requests(url)['content']
    # print(response)
    html = etree.HTML(response)
    script = html.xpath('//script/text()')[0]
    json_data = re.findall(r'[^\{]*(\{.*\})[^\}]*', script)[0]
    # print(json_data)
    data = json.loads(json_data)
    # pprint(data)
    title = data['curVideoMeta']['title']
    desc = data['header']['description']
    video_ID = data['curVideoMeta']['id']
    author = data['author']['name']
    publish_date = {
        'timestamp': data['curVideoMeta']['publish_time'],
        'granularity': 'second',
    }
    video_url = url
    channel = None
    keywords = data['header']['keywords'].split(',')
    duration = data['curVideoMeta']['duration']
    views = data['playCount']
    like = data['like']['count']


    play_list = []

    def key_to_level(key):
        if key == 'sd':
            return 0
        elif key == 'hd':
            return 1
        elif key == 'sc':
            return 2
        elif key == '1080p':
            return 3
        else:
            return 4

    for play_url in data['curVideoMeta']['clarityUrl']:
        play_list.append({'key': play_url['key'], 'url': play_url['url'], 'level': key_to_level(play_url['key'])})
    max_res = 0
    max_res_url = None
    res_key = None
    for play_url in play_list:
        res = play_url['level']
        if res > max_res:
            max_res = res
            max_res_url = play_url['url']
            res_key = play_url['key']
    response = requests.get(max_res_url)

    download_url = max_res_url

    path_dict = self.filename(title, self.mode, 'mp4', 2, self.via, '百家号')
    with open(path_dict['output_path'], 'wb+') as f:
        f.write(response.content)

    return {
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
        'video_url': video_url,
        'download_url': download_url,
        'channel': channel,
        'keywords': keywords,
        'duration': duration,
        'views': views,
        'like': like,
        'path': path_dict['data_dir'],
        'file_path': path_dict['output_path'],
    }