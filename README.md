# SimpleCrawler

> 网络信息内容安全：视频网站内容获取
>
> 2025.4
>
> author:曹佳程，王骏箫，吴尚哲
>
> 持续更新中......
>
> 最新更新了框架 - 2025.4.13

## 一. 项目介绍

本项目为**网络信息内容安全：视频网站内容获取**作业部分

### 任务描述

#### 子任务一
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

#### 子任务二
深入了解网站的组成结构，探索各种网络资源的功能属性。

针对上述网站，对于每个网站自行挑选一个页面，对该页面中的所有网络资源（这些资源可以通过 浏览器开发者工具-网络 获取到）进行标识。标识的属性和维度请同学们自行设计，但应至少包括：1. 资源URL在页面中的功能；2. 资
源域名属于哪个组织（厂商，譬如第三方）；3. 资源URL是否可以直接访问等。

提示：开放性任务，需要同学们自行设计合理的资源标识体系，例如资源的功能和资源类型紧密相关；资源的重要性可以通过是否会阻碍其他资源加载来衡
量等等，言之有理即可。

### 任务分工

#### 子任务一
- [1，3，7] 由 曹佳程 同学 完成
- [2，6] 由 王骏箫 同学 完成
- [4，5] 由 吴尚哲 同学 完成

#### 子任务二
- 标识标准由大家共同商讨制定
- 代码部分主要由曹佳程，吴尚哲同学完成

### 爬取信息汇总
| 序号 | 网站名称          | title  | video_ID | author | publish_date | video_url | download_url | channel | duration | views | desc | likes | else |  
|------|-------------------|--------|----------|--------|--------------|-----------|--------------|---------|----------|-------|------|-------|-------|
| 1    | v.ifeng.com       | ✅     | ✅      | ✅     | ✅          | ✅        |   ✅        | ✅      | ✅      | ✅    |✅   |✅     |       |
| 2    | v.xiaodutv.com    |        |          |         |             |            |             |          |         |        |     |       |       |
| 3    | www.thepaper.cn   | ✅     | ✅      | ✅     | ✅          | ✅        |   ✅        | ✅      | ✅      |        |✅   |✅     |       |
| 4    | haokan.baidu.com  | ✅     | ✅      | ✅     | ✅          | ✅        |   ✅        | ✅      | ✅      | ✅    |✅   |✅     |       |
| 5    | www.ku6.com       | ✅     | ✅      |        |             | ✅        |   ✅        | ✅      |          |        |      |       |       |
| 6    | v.cctv.cn         | ✅     | ✅      | ✅     | ✅         |✅          |  ✅         |  ✅    |  ✅      |        |✅   |✅     |       |
| 7    | www.bilibili.com  | ✅     | ✅      | ✅     |             | ✅        |   ✅        | ✅      | ✅      | ✅    |✅   |✅     | ✅    |

- **注意**
  - **video_url** ： 可直达视频网页
  - **download_url** ： 视频资源下载地址
  - **channel** : 可能为频道，可能为keywords，具体在对应代码中找寻
  - **else** : 这里为bilibili特有的信息
    - **coins**：投币数
    - **favs**：收藏数
    - **shares**：转发数
### 网络信息标识体系

- **可访问性(accessible)** : 直接对URL进行http访问，HEAD 请求失败时降级为 GET 请求，返回状态码小于400, 即为可访问。可访问为为True，否则为False
- **供应商(vendor)** : 共三种结果可供参考
  - **whois**： 直接对域名进行查询
  - **dns解析 + ipwhois** : 获取 A 记录中第一个 IP 地址，对ip地址进行ipwhois查询，得到
    - **entities 信息**
    - **asn_description 信息**
- **功能性(function_description)** : 参考资源类型，简介其主要功能
  - 资源类型主要分为两种
    - **resource_type** ：  Playwright 用来分类网络请求的标准类型，主要有 “document，script” 等等。若其没有值，则启动人工自动分类，返回对应的resource_type,详情参考network_5.py中resource_function_mapping中的键值
    - **content_type** ： 响应头headers中content_type值
- **重要性(blocking_comment)** : 通过查看请求启动器链，判断资源是否妨碍其他资源加载，妨碍为True，否则为False



## 二. 环境搭建参考

> 推荐使用虚拟环境，在虚拟环境中运行
> 
> 使用python内置的venv虚拟环境或者其他

### 1. 虚拟环境搭建

> 这里提供 `vscode + venv`虚拟环境搭建参考

- `ctrl + shift + p` > 选择 `Python: Create Environment`
- 选择 `Venv` 在当前工作区创建`".venv"`虚拟环境
- 选择`Python解释器`，该项目推荐使用`python 3.12.4 64bit`
- 选择安装需要安转的依赖项`requirements.txt`
- 等待环境创建成功，最终项目文件会有`.venv`文件夹，即环境创建成功
- 激活虚拟环境：

```bash
.venv\Scripts\activate
```

> **务必记得需要启动虚拟环境**

### 2. 安装浏览器驱动

本项目默认用户安装`chrome`浏览器，若未安装浏览器，请安装以下浏览器驱动

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

### 5.windows支持ffmpeg

