<!-- markdownlint-disable MD033 -->
<h1 align="center">TDLauncher</h1>

<p align="center">
  <b>Telegram 高速下载器 · 可视化桌面工具</b><br>
  <sub>为 <a href="https://github.com/iyear/tdl">tdl</a> 提供 Windows 图形界面封装</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/PySide6-6.11-41cd52?logo=qt" alt="PySide6">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows%20x64-0078D4?logo=windows" alt="Windows">
</p>

---

[English](#english) · [中文](#中文)

---

<a id="english"></a>

## TDLauncher

A Windows desktop GUI for **tdl** — the Telegram downloader CLI. Paste Telegram links, pick your options, and download media with real-time progress.

### Features

- 📥 **Link-based download** — supports public posts (`t.me/channel/123`), private channels (`t.me/c/123/456`), comments, and threads
- 💬 **Comments section download** — auto-export and batch download media from comment threads
- 📁 **Smart archiving** — organize downloads by channel name + message ID (`ChannelName/12345/`)
- 🎵 **Content type filter** — all / images / videos / audio / custom extensions
- ⚙️ **Advanced options** — thread count, concurrency limit, proxy, filename templates, skip-duplicates, resume, takeout mode
- 📊 **Real-time progress** — progress bars + raw tdl output log
- 🔄 **Queue mode** — paste multiple links, download sequentially
- 🚀 **Takeout mode** — reduced rate-limit for bulk downloads
- 🌙 **Dark theme** — Telegram-inspired dark UI

### Prerequisites

- **Windows** x64
- **Python 3.12+**
- **tdl** — download from [GitHub Releases](https://github.com/iyear/tdl/releases)

### Quick Start

```powershell
# 1. Install tdl (one-time)
# Download tdl_Windows_64bit.zip from https://github.com/iyear/tdl/releases
# Extract tdl.exe and place it in your PATH, or run:
iwr -useb https://docs.iyear.me/tdl/install.ps1 | iex

# 2. Login (one-time)
tdl login -T qr

# 3. Clone & install TDLauncher
git clone https://github.com/comzxkd/TDLauncher.git
cd TDLauncher
pip install -r requirements.txt

# 4. Launch
python app\main.py
```

### Usage

1. **Paste one or more Telegram message links** into the text area
2. **Select content type** — All, Images, Videos, Audio, or Custom
3. **Choose download directory**
4. **Toggle advanced options** as needed:
   - Comments section download
   - Auto-archive by channel + message ID
   - Proxy, threads, concurrency limit
   - Skip duplicates, resume, takeout mode
5. **Click "Start Download"** — watch real-time progress in the log panel

#### Example links

```
https://t.me/telegram/193              # Public post
https://t.me/c/1697797156/151          # Private channel post
https://t.me/simisebaisi/50063?comment=211049  # Comment link
https://t.me/myhostloc/1485524?thread=1485523  # Thread link
```

### Build Standalone EXE

```powershell
pip install pyinstaller
pyinstaller --noconsole --name TDLauncher --icon resources/icon.ico ^
  --add-data "vendor/tdl.exe;vendor" ^
  app/main.py
```

> **Note**: `vendor/tdl.exe` is not included in this repository. For a portable build, download `tdl_Windows_64bit.zip` from [tdl releases](https://github.com/iyear/tdl/releases), extract `tdl.exe` into the `vendor/` directory, then run the build command above.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| GUI | PySide6 (Qt 6) |
| Backend | Python 3.12+ |
| Download Engine | [tdl](https://github.com/iyear/tdl) (Golang, AGPL-3.0) |
| Process Management | QProcess (async, non-blocking) |

### Project Structure

```
TDLauncher/
├── app/
│   ├── main.py              ← Entry point
│   ├── main_window.py       ← Main UI (751 lines)
│   ├── config.py            ← Config read/write (JSON)
│   ├── link_parser.py       ← Telegram link parser
│   ├── command_builder.py   ← tdl command builder
│   ├── tdl_runner.py        ← QProcess wrapper
│   └── progress_parser.py   ← Progress extractor
├── docs/                    ← Design documents
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

### Credits

- [iyear/tdl](https://github.com/iyear/tdl) — the incredible Telegram toolkit this project wraps
- Qt for Python (PySide6) — LGPL-3.0 licensed GUI framework

### License

This project is licensed under the **MIT License**.

The underlying download engine **tdl** is licensed under **AGPL-3.0**. When you run TDLauncher, the `tdl.exe` binary (a separate, unmodified program) is invoked as a subprocess, and its source code is available at [github.com/iyear/tdl](https://github.com/iyear/tdl).

---

<a id="中文"></a>

## TDLauncher

Telegram 高速下载器的 Windows 桌面图形界面。粘贴链接、选择选项，实时查看下载进度。

### 功能

- 📥 **链接下载** — 支持公开帖子、私有频道、评论链接、话题链接
- 💬 **评论区下载** — 自动导出并批量下载评论区中的媒体
- 📁 **智能归档** — 按频道显示名 + 消息 ID 自动分类存放
- 🎵 **内容过滤** — 全部 / 图片 / 视频 / 音频 / 自定义扩展名
- ⚙️ **高级选项** — 线程数、并发限制、代理、文件名模板、去重、断点续传、Takeout 模式
- 📊 **实时进度** — 进度条 + tdl 原始输出日志
- 🔄 **队列模式** — 粘贴多个链接，依次下载
- 🚀 **Takeout 模式** — 降低限流惩罚，适合大批量下载
- 🌙 **深色主题** — Telegram 风格暗色界面

### 快速开始

```powershell
# 1. 安装 tdl（仅首次）
# 从 https://github.com/iyear/tdl/releases 下载 tdl_Windows_64bit.zip
# 解压 tdl.exe 放到 PATH 目录，或一键安装：
iwr -useb https://docs.iyear.me/tdl/install.ps1 | iex

# 2. 登录（仅首次）
tdl login -T qr

# 3. 克隆并安装依赖
git clone https://github.com/comzxkd/TDLauncher.git
cd TDLauncher
pip install -r requirements.txt

# 4. 启动
python app\main.py
```

### 使用说明

1. **粘贴一个或多个 Telegram 消息链接**
2. **选择内容类型** — 全部、图片、视频、音频或自定义
3. **选择下载目录**
4. **配置高级选项**（可选）：
   - 下载评论区媒体
   - 自动按帖子归档（频道名/消息ID）
   - 代理、线程数、并发限制
   - 去重、断点续传、Takeout 模式
5. **点击「开始下载」** — 在日志面板中查看实时进度

### 打包为独立 EXE

```powershell
pip install pyinstaller
pyinstaller --noconsole --name TDLauncher --icon resources/icon.ico ^
  --add-data "vendor/tdl.exe;vendor" ^
  app/main.py
```

> **注意**：本仓库不包含 `vendor/tdl.exe`。如需制作便携包，请从 [tdl releases](https://github.com/iyear/tdl/releases) 下载后放入 `vendor/` 目录，再执行上方打包命令。

### 致谢

- [iyear/tdl](https://github.com/iyear/tdl) — 本项目包装的 Telegram 工具包，功能强大
- Qt for Python (PySide6) — LGPL-3.0 许可的 GUI 框架

### 许可

本项目采用 **MIT 许可**。

底层下载引擎 **tdl** 采用 **AGPL-3.0 许可**。TDLauncher 以子进程方式调用 tdl.exe（独立、未修改的程序），其源码见 [github.com/iyear/tdl](https://github.com/iyear/tdl)。
