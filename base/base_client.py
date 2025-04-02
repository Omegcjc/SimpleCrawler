import logging

from typing import Optional
from playwright.sync_api import sync_playwright, Page, BrowserContext

from base.base_config import BaseBrowerConfig

logger = logging.getLogger(__name__)


class BaseClient:
    '''基本的客户端实现基类'''
    def __init__(self, headless: bool = True):
        self.headless = headless

        self.p: Optional[sync_playwright] = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def start_browser(self, base_url: str = None, js_path = None, sessdata:str = None):
        try:
            self.p = sync_playwright().start() 
            self.browser = self.p.chromium.launch(
                channel="chrome",
                headless= self.headless,
                args = BaseBrowerConfig.get_chromium_args()
            )
            headers = BaseBrowerConfig.get_headers(base_url)
            self.context = self.browser.new_context(
                accept_downloads = True,
                user_agent=headers["User-Agent"],
                extra_http_headers=headers["extra_http_headers"]
            )

            # 反反爬对应的JavaScript
            if js_path:
                self.context.add_init_script(path = js_path)
            
            # cookie 登录
            if sessdata:
                self.context.add_cookies([{
                    'name': 'SESSDATA',
                    'value': sessdata,
                    'domain': ".bilibili.com",
                    'path': "/"
                }])
            
            self.page = self.context.new_page()
            # self.page.evaluate("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            logger.error(f"浏览器启动失败，错误: {str(e)}")
            raise
    
    def end_browser(self):
            # 按逆序关闭资源
        if self.page is not None:
            self.page.close()
        if self.context is not None:
            self.context.close()
        if self.browser is not None:
            self.browser.close()
        if self.p is not None:
            self.p.stop()
