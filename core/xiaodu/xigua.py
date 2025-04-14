import logging
import re

def xigua(url):
    def response_handle(self, response):
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
            try:
                content = response.body(timeout=1000)
                length = len(content)
            except:
                content = None
                length = 0
            doc.append({
                'url': response.url,
                'headers': response.request.headers,
                'content': content,
                'length': length,
            })
    def initial_playwright(this_object):
        this_object.playwright_need['doc'] = list()
        this_object.playwright_need['media'] = list()
        this_object.playwright_need['response_handle'] = response_handle
    def click_play(browser, context, page):
        try:
            page.locator('//*[@id="App"]/div/main/div/div[3]/div[3]/div[1]/div[1]/div/h1').text_content()
        except:
            page.reload()
        video_block = page.locator('//*[@id="mp4-player"]')
        play_button = page.locator('//*[@id="mp4-player"]/xg-start')
        try:
            video_block.hover(timeout=500)
            play_button.click(timeout=5000)
        except:
            pass
        # print('click_play')
    def waiting_condition(this_object, browser, context, page):
        global len
        # print('waiting_condition', len(this_object.playwright_need['media']))
        return len(this_object.playwright_need['media']) < 2 # or len(this_object.playwright_need['doc']) < 2
    def integreted_handle(this_object, browser, context, page):

        title = page.locator('//*[@id="App"]/div/main/div/div[3]/div[3]/div[1]/div[1]/div/h1').text_content()
        page.locator('//*[@id="App"]/div/main/div/div[3]/div[3]/div[1]/div[2]/div/div[1]/div[1]/div/span').click()
        desc = page.locator('//*[@id="App"]/div/main/div/div[3]/div[3]/div[1]/div[2]/div/div[1]/div[2]/div').text_content()
        video_ID = url.split('?')[0].split('/')[3]
        author = page.locator('//*[@id="App"]/div/main/div/div[3]/div[2]/div/div[2]/a[1]/span[1]').text_content()
        timestamp = page.locator('//*[@id="App"]/div/main/div/div[3]/div[3]/div[1]/div[2]/div/div[1]/div[1]/p/span[3]').get_attribute('data-publish-time')
        publish_date = {
            'timestamp': int(timestamp),
            'granularity': 'second',
        }
        views = int(re.sub(r',|\.| ', '', page.locator('//*[@id="App"]/div/main/div/div[3]/div[3]/div[1]/div[2]/div/div[1]/div[1]/p/span[1]').inner_text().strip(' \n次观看')))
        likes = int(re.sub(r',|\.| ', '', page.locator('//*[@id="App"]/div/main/div/div[3]/div[3]/div[1]/div[2]/div/div[2]/div/button[1]/span/span').text_content()))
        time_duration = page.locator('//*[@id="mp4-player"]/xg-controls/xg-inner-controls/xg-left-grid/div[3]/div/span[3]').text_content()
        time_duration = time_duration.split(':')
        duration = int(time_duration[0]) * 60 + int(time_duration[1])

        # 修改 headers
        this_object.headers = this_object.playwright_need['media'][0]['headers']

        result = {
            'title': title,
            'desc': desc,
            # url 里面的 ID, 也是 guid
            'video_ID': video_ID,
            'author': author,
            # 距离 1970 年的秒数
            'publish_date': publish_date,
            'video_url': url,
            'download_url': this_object.playwright_need['media'][-1]['url'],
            'channel': '',
            'keywords': None,
            # 秒数
            'duration': duration,
            'views': views,
            'like': likes,
            'platform': this_object.platform,
            'via': this_object.via,
            'index': None,
            'mode': this_object.mode,
            'search_key': this_object.search_key,
        }
        return result

    register_function = {
        'initial_playwright': initial_playwright,
        'click_play': click_play,
        'get_duration': None,
        'waiting_condition': waiting_condition,
        'integreted_handle': integreted_handle,
        'request_for_video': None,
        'path_from_root': r'data\xiaodutv\search_list',
        'write_to_file': None,
    }

    return register_function




















































