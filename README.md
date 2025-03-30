
# SimpleCrawler

## 一. 环境搭建参考

- 使用python内置的venv虚拟环境

### 1. 激活虚拟环境(windows)

```powershell
.\.venv\Scripts\activate.bat
```

### 2. 安装浏览器驱动

```powershell
python -m playwright install chromium
```

### 3.验证环境搭建成功

- 运行项目文件`test_playwright.py`，预计输出`百度一下，你就知道`.

```powershell
python test_playwright.py
```

### 4.windows支持wget

```bash

# 使用 Winget（Windows 11 内置）
winget install --id GUN.Wget
```

## 二. 提示

个别网站打开**开发者模式**后可以在**控制台**输入：

``` bash
# www.bilibli.com 对应的视频网站
window.__INITIAL_STATE__

# v.ifeng.com 对应的视频网站
allData

# www.thepaper.com 对应的视频网站
window.__NEXT_DATA__
```

如果其有值，可以简化获取信息的流程

## 三.项目文件架构图

``` txt
SimpleCrawler/                            # [项目根目录]
├── .venv/                          # 虚拟环境venv相关配置
│   └── ...                         # 内置一些需要使用的python package,环境启动见README.md
├── base/                           # [基础文件]
|   └── base_client.py              # 客户端基本实现模块
├── config/                         # [配置文件]
│   ├── BaseConfig.py               # 全局浏览器配置（代理/请求头等）
│   ├── bilibiliConfig.py           # bilibili基础配置 (url, 文件保存路径等)
│   ├── ifengConfig.py              # ifeng基础配置(同上)
│   ├── thepaperConfig.py           # thepaper基础配置(同上)
│   └── config.py                   # 日志记录基础配置文件(简写，可按照需要更改)
├── core/                           # [核心逻辑]
│   ├── bili_crawel.py              # bilibili爬虫核心模块
│   ├── ifeng_crawel.py             # ifeng爬虫核心模块 
│   └── thepaper_crawel.py          # thepaper爬虫核心模块
├── data/                           # [输出目录]                
│   └── */*                         # 输出文件path自定义
├── tools/                          # [工具脚本]
│   ├── file_tools.py               # 文件保存工具
│   ├── video_down_wget.py          # 视频下载工具(wget下载)
│   └── scraper_utils.py            # 浏览器界面辅助工具(如自动翻滚，关闭弹窗等)
├── additonal/                        # [其他文件目录]
│   ├── beifeng_ifeng_v1.0.py       # ifeng爬虫核心模块v1.0备份
│   └── bili_crawler_v1.0.py        # bili爬虫核心模块v1.0备份
├── stealth.min.js                  # bilibli 反反爬js文件
├── test_playwright.py              # 环境测试文件
├── requirements.txt                # 依赖库清单
└── main.py                         # 主入口文件(还没写)
```
