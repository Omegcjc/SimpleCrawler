import requests
import re
from lxml import etree
import json
import os
from pprint import pprint

def bilibili(self, url):

    purify_url = lambda x: x.split('?')[0].strip('/ ')
    url = purify_url(url) + '/'

    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0'
    }

    response = requests.get(url, headers=headers)

    html = response.content.decode()

    dom = etree.HTML(html)
    script = dom.xpath('//script/text()')
    playinfo = None
    videoinfo = None
    for scr in script:
        if scr.find('window.__playinfo__') == 0:
            playinfo = scr
        elif scr.find('window.__INITIAL_STATE__') == 0:
            videoinfo = scr

    play_json_str = re.findall(r'__playinfo__\s*=\s*(\{.*\})', playinfo)[0]
    play_json_data = json.loads(play_json_str)
    video_json_str = re.findall(r'__INITIAL_STATE__\s*=\s*(\{.*\})\s*;', videoinfo)[0]
    video_json_data = json.loads(video_json_str)

    title = video_json_data['videoData']['title']
    index = None
    desc = video_json_data['videoData']['desc']
    video_ID = video_json_data['videoData']['bvid']
    author = video_json_data['videoData']['owner']['name']
    publish_date = {
        'timestamp': video_json_data['videoData']['pubdate'],
        'granularity': 'second',
    }
    channel = [
        video_json_data['videoData']['tname'],
        video_json_data['videoData']['tname_v2'],
    ]
    keywords = []
    for tag in video_json_data['tags']:
        keywords.append(tag['tag_name'])
    duration = video_json_data['videoData']['duration']
    views = video_json_data['videoData']['stat']['view']
    like = video_json_data['videoData']['stat']['like']
    coins = video_json_data['videoData']['stat']['coin']
    favs = video_json_data['videoData']['stat']['favorite']
    shares = video_json_data['videoData']['stat']['share']

    video_dn_urls = []
    audio_dn_urls = []
    for reso in play_json_data['data']['dash']['video']:
        li = []
        if reso['baseUrl'] not in li:
            li.append(reso['baseUrl'])
        if reso['base_url'] not in li:
            li.append(reso['base_url'])
        for u in reso['backupUrl']:
            if u not in li:
                li.append(u)
        for u in reso['backup_url']:
            if u not in li:
                li.append(u)
        video_dn_urls.append(li)
    for reso in play_json_data['data']['dash']['audio']:
        li = []
        if reso['baseUrl'] not in li:
            li.append(reso['baseUrl'])
        if reso['base_url'] not in li:
            li.append(reso['base_url'])
        for u in reso['backupUrl']:
            if u not in li:
                li.append(u)
        for u in reso['backup_url']:
            if u not in li:
                li.append(u)
        audio_dn_urls.append(li)

    # pprint(video_dn_urls)
    # pprint(audio_dn_urls)

    video_ok = False
    audio_ok = False

    download_url = []

    headers = {
        "origin": "https://www.bilibili.com",
        "referer": url,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
    }

    self.display.info('正在下载视频画面', fixed=False)
    for reso in video_dn_urls:
        for u in reso:
            if video_ok:
                break
            try:
                response_video = requests.get(u, headers=headers)
                # print(response_video.status_code)
                if response_video.status_code >= 300:
                    raise Exception('下载出错')
                else:
                    video_ok = True
                    download_url.append(u)
                    break
            except:
                pass
        if video_ok:
            break

    self.display.info('正在下载音频', fixed=False)

    for reso in audio_dn_urls:
        for u in reso:
            if audio_ok:
                break
            try:
                response_audio = requests.get(u, headers=headers)
                # print(response_audio.status_code)
                if response_audio.status_code >= 300:
                    raise Exception('下载出错')
                else:
                    audio_ok = True
                    download_url.append(u)
                    break
            except:
                pass
        if audio_ok:
            break

    # print(video_ok, audio_ok)

    self.display.info('正在写入文件和格式转换', fixed=False)

    path_dict_video = self.filename(title + '_video', self.mode, 'm4s', 2, self.via, self.platform)
    path_dict_audio = self.filename(title + '_audio', self.mode, 'm4s', 2, self.via, self.platform)
    path_dict_mp4 = self.filename(title, self.mode, 'mp4', 2, self.via, self.platform)
    # with open(path_dict['output_path'], 'wb+') as f:
    #     f.write(response.content)

    with open(path_dict_video['output_path'], 'wb+') as f:
        f.write(response_video.content)
    with open(path_dict_audio['output_path'], 'wb+') as f:
        f.write(response_audio.content)

    # 防止 ffmpeg 询问覆写的问题
    if os.path.exists(path_dict_mp4['output_path']):
        os.remove(path_dict_mp4['output_path'])
    self.convert_ts_to_mp4(
        ts_file=[
            path_dict_video['output_path'],
            path_dict_audio['output_path'],
        ],
        out_file=path_dict_mp4['output_path']
    )

    # 删除 m4s 文件
    if os.path.exists(path_dict_video['output_path']):
        os.remove(path_dict_video['output_path'])
    if os.path.exists(path_dict_audio['output_path']):
        os.remove(path_dict_audio['output_path'])

    result = {
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
        'coins': coins,
        'favs': favs,
        'shares': shares,
        'path': path_dict_mp4['data_dir'],
        'file_path': path_dict_mp4['output_path'],
    }

    return result



















































