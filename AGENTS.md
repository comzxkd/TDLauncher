# AGENTS.md — TDLauncher 工作交接

> 面向接手本项目的 AI agent / 开发者。目标：让你**不踩坑**地继续维护，而不是从零读代码。
> 项目：tdl（Telegram 下载 CLI）的 Windows 桌面 GUI。技术栈 Python 3.12 + PySide6。
> 仓库：https://github.com/comzxkd/TDLauncher　｜　许可：MIT（依赖的 tdl 为 AGPL-3.0）
> 更新：2026-07-22

---

## 0. 先读这里

- 项目本体是 `app/` 下 7 个 Python 文件；**绝大部分逻辑在 `app/main_window.py`**（界面 + 下载调度，1200+ 行）。
- 详细背景见 `docs/项目总览.md`；迭代过程与踩坑记录见 `docs/开发日志.md`。
- 有改动需求时，**先读完本文件第 1、4 节**再动手。

---

## 1. 铁律（违反会直接出错）

1. **tdl 进程必须串行**。tdl 的登录 session 是 bolt 数据库、带**独占锁**，同时开两个进程会报
   `Current database is used by another process, please terminate it first`。
   所以链接与链接之间只能一条一条下载，**不要**试图改成多进程并行。
   （`-l` 并发数只在**单条链接内部**对多个媒体条目生效。）
2. **前端改动只动 `app/main_window.py`**。后端五个模块 `config.py / link_parser.py / command_builder.py / tdl_runner.py / progress_parser.py` 属于稳定层，**非明确要求不要动**。
3. **不要重命名 `MainWindow` 的控件属性**（见第 4 节列表）。`_apply_config` / `_save_config` / 下载逻辑都直接引用它们，改名会静默失效。
4. **测试/预览不要打扰正在运行的实例**。渲染预览用 `tools/preview_ui.py`（离屏、不弹窗）。
5. **测试后必须还原 `config.json`**：任何走到 `_start_download` 的测试都会经 `_save_config` 改写它（下载目录、并发等）。
6. **不要把 `config.json` / `vendor/` / `logs/` / `dist/` / `*.bak` 提交进仓库**（已在 `.gitignore` 中）。

---

## 2. 环境与运行

```powershell
pip install -r requirements.txt        # 仅 PySide6
python app\main.py                     # 运行（源码）
```

