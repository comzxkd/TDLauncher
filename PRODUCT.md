# Product

<!-- impeccable:product-schema 1 -->

## Platform

desktop (Windows native, PySide6) —  impeccable 平台分类按 `web` 工作流处理，实际构建目标是 Qt 桌面窗口（1280×720 固定画布等比缩放）。

## Users

Telegram 重度下载用户：批量抓取频道/帖子媒体（含评论区媒体、相册分组），常用代理（socks5），在 Windows 桌面、夜间/挂机场景使用。核心诉求：贴上链接就走、进度一目了然、归档井井有条。

## Product Purpose

TDLauncher 是 tdl（Telegram 下载 CLI）的 Windows 桌面 GUI。它把 tdl 的命令行参数、链接解析、串行调度、进度输出翻译成一张可视化控制台：粘贴链接 → 识别 → 配置参数 → 逐条下载 → 按「频道名/消息ID」归档。成功 = 用户不看日志也知道下载进行到哪、剩多久、哪些已完成。

## Positioning

tdl 本身只有终端输出；同类 GUI 要么多开并行（会撞 tdl 的 session 独占锁导致失败），要么只是把命令拼起来。TDLauncher 的差异机制：**理解 tdl 约束的调度器**——严格串行遵守 session 锁、按帧解析 tdl 的 \r 刷新输出、评论区两步下载、数字 ID 与频道的语义化呈现。

## Operating Context

- Windows 11 桌面，pythonw 无窗口启动（`启动TDLauncher.bat`）。
- 常夜间/挂机运行，用户断续扫一眼进度。
- 需要代理连通 Telegram；下载目录常为大容量数据盘。
- tdl 进程必须串行（session 是 bolt 数据库带独占锁），这是不可违抗的技术事实。

## Capabilities and Constraints

- 链接类型：public_post / private_post / comment / thread。
- 参数：内容类型过滤、自定义扩展名、文件名模板、线程（-t，单条目内）、并发（-l，单进程内条目并发）、下载目录、代理。
- 开关：评论区下载、按帖归档、跳过重复、断点续传、Takeout 模式、相册分组、启用代理。
- 硬约束：tdl 进程串行；前端改动集中在 `app/main_window.py`；控件属性名不可改（见 AGENTS.md §4）。
- 仓库不含 tdl.exe（用户自置于 vendor/）。

## Brand Commitments

名称 TDLauncher；技术上依赖的 tdl 为 AGPL-3.0，本项目 MIT。用户明确表态：视觉世界完全开放、不设保留元素（2026-10-10 确认）。

## Evidence on Hand

真实数据形态：t.me 链接、频道 handle（如 @photolang）、消息 ID、媒体文件名（media_001.jpg）、tdl 输出的百分比/速度/ETA。无 logo 资产、无品牌指南。

## Product Principles

1. 一眼知状态：进度、队列、结果在任何一瞥下可读。
2. 尊重工具本性：这是给人操作机器的控制台，精确、诚实、不装饰数据。
3. 约束即设计：串行不是缺陷而是节奏——把「一次一条，条条清楚」做成体验。
4. 中文优先：界面语言为中文，字体与排版以中文渲染质量为先。
