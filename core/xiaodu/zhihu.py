import requests
import re
from lxml import etree
import json
import os

def zhihu(self, url):
    # 知乎
    self.headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0'
    }
    text = self.get_document(url)['content']
    html = etree.HTML(text)
    data = html.xpath('//*[@id="js-initialData"]/text()')[0]
    json_data = json.loads(data)

    video_ID = url.split('?', 1)[0].rsplit('/', 1)[1]
    title = json_data['initialState']['entities']['zvideos'][video_ID]['title']
    # 从 1970 年开始的时间戳
    try:
        publish_date = int(json_data['initialState']['entities']['zvideos'][video_ID]['publishedAt'])
        publish_date = {
            'timestamp': publish_date,
            'granularity': 'second',
        }
    except:
        publish_date = float(json_data['initialState']['entities']['zvideos'][video_ID]['publishedAt'])
        publish_date = {
            'timestamp': publish_date,
            'granularity': 'microsecond',
        }
    video_url = url
    for pair in json_data['initialState']['entities']['users'].items():
        if 'name' in pair[1]:
            author = pair[1]['name']
    keyword = []
    for dic in json_data['initialState']['entities']['zvideos'][video_ID]['topics']:
        keyword.append(dic['name'])
    channel = None
    # 秒数
    try:
        duration = int(json_data['initialState']['entities']['zvideos'][video_ID]['video']['duration'])
    except:
        duration = float(json_data['initialState']['entities']['zvideos'][video_ID]['video']['duration'])
    views = int(json_data['initialState']['entities']['zvideos'][video_ID]['playCount'])
    desc = None
    # 实际上是赞同数
    likes = int(json_data['initialState']['entities']['zvideos'][video_ID]['voteupCount'])

    play_list = []
    for pair in json_data['initialState']['entities']['zvideos'][video_ID]['video']['playlist'].items():
        play_list.append({
            'url': pair[1]['url'],
            'width': pair[1]['width'],
            'height': pair[1]['height'],
            'resolution': pair[0]
        })
    try:
        for pair in json_data['initialState']['entities']['zvideos'][video_ID]['video']['playlistV2'].items():
            play_list.append({
                'url': pair[1]['url'],
                'width': pair[1]['width'],
                'height': pair[1]['height'],
                'resolution': pair[0]
            })
    except:
        pass

    download_url = None

    play_list = sorted(play_list, key=lambda x: x['width'], reverse=True)
    for source in play_list:
        download_url = source['url']
        try:
            response = requests.get(source['url'], headers=self.headers)
            code = response.status_code
            if code >= 200 and code < 300:
                path_dict = self.filename(title, self.mode, 'mp4', 2, self.via, '知乎')
                with open(path_dict['output_path'], 'wb+') as f:
                    f.write(response.content)
                break
        except:
            pass

    result = {
        'title': title,
        'desc': desc,
        # url 里面的 ID
        'video_ID': video_ID,
        'author': author,
        # 距离 1970 年的秒数
        'publish_date': publish_date,
        'video_url': video_url,
        'download_url': download_url,
        'channel': channel,
        # 秒数
        'duration': duration,
        'views': views,
        'like': likes,
        # !!!!!!!!!!!!!!!!!!!! file !!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # 视频文件的地址
        'path': path_dict['data_dir'],
        'file_path': path_dict['output_path'],
        'platform': self.platform,
        'via': self.via,
        'index': None,
        'mode': self.mode,
        'search_key': self.search_key,
    }

    return result