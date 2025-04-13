
import random
from time import sleep
from playwright.sync_api import Page

def dynamic_scroll(page:Page, scroll_times=2):
    """模拟人工滚动"""
    for _ in range(scroll_times):
        page.mouse.wheel(0, random.randint(800, 1200))
        sleep(random.uniform(1.2, 2.5))

def close_popups(page:Page, max_attempts=3):
    """弹窗关闭策略"""
    for _ in range(max_attempts):
        if close_btn := page.query_selector('.header-vip-close, .popup-close'):
            close_btn.click(timeout=2000)
            sleep(0.8)