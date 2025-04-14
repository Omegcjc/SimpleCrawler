import requests
import json
import re
from playwright.sync_api import sync_playwright
from pprint import pprint
import re

def weibo(self, url):
    purify = lambda x: x.split('?')[0].strip('/ ')
    url = purify(url)

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

        headers_pipe = []

        def response(response):
            nonlocal url, purify, headers_pipe
            res_headers = response.all_headers()
            req_headers = response.request.headers
            res_url = response.url
            try:
                if 'mp4' in res_headers['content-type']:
                    headers_pipe.append(res_url)
            except:
                pass

        context = browser.new_context()
        context.on('response', response)

        page = context.new_page()
        page.set_viewport_size({"width": 1800, "height": 1000})

        # input('输入点什么')

        try:
            page.goto(url, timeout=10000)
        except:
            pass

        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
            'referer': 'https://weibo.com/',
        }

        # url = 'https://f.video.weibocdn.com/o0/okKBafTrlx08nqabi0iA01041200eJjZ0E010.mp4?label=mp4_720p&template=960x720.25.0&media_id=5154721942405189&tp=8x8A3El:YTkl0eM8&us=0&ori=1&bf=4&ot=h&ps=3lckmu&uid=3ZoTIp&ab=,8012-g2,8013-g0,14490-g9,3601-g39&Expires=1744523819&ssig=o3prGq0AnP&KID=unistore,video'

        page.wait_for_timeout(10000)

        playwright_cookie = context.cookies()

        requests_cookie = {}
        for c in playwright_cookie:
            requests_cookie[c['name']] = c['value']

        video_ID = url.split('/')[-1]

        params = {
            'page': '/tv/show/' + video_ID
        }

        json_data = {
            'Component_Play_Playinfo': {
                'oid': video_ID
            }
        }

        json_string = json.dumps(json_data, ensure_ascii=False)

        data = {
            'data': json_string
        }

        response = requests.post('https://weibo.com/tv/api/component', params=params, data=data, headers=headers,
                                 cookies=requests_cookie)

        json_str = response.content.decode('gbk')
        json_dt = json.loads(json_str)

        json_dt = json_dt['data']['Component_Play_Playinfo']

        title = json_dt['title']
        author = json_dt['author']
        desc = json_dt['text']
        desc = re.sub(r'(<[^>\n]*?>)', '', desc)
        views = int(re.sub(r',|\.| ', '', json_dt['play_count']))
        likes = json_dt['attitudes_count']
        duration = json_dt['duration_time']
        publish_date = {
            'timestamp': json_dt['real_date'],
            'granularity': 'second',
        }
        keywords = [item['content'] for item in json_dt['topics']]
        channel = None
        index = None

        video_url = headers_pipe[-1]

        response = requests.get(video_url, headers=headers)

        path_dict = self.filename(title, self.mode, 'mp4', 2, self.via, self.platform)
        with open(path_dict['output_path'], 'wb+') as f:
            f.write(response.content)

        page.close()
        context.close()
        browser.close()
    finally:
        driver.stop()

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
        'download_url': video_url,
        'channel': channel,
        'keywords': keywords,
        'duration': duration,
        'views': views,
        'like': likes,
        'path': path_dict['data_dir'],
        'file_path': path_dict['output_path'],
    }

if __name__ == '__main__':
    weibo(None, 'https://weibo.com/tv/show/1034:5154721942405189')






































