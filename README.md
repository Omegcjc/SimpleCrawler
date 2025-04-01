# SimpleCrawler

> 网络信息内容安全：视频网站内容获取
>
> 2025.4
>
> author:曹佳程，王骏箫，吴尚哲
>
> 持续更新中......

## 一. 项目介绍
本项目为**网络信息内容安全：视频网站内容获取**作业部分

### 任务描述

开发一个或多个爬虫脚本，可以根据输入的视频节目的ID和搜索词，自动爬取对应视频网站中的该视频节目ID\该搜索词搜索下视频的标题、简介、播放量、频道和视频文件等。
为实现上述目标，请分析目标网站的结构，针对下述网站自动获取不同视频节目信息。

| 序号 | 网站名称          | 标题   | 简介   | 播放量 | 点赞数 | 热力值 | 提示  |
|------|-------------------|--------|--------|--------|--------|--------|-------|
| 1    | v.ifeng.com       | 存在   | 不存在 | 存在   | 存在   | 存在   |       |
| 2    | v.xiaodutv.com    | 存在   | 不存在 | 存在   | 存在   | 存在   |       |
| 3    | www.thepaper.cn   | 存在   | 存在   | 存在   | 存在   | 存在   |       |
| 4    | haokan.baidu.com  | 存在   | 不存在 | 存在   | 存在   | 存在   |       |
| 5    | www.ku6.com       | 存在   | 不存在 | 不存在 | 不存在 | 不存在 |       |
| 6    | v.cctv.cn         | 存在   | 存在   | 不存在 | 不存在 | 不存在 | HLS   |
| 7    | www.bilibili.com  | 存在   | 存在   | 存在   | 存在   | 存在   |       |

- 注意： 表格仅供参考，如有问题，请以事实为准

### 任务分工

- [1，3，7] 由 曹佳程 同学 完成
- [2，6] 由 王骏箫 同学 完成
- [4，5] 由 吴尚哲 同学 完成

### 爬取信息汇总
| 序号 | 网站名称          | title  | video_ID | author | publish_date | video_url | download_url | channel | duration | views | desc | likes | else |  
|------|-------------------|--------|----------|--------|--------------|-----------|--------------|---------|----------|-------|------|-------|-------|
| 1    | v.ifeng.com       | ✅     | ✅      | ✅     | ✅          | ✅        |   ✅        | ✅      | ✅      | ✅    |✅   |✅     |       |
| 2    | v.xiaodutv.com    |        |          |         |             |            |             |          |         |        |     |       |       |
| 3    | www.thepaper.cn   | ✅     | ✅      | ✅     | ✅          | ✅        |   ✅        | ✅      | ✅      |        |✅   |✅     |       |
| 4    | haokan.baidu.com  | ✅     | ✅      | ✅     | ✅          | ✅        |   ✅        | ✅      | ✅      | ✅    |✅   |✅     |       |
| 5    | www.ku6.com       | ✅     | ✅      |        |             | ✅        |   ✅        | ✅      |          |        |      |       |       |
| 6    | v.cctv.cn         |        |          |        |             |            |             |          |          |        |      |      |       |
| 7    | www.bilibili.com  | ✅     | ✅      | ✅     |             | ✅        |   ✅        | ✅      | ✅      | ✅    |✅   |✅     | ✅    |


- **video_url** ： 可直达视频网页
- **download_url** ： 视频资源下载地址
- **channel** : 可能为频道，可能为keywords，具体在对应代码中找寻
- **else** : 这里为bilibili特有的信息
  - **coins**：投币数
  - **favs**：收藏数
  - **shares**：转发数
## 二. 环境搭建参考

- 使用python内置的venv虚拟环境

### 1. 安装必要环境
```bash
pip install -r requirements.txt
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

## 三. 提示

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

## 四.项目文件架构

``` txt
SimpleCrawler/                      # [项目根目录]
├── .venv/                          # 虚拟环境venv相关配置
│   └── ...                         # 内置一些需要使用的python package,环境启动见README.md
├── base/                           # [基础文件]
|   └── base_client.py              # 客户端基本实现模块
├── config/                         # [配置文件]
│   ├── BaseConfig.py               # 全局浏览器配置（代理/请求头等）
│   ├── bilibiliConfig.py           # bilibili基础配置 (url, 文件保存路径等)
│   ├── ifengConfig.py              # ifeng基础配置(同上)
│   ├── thepaperConfig.py           # thepaper基础配置(同上)
│   ├── haokanConfig.py             # haokan基础配置(同上)
│   ├── ku6Config.py                # ku6基础配置(同上)
│   └── config.py                   # 日志记录基础配置文件(简写，可按照需要更改)
├── core/                           # [核心逻辑]
│   ├── bili_crawler.py             # bilibili爬虫核心模块
│   ├── ifeng_crawler.py            # ifeng爬虫核心模块 
│   ├── thepaper_crawler.py         # thepaper爬虫核心模块
│   ├── ku6_crawler.py              # ku6爬虫核心模块
│   └── haokan_crawler.py           # haokan爬虫核心模块
├── data/                           # [输出目录]                
│   └── */*                         # 输出文件path自定义
├── tools/                          # [工具脚本]
│   ├── file_tools.py               # 文件保存工具
│   ├── video_down_wget.py          # 视频下载工具(wget下载)
│   └── scraper_utils.py            # 浏览器界面辅助工具(如自动翻滚，关闭弹窗等)
├── additonal/                      # [其他文件目录]
│   ├── beifeng_ifeng_v1.0.py       # ifeng爬虫核心模块v1.0备份 - cjc
│   ├── haokan_crawler_v1.0.py      # haokan爬虫核心模块v1.0备份 - wsz
│   ├── ku6_crawler_v1.0.py         # ku6爬虫核心模块v1.0备份 - wsz
│   └── bili_crawler_v1.0.py        # bili爬虫核心模块v1.0备份 - cjc
├── stealth.min.js                  # bilibli 反反爬js文件
├── test_playwright.py              # 环境测试文件
├── requirements.txt                # 依赖库清单
└── main.py                         # 主入口文件(还没写)
```

## 五.REFERENCES

https://github.com/NanmiCoder/MediaCrawler

https://github.com/AntiQuality/VideoCrawl