- 启动脚本：`启动TDLauncher.bat`（用 `pythonw` 无窗口启动）。
- `tdl.exe` 查找顺序（`_find_tdl`）：`vendor/tdl.exe` → PyInstaller `_internal/vendor/tdl.exe` → `~/.tdl/bin/tdl.exe` → `C:\tdl\tdl.exe` → 系统 PATH。仓库**不含** tdl.exe，需自行从 [tdl releases](https://github.com/iyear/tdl/releases) 放到 `vendor/`。

打包：

```powershell
pyinstaller --noconsole --name TDLauncher --add-data "vendor/tdl.exe;vendor" app/main.py
```

---

## 3. 文件地图

| 文件 | 职责 | 维护建议 |
|---|---|---|
| `app/main.py` | 入口：QApplication + 图标 + MainWindow | 基本不动 |
| `app/config.py` | `Config` dataclass、`load()`/`save()` 读写 `config.json` | 仅在需新增配置项时动 |
| `app/link_parser.py` | 链接 → `ParsedLink`（public_post/private_post/comment/thread/unknown） | 稳定 |
| `app/command_builder.py` | 链接 + 配置 → tdl 参数列表（含评论区两步） | 改 tdl 参数时动 |
| `app/tdl_runner.py` | QProcess 封装，异步 stdout/stderr，停止杀进程树 | 稳定 |
| `app/progress_parser.py` | 从 tdl 输出提取百分比/速度/错误 | 稳定 |
| `app/main_window.py` | **全部界面与下载调度** | 前端改动主战场 |
| `tools/preview_ui.py` | 离屏渲染主窗口为 PNG（不弹窗、不改配置） | 用于验证界面 |
| `docs/` | 总览 / 开发日志 / 设计文档 | 改动后同步 |

---

## 4. 前端控件契约（**不可改名**）

`_apply_config` / `_save_config` 与下载逻辑依赖以下属性名，重构界面时保留：

```
输入区：  _txt_links _lbl_recognition _btn_clear
参数区：  _combo_content _txt_custom_ext _combo_template
          _spin_threads _spin_limit _txt_dir _btn_browse _txt_proxy
选项开关：_chk_comments _chk_subfolder _chk_skip_same _chk_resume
          _chk_takeout _chk_group _chk_proxy
进度区：  _lbl_current _lbl_url _lbl_badge _lbl_bigpct _cells
          _lbl_speed _lbl_eta _lbl_totalcount _lbl_status
队列：    _queue_box _queue_rows   （行是 QueueRow）
详情文件：_files_box _detail_files _detail_file_rows （行是 FileRow）
日志：    _txt_output _btn_log
状态栏：  _lbl_tdlpath _lbl_sstate _lbl_path
按钮：    _btn_start _btn_stop _btn_open_dir
任务模型：_jobs（列表） _sel（当前选中序号）
```

`main_window.py` 内的类：`TipLabel`（带阴影悬浮提示）、`CellsBar`（24 格量化进度）、`QueueRow`、`FileRow`、`Job`、`MainWindow`。

---

## 5. 改前端怎么做

1. 样式集中在 `MainWindow._apply_theme()` 的 QSS 字符串里；**窗口缩放**在 `resizeEvent` / `_fit`（固定画布 `DESIGN_W×DESIGN_H = 1280×720`）。
2. 布局在 `_build_ui()`：顶栏 → 左链接(`body` 里 stretch 1) → 右栏(参数 / `work`(队列|进度)) → 状态栏。
3. 队列每行是 `QueueRow`（可点击切到详情）；切详情走 `_select_job` → `_show_detail`。
4. 加控件时，若它属于「配置项」，需同步扩展 `Config` 与 `_apply_config`/`_save_config`（会动 `config.py`，属后端，需确认）。

---

## 6. 测试与预览（**必须做**）

### 看界面（不弹窗、不动配置）

```powershell
python tools\preview_ui.py
# 生成 tools\preview\preview-1280x720.png 与 preview-2560x1440.png
```

原理：`WA_DontShowOnScreen` + `grab()`，用真实字体栈且不显示窗口。
（**别用** `QT_QPA_PLATFORM=offscreen`，它不加载系统字体，中文会全变方块。）

### 模拟下载流程（无真实 tdl）

用假的 `TdlRunner` 替换，验证调度与输出翻译：

```python
import main_window as mw
class FakeRunner:
    def __init__(self, path): self.is_running = False
    def start(self, args): self.is_running = True   # 需要时手动调 self.on_exit(0)
    def stop(self): self.is_running = False
mw.TdlRunner = FakeRunner
mw.QMessageBox.warning = staticmethod(lambda *a, **k: None)
mw.QMessageBox.information = staticmethod(lambda *a, **k: None)
mw.MainWindow._check_login_status = lambda self: None
```

可验证：逐条串行调度（同时只 1 个 `running`）、`done!` 逐项完成、数字 ID 加 `#`、命令退出后文件行标记完成。
**注意**：任何调用 `_start_download` 的测试都会改写 `config.json`，测完还原。

### 真实验收

重启 `启动TDLauncher.bat`，跑真实链接：确认归档为「频道名/消息ID」、评论区子项下完变「完成」。

---

## 7. 已知坑（血泪，别重复踩）

| 坑 | 现象 | 正确做法 |
|---|---|---|
| tdl session 独占锁 | 第二个 tdl 进程报 `Current database is used by another process` | 进程串行，别并行 |
| `-t` / `-l` 语义 | 以为 `-l` 无用 | `-t`=单条目线程；`-l`=单进程内并发条目数 |
| 批量并行（单进程多 `-u`） | 归档变数字、漏文件、99% 卡住、计数不变 | 已**整段移除**，别再引入 |
| Gemini 改的 UI | 间距 12/16 撑爆 960×720，按钮被挤出/点不动 | 只取配色，保留原布局 |
| 离屏渲染字体 | 中文全变方块 | 用 `WA_DontShowOnScreen` |
| tdl 描述无文件名 | 进度行只有「频道(id):消息ID」 | 逐文件列表只能显示描述符 |
| 子项进度卡 0% | 未解析 tdl 的 `done!` | 解析 `done!` 标记完成 |
| 测试污染 config | 下载目录/并发被改 | 测完还原 `config.json` |
| git push SSL 失败 | `schannel: failed to receive handshake` | 循环重试 2~3 次 |

---

## 8. tdl 输出翻译约定（改这部分前必读）

tdl 用 `\r` 每秒约 30 帧原地刷新。`main_window.py` 的 `_process_job_frame` 按帧分流：

- 进度帧（含 `数字% [`）→ `_apply_progress_frame` → 只更新 UI（大数字/格量/文件行/速度/ETA），**不写日志**。
- `CPU: … Memory: …` → 丢弃。
- 其余 → `job.log` + 可折叠日志；其中含 `done!` 的行 → 把对应文件行标记完成。
- 描述键 `_desc_key`：取 `->`/`→` 左侧、去 `-> …` 后缀，纯数字加 `#` 前缀。

---

## 9. 提交约定

- 提交前：`python tools\preview_ui.py` 看一眼；确认没跑坏 `config.json`。
- 提交信息用中文、动宾短语，例：`fix: 解析 done! 逐项完成标记`。
- 只提交源码与文档，**不要**提交 `config.json` / `vendor/` / 预览 PNG（已在 `.gitignore`）。

---

## 10. 待办 / 决策记录

**待办**
- [ ] 进度区大百分比改为「整体进度」（已完成条目/总数），评论区场景更直观（当前是当前文件进度）。
- [ ] 配置持久化扩展（如并发模式开关状态）；注意 `Config` 加字段属后端改动。

**已决策**
- 界面：终端风格（黑底+磷绿）、16:9 等比缩放（固定 1280×720 画布）。
- 下载：逐条串行（受 session 锁限制），保留 `-l` 给单条内部并发。
- 归档：`{下载目录}/{频道显示名}/{消息ID}/`。
- 并发/批量模式：**已移除**，不再使用。

---

## 11. 一句话给下一个 agent

改界面 → 动 `main_window.py`，用 `tools/preview_ui.py` 验证；
改下载逻辑 → 记住 tdl 必须串行、输出按帧分流；
动后端 → 先确认真的必要，并同步 `docs/`。
