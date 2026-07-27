# TDLauncher 正式版设计文档

> 目标：为 `tdl` 构建一个稳定、易用、可扩展的 Windows 本地图形界面。  
> 定位：Telegram 媒体下载工作流工具，而不只是 `tdl dl -u` 的按钮封装。

---

## 1. 项目背景

当前已经完成了一个 PowerShell WinForms 原型，用于验证：

- `tdl` 安装与登录；
- 代理下载；
- 原始文件名模板；
- 多链接下载队列；
- tdl 输出中的百分比与速度解析；
- 配置保存；
- 目录选择。

但原型版继续扩展会遇到明显瓶颈：

- PowerShell WinForms 的子进程输出捕获不稳定；
- UI 布局和复杂交互维护成本高；
- 评论区导出、临时 JSON、任务队列会让脚本快速膨胀；
- 打包与分发体验较弱。

因此，PowerShell 版应冻结为“验证原型”，正式版建议重写。

---

## 2. 产品目标

一句话目标：

> 把 tdl 的“链接下载 + 评论区导出 + JSON 批量下载 + 过滤选项”封装成一个 Windows 本地可视化下载工作台。

核心体验：

1. 用户粘贴 Telegram 链接；
2. 程序自动识别链接类型；
3. 用户选择下载内容类型、目录和高级选项；
4. 点击下载；
5. 界面实时显示 tdl 原始输出、速度和进度；
6. 如开启评论区下载，自动执行导出与批量下载流程。

---

## 3. 推荐技术路线

### 3.1 推荐方案：Python + PySide6

选择理由：

- 子进程管理稳定，适合长期运行下载任务；
- stdout/stderr 实时读取更可靠；
- GUI 组件成熟；
- 便于打包为 Windows exe；
- 本地文件、配置、日志处理方便；
- 后续可扩展任务队列、历史记录、错误重试。

### 3.2 暂不推荐继续使用 PowerShell GUI

PowerShell 版适合原型验证，不适合正式版继续扩展。

原因：

- 复杂状态管理不直观；
- 异步事件容易出现运行期问题；
- UI 自适应布局维护困难；
- 打包成独立应用体验一般。

### 3.3 可选路线：Python + PyWebView

适合后续想做更漂亮的网页式界面，但第一版不建议采用。

原因：

- 多一层前后端通信；
- 打包和调试链路更复杂；
- 当前工具重心是本地命令调度，桌面 GUI 更直接。

---

## 4. 版本规划

### V0.1：MVP，稳定下载核心

必须实现：

- Telegram 链接输入；
- 多链接任务队列；
- 下载目录选择与记忆；
- 内容类型过滤；
- 代理、线程、并发设置；
- 原始 tdl 输出窗口；
- 当前任务状态；
- 总任务进度；
- 配置保存；
- 失败日志保留。

不做：

- 评论区自动下载；
- 频道选择器；
- 上传/转发；
- 高级模板编辑器；
- 任务历史数据库。

### V0.2：评论区自动下载

核心增强：

- 解析普通帖子链接；
- 自动执行 `tdl chat export --reply`；
- 再执行 `tdl dl -f comments.json`；
- 评论区内容类型过滤；
- 临时 JSON 管理；
- 评论区为空、导出失败、私有频道异常提示。

### V0.3：产品化增强

可加入：

- 文件名模板折叠面板；
- 模板预设；
- 下载历史；
- 失败重试；
- `tdl chat ls` 频道搜索；
- 登录状态检测；
- `tdl backup/recover` 会话备份入口。

### V1.0：完整工作台

可考虑：

- 上传文件；
- 转发消息；
- 批量导出频道媒体；
- 成员导出；
- 多账号命名空间；
- 任务数据库。

---

## 5. MVP 功能结构

### 5.1 主界面布局

建议窗口尺寸：`960 × 720`，支持缩放。

布局：

```text
┌────────────────────────────────────────────┐
│ TDLauncher                                 │
├────────────────────────────────────────────┤
│ Telegram 链接输入                          │
│ ┌────────────────────────────────────────┐ │
│ │ 每行一个链接                           │ │
│ └────────────────────────────────────────┘ │
│ [粘贴] [清空]  识别结果：普通帖子/评论链接 │
├────────────────────────────────────────────┤
│ 下载设置                                   │
│ 内容类型: (全部媒体) (仅图片) (仅视频) (自定义)│
│ 下载目录: [D:\Downloads              ] [...]│
│ 文件名:   (原始文件名) (tdl默认)            │
├────────────────────────────────────────────┤
│ 高级设置                                   │
│ 代理: [socks5://127.0.0.1:7897]            │
│ 线程: [8]  并发: [4]                       │
│ ☑ 跳过同名  ☑ 断点续传  ☐ MIME修正扩展名  │
├────────────────────────────────────────────┤
│ 操作区                                     │
│ [开始下载] [停止] [打开目录]                │
│ 当前任务: 37.4% | 5.5 MiB/s                │
│ 总任务: 2/7                                │
├────────────────────────────────────────────┤
│ tdl 原始输出日志                           │
│ ┌────────────────────────────────────────┐ │
│ │ All files will be downloaded...        │ │
│ │ Telegram News ... 37.4% ... 5.5MiB/s   │ │
│ └────────────────────────────────────────┘ │
└────────────────────────────────────────────┘
```