- 请前往下载ffmpeg预编译版本: https://www.gyan.dev/ffmpeg/builds/  -> 选择ffmpeg-release-essentials.7z版本下载
- 或者使用本项目提供的预编译版本 - ffmpeg-7.1.1-full_build.7z
- 解压完成后，需要将ffmpeg.exe文件所在的bin文件夹路径添加到系统变量中！！！

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
├── .venv/                          # 虚拟环境venv相关配置 (如果使用venv虚拟环境)
│   └── ...                         # 内置一些需要使用的python package,环境启动见README.md
│ 
├── base/                           # [基础文件]
│   ├── base_client.py              # 客户端实现基类
│   ├── base_config.py              # 配置实现基类
│   ├── base_crawler.py             # 爬虫实现基类
│   └── base_contentcrawler.py      # cctv + baisou 专用爬虫实现基类
│ 
├── config/                         # [配置文件]
│   ├── bilibiliConfig.py           # bilibili基础配置 (url, 文件保存路径等)
│   ├── ifengConfig.py              # ifeng基础配置(同上)
│   ├── thepaperConfig.py           # thepaper基础配置(同上)
│   ├── haokanConfig.py             # haokan基础配置(同上)
│   ├── ku6Config.py                # ku6基础配置(同上)
│   ├── cctvconfig.py               # cctv基础配置,暂无内容
│   └── config.py                   # 日志记录基础配置文件(简写，可按照需要更改)
│ 
├── core/                           # [核心逻辑]
│   ├── bili_crawler.py             # bilibili爬虫核心模块
│   ├── ifeng_crawler.py            # ifeng爬虫核心模块 
│   ├── thepaper_crawler.py         # thepaper爬虫核心模块
│   ├── ku6_crawler.py              # ku6爬虫核心模块
│   ├── cctv_crawler.py             # cctv爬虫核心模块
│   └── haokan_crawler.py           # haokan爬虫核心模块
│ 
├── data/                           # [输出目录]                
│   └── */*                         # 输出文件path自定义
│ 
├── tools/                          # [工具脚本]
│   ├── file_tools.py               # 文件保存工具
│   ├── video_down_wget.py          # 视频下载工具(wget单线程下载)
│   ├── download_manager.py         # 视频下载工具(wget多线程下载)
│   ├── scraper_utils.py            # 浏览器界面辅助工具(如自动翻滚，关闭弹窗等)
│   └── screen_display.py           # cctv + baisou 专用终端打印工具
│ 
├── additonal/                      # [其他文件目录]
│   ├── SimpleCrawler.zip           # 旧版SimpleCrawler框架_2025.4.2之前 - cjc
│   ├── beifeng_ifeng_v1.0.py       # ifeng爬虫核心模块v1.0备份 - cjc
│   ├── haokan_crawler_v1.0.py      # haokan爬虫核心模块v1.0备份 - wsz
│   ├── ku6_crawler_v1.0.py         # ku6爬虫核心模块v1.0备份 - wsz
│   └── bili_crawler_v1.0.py        # bili爬虫核心模块v1.0备份 - cjc
│
├── network_5.py                    # 子任务二对应实现文件
├── stealth.min.js                  # bilibli 反反爬js文件
├── test_playwright.py              # 环境测试文件
├── requirements.txt                # 依赖库清单
├── cli_paeser.py                   # 命令行参数解析器
└── main.py                         # 主入口文件
```

**注意**：
  - 上述**additional**文件夹中的代码环境可能不同，也可能无法运行，只作为**备份文件夹**
  - bilibili 视频下载并不完善
  - cctv + baisou使用selunim作为自动化浏览器工具
  - 使用基类默认视频下载函数时(wget)，网站和网速影响较大，如ku6网站需要等待较长时间


## 五.示例使用
- 命令行输入参考：
```bash
# SimpleCrawler 命令行解析器
# options:
#   -h, --help            show this help message and exit
#   -p PLATFORM, --platform PLATFORM
#                         指定爬取平台（bilibili, ku6, haokan, ifeng, thepaper, cctv, baisou）
#   -m {search,video}, --mode {search,video}
#                         指定爬取类型（search 或 video）
#   -t TARGET, --target TARGET
#                         指定目标（搜索关键词或视频ID，多个ID用英文逗号分隔）
#   --multithreaded       是否启用多线程下载（默认不启用）


# 命令行输入参考：
# 示例命令行输入：
python main.py -p bilibili -m search -t "python爬虫"
python main.py -p ku6 -m video -t "QdRTpiXkNC6iPrVnhaN5_tCg5UI." --multithreaded  # 启用多线程下载
python main.py --help # 查看帮助信息

# 手动输入示例：
python main.py

# 上述运行后结果示例：
请输入平台名称（bilibili, bili, ku6, haokan, ifeng, thepaper, cctv, baisou）：ku6
请输入爬取类型（搜索：search / 视频：video）：search
请输入搜索关键词：特朗普
是否启用多线程下载？（y/n，默认n）：n
2025-04-10 16:38:52,895 - core.ku6_crawler - INFO - ku6网站无法搜索，请直接输入视频ID

```

## 六.REFERENCES

https://github.com/NanmiCoder/MediaCrawler

https://github.com/AntiQuality/VideoCrawl

## 七.致谢

- 感谢美好的大模型 Chatgpt + deepseek + copilot + kimi 让整个项目的代码编写进入快车道

- 感谢曹佳程同学，王骏箫同学和吴尚哲同学的付出

- 最后，感谢每一天，都是debug的一天......

- 有任何问题可以联系曹佳程（3447999786@qq.com）