### 5.2 输入区

功能：

- 支持多行链接；
- 自动去空行；
- 自动去重；
- 粘贴后即时识别链接类型；
- 非 Telegram 链接标红或提示。

支持格式：

```text
https://t.me/telegram/193
https://t.me/c/1697797156/151
https://t.me/username/123
https://t.me/simisebaisi/50063?comment=211049
https://t.me/myhostloc/1485524?thread=1485523
```

### 5.3 内容类型

单选：

| UI 选项 | tdl 参数 |
|---|---|
| 全部媒体 | 不加 `-i` |
| 仅图片 | `-i jpg,png,gif,webp,jpeg` |
| 仅视频 | `-i mp4,mkv,mov,avi,webm,flv` |
| 自定义 | `-i 用户输入` |

### 5.4 高级下载选项

第一版建议支持：

| UI 选项 | tdl 参数 |
|---|---|
| 跳过同名同大小 | `--skip-same` |
| 断点续传 | `--continue` |
| 重新开始 | `--restart` |
| MIME 修正扩展名 | `--rewrite-ext` |
| 反序下载 | `--desc` |
| 分组/相册探测 | `--group` |

注意：`--continue` 和 `--restart` 互斥，界面要做互斥逻辑。

---

## 6. 链接解析规则

### 6.1 数据结构

```python
class ParsedLink:
    raw_url: str
    kind: str  # public_post | private_post | comment | thread | unknown
    channel: str | None
    chat_id: str | None
    message_id: int | None
    comment_id: int | None
    thread_id: int | None
```

### 6.2 公开频道链接

```text
https://t.me/simisebaisi/50063
```

解析：

```text
kind = public_post
channel = simisebaisi
message_id = 50063
```

### 6.3 私有频道链接

```text
https://t.me/c/1697797156/151
```

解析：

```text
kind = private_post
chat_id = 1697797156
message_id = 151
```

注意：私有频道在 `tdl chat export -c` 中是否应使用 `1697797156` 或 `-1001697797156` 需要实测验证。

### 6.4 评论链接

```text
https://t.me/simisebaisi/50063?comment=211049
```

解析：

```text
kind = comment
channel = simisebaisi
message_id = 50063
comment_id = 211049
```

如果用户勾选“下载评论区”，应提示：

```text
该链接已经指向具体评论，无法再按帖子批量导出评论区。
```

### 6.5 话题链接

```text
https://t.me/myhostloc/1485524?thread=1485523
```

解析：

```text
kind = thread
channel = myhostloc
message_id = 1485524
thread_id = 1485523
```

V0.1 只作为普通链接下载。  
V0.2 再考虑 `tdl chat export --topic`。

---

## 7. tdl 命令映射

### 7.1 普通链接下载

```powershell
tdl dl -u <url> -d <dir> --proxy <proxy> -t <threads> -l <limit>
```

如果启用原始文件名：

```powershell
--template "{{ filenamify .FileName }}"
```

### 7.2 多链接下载

两种实现：

方案 A，单链接一个任务：

```powershell
tdl dl -u <url1>
tdl dl -u <url2>
```

优点：状态清楚，单个失败不影响全部。  
缺点：tdl 内部并发能力利用较弱。

方案 B，一个 tdl 进程带多个 `-u`：

```powershell
tdl dl -u <url1> -u <url2> -u <url3>
```

优点：能更好利用 tdl 内部并发。  
缺点：GUI 较难精确区分每个链接状态。

MVP 建议采用方案 A。

### 7.3 评论区下载流程

```powershell
# 第一步：下载帖子本身
tdl dl -u <post_url> -d <dir>

# 第二步：导出评论区媒体
tdl chat export -c <channel> --reply <message_id> -o <tmp_json>

# 第三步：下载评论区媒体
tdl dl -f <tmp_json> -d <dir>
```

如果仅图片：

```powershell
-i jpg,png,gif,webp,jpeg
```

如果仅视频：

```powershell
-i mp4,mkv,mov,avi,webm,flv
```

---

## 8. 进程与日志架构

### 8.1 进程模型

```text
GUI 主线程
   ↓ 创建任务
TaskManager
   ↓ 启动子进程
TdlRunner
   ↓ 实时读取 stdout/stderr
ProgressParser
   ↓ 更新 UI 信号
MainWindow
```

### 8.2 tdl 输出处理

Python 中使用 `QProcess` 或 `subprocess.Popen`。

推荐 PySide6：

```python
process = QProcess()
process.readyReadStandardOutput.connect(handle_stdout)
process.readyReadStandardError.connect(handle_stderr)
```

输出直接追加到日志窗口，并同时解析：

- 百分比：`(?P<percent>\d+(?:\.\d+)?)%`
- 速度：`;\s*(?P<speed>[^\]]+/s)\]`

### 8.3 日志策略

目录：

```text
logs/
  app.log
  task_20260715_120000.log
  failed_20260715_120300.log
```

策略：

- 成功任务日志保留最近 N 条或自动清理；
- 失败任务日志长期保留；
- app.log 超过 5MB 轮转；
- UI 中提供“打开日志目录”。

---

## 9. 配置文件

路径：

```text
config.json
```

建议结构：

```json
{
  "download_dir": "D:/Downloads",
  "proxy": "socks5://127.0.0.1:7897",
  "threads": 8,
  "limit": 4,
  "content_type": "all",
  "custom_extensions": "",
  "filename_template": "{{ filenamify .FileName }}",
  "skip_same": true,
  "continue": false,
  "rewrite_ext": false,
  "group": true,
  "desc": false,
  "auto_subfolder": false
}
```

---

## 10. 模块划分

建议目录：

```text
TDLauncher/
  app/
    main.py
    main_window.py
    config.py
    link_parser.py
    task_model.py
    task_manager.py
    tdl_runner.py
    progress_parser.py
    command_builder.py
    log_manager.py
  resources/
    icon.ico
  vendor/
    tdl.exe
  config.json
  logs/
  downloads/
```

### 10.1 `link_parser.py`

职责：

- 解析 Telegram 链接；
- 判断链接类型；
- 提取 channel、message_id、comment_id、thread_id；
- 返回 `ParsedLink`。

### 10.2 `command_builder.py`

职责：

- 根据任务配置生成 tdl 命令；
- 负责路径、模板、代理等参数转义；
- 避免 UI 代码直接拼命令。

### 10.3 `tdl_runner.py`

职责：

- 启动 tdl 子进程；
- 捕获输出；
- 停止进程树；
- 返回退出码。

### 10.4 `task_manager.py`

职责：

- 管理任务队列；
- 顺序或并发执行；
- 维护任务状态：pending/running/success/failed/stopped；
- 处理下载帖子 + 评论区的多阶段任务。

### 10.5 `progress_parser.py`

职责：

- 从 tdl 输出中提取百分比、速度、耗时；
- 清理 ANSI 控制符；
- 识别错误信息。

---

## 11. 任务状态模型

```python
class DownloadTask:
    id: str
    source_url: str
    parsed_link: ParsedLink
    target_dir: str
    content_type: str
    custom_extensions: str | None
    include_comments: bool
    status: str  # pending/running/success/failed/stopped
    stage: str   # post_download/comment_export/comment_download
    progress: float
    speed: str
    log_path: str
    error_message: str | None
```

---

## 12. 错误处理

| 情况 | 处理 |
|---|---|
| tdl.exe 不存在 | 弹窗提示，提供选择路径 |
| 未登录 | 显示登录提示，提供 `tdl login -T qr` 指令 |
| 代理错误 | 显示 tdl 原始错误，保留日志 |
| 链接无效 | 输入区标红，不允许开始 |
| 下载失败 | 状态标记 failed，保留日志 |
| 评论区导出失败 | 帖子下载保留，评论区任务 failed |
| 用户停止任务 | 杀进程树，状态 stopped |

---

## 13. 打包方案

推荐：PyInstaller。

打包结构：

```text
TDLauncher.exe
vendor/tdl.exe
resources/icon.ico
```

命令示例：

```powershell
pyinstaller --noconsole --name TDLauncher --icon resources/icon.ico app/main.py
```

注意：

- `tdl.exe` 可作为外部文件放在 `vendor/`；
- 首次启动检查 `vendor/tdl.exe`，找不到则尝试系统 PATH；
- 不建议把 tdl.exe 硬塞进单文件 exe，升级不方便。

---

## 14. 关键技术风险

### 14.1 tdl 输出格式变化

进度解析依赖 tdl 文本输出。  
解决：保留原始输出窗口，即使解析失败，用户仍能看到真实日志。

### 14.2 评论区导出对私有频道支持需实测

公开频道：`-c simisebaisi --reply 50063` 明确可行。  
私有频道：`t.me/c/...` 需要验证 `-c` 参数应传哪种 ID。

### 14.3 下载速度受代理限制

GUI 不应承诺提速，只负责更好调用 tdl。速度仍由 Telegram 账号、代理和节点质量决定。

### 14.4 文件覆盖与重名

默认建议启用 `--skip-same`，避免重复下载。

---

## 15. 第一阶段验收标准

V0.1 完成后，应满足：

- 能粘贴 1 个或多个链接；
- 能选择目录并记住；
- 能按全部/图片/视频过滤；
- 能显示 tdl 原始输出；
- 能显示当前下载速度；
- 能显示当前任务进度和总任务进度；
- 能停止任务；
- 失败时保留日志；
- 重启程序后设置仍在。

---

## 16. 下一步建议

下一步不要继续扩展 PowerShell 原型。建议直接开始创建 Python 项目骨架，先做 V0.1。

推荐第一批实现文件：

1. `config.py`
2. `link_parser.py`
3. `command_builder.py`
4. `tdl_runner.py`
5. `main_window.py`
6. `main.py`

先跑通一条链路：

```text
粘贴链接 → 生成 tdl 命令 → 启动子进程 → 输出到日志窗口 → 下载完成
```

等 V0.1 稳定后，再加评论区自动下载。
