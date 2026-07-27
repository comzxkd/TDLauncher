import os
import sys
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QSpinBox,
    QGroupBox, QProgressBar,
    QFileDialog, QMessageBox, QSplitter,
)

from config import Config
from link_parser import parse_telegram_link, ParsedLink
from command_builder import build_download_commands
from tdl_runner import TdlRunner
from progress_parser import ProgressParser


def _find_tdl() -> Optional[str]:
    """查找 tdl.exe 路径。从源码运行时需自行安装 tdl（https://github.com/iyear/tdl）。"""
    # PyInstaller 打包后数据文件在 _internal/ 下
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))

    candidates = [
        os.path.join(base, "vendor", "tdl.exe"),
        os.path.join(base, "_internal", "vendor", "tdl.exe"),
        os.path.expanduser("~/.tdl/bin/tdl.exe"),
        r"C:\tdl\tdl.exe",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    # 尝试系统 PATH
    for p in os.environ["PATH"].split(";"):
        full = os.path.join(p, "tdl.exe")
        if os.path.isfile(full):
            return full
    return None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TDLauncher - Telegram 下载器")
        self.setMinimumSize(960, 720)

        self._config = Config.load()
        if self._config.window_width and self._config.window_height:
            self.resize(self._config.window_width, self._config.window_height)

        self._tdl_path = _find_tdl()
        self._runner: Optional[TdlRunner] = None
        self._progress_parser = ProgressParser()

        self._current_task_index = 0
        self._task_commands: list = []
        self._task_labels: list = []
        self._total_tasks = 0
        self._completed_tasks = 0
        self._channel_display_name: str = ""
        self._chat_info_cache: dict = {}  # username -> visible_name

        self._build_ui()
        self._apply_theme()
        self._apply_config()
        self._update_status_bar()

        if not self._tdl_path:
            QMessageBox.warning(self, "TDLauncher", "未找到 tdl.exe，请确认安装路径。")
        else:
            self._check_login_status()

    # ---- UI 构建 ----

    def _apply_theme(self):
        qss = '''
            QMainWindow, QWidget {
                background-color: #182533;
                color: #F5F6F7;
                font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
                font-size: 13px;
            }
            QStatusBar {
                background-color: #111b24;
                color: #7f91a4;
                border-top: 1px solid #242F3D;
            }
            QTextEdit, QLineEdit {
                background-color: #242F3D;
                border: 1px solid #2B394A;
                border-radius: 6px;
                padding: 4px 8px;
                color: #FFFFFF;
            }
            QTextEdit:focus, QLineEdit:focus {
                border: 1px solid #5288c1;
            }
            QGroupBox {
                background-color: #1c2a38;
                border: 1px solid #243444;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                font-weight: bold;
                color: #5288c1;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 4px;
            }
            QComboBox {
                background-color: #242F3D;
                border: 1px solid #2B394A;
                border-radius: 5px;
                padding: 3px 8px;
                color: #FFFFFF;
            }
            QComboBox:hover {
                border: 1px solid #45566b;
            }
            QComboBox QAbstractItemView {
                background-color: #242F3D;
                border: 1px solid #2B394A;
                selection-background-color: #2B7CB6;
                color: #FFFFFF;
            }
            QSpinBox {
                background-color: #242F3D;
                border: 1px solid #2B394A;
                border-radius: 5px;
                padding: 3px 6px;
                color: #FFFFFF;
            }
            QSpinBox:hover {
                border: 1px solid #45566b;
            }
            QCheckBox {
                spacing: 6px;
                color: #EFEFEF;
            }
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border-radius: 3px;
                border: 1px solid #45566b;
                background-color: #242F3D;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #5288c1;
            }
            QCheckBox::indicator:checked {
                background-color: #2B7CB6;
                border: 1px solid #2B7CB6;
            }
            QProgressBar {
                border: none;
                background-color: #182533;
                height: 8px;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4f9cd6;
                border-radius: 4px;
            }
        '''
        self.setStyleSheet(qss)

    @staticmethod
    def _add_shadow(widget, blur=10, offset=2, opacity=80):
        """为控件添加阴影效果。"""
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur)
        shadow.setOffset(offset, offset)
        shadow.setColor(QColor(0, 0, 0, opacity))
        widget.setGraphicsEffect(shadow)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # ---- 链接输入 ----
        grp_link = QGroupBox("下载链接")
        self._add_shadow(grp_link)
        layout.addWidget(grp_link)
        link_layout = QVBoxLayout(grp_link)

        hint = QLabel("💡 粘贴 Telegram 消息链接，每行一个")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        link_layout.addWidget(hint)

        input_row = QHBoxLayout()
        self._txt_links = QTextEdit()
        self._txt_links.setPlaceholderText("https://t.me/telegram/193")
        self._txt_links.setMaximumHeight(60)
        self._txt_links.setFont(QFont("Consolas", 10))
        self._txt_links.textChanged.connect(self._on_links_changed)
        input_row.addWidget(self._txt_links)

        btn_row = QVBoxLayout()
        self._btn_paste = QPushButton("📋 粘贴")
        self._add_shadow(self._btn_paste, blur=6, offset=1, opacity=60)
        self._btn_paste.clicked.connect(self._paste_links)
        self._btn_clear = QPushButton("🗑️ 清空")
        self._add_shadow(self._btn_clear, blur=6, offset=1, opacity=60)
        self._btn_clear.setMinimumWidth(80)
        self._btn_clear.setStyleSheet("""
            QPushButton { background-color: #242F3D; border: 1px solid #36485d; color: #a4b3c1; }
            QPushButton:hover { background-color: #2f3e52; border-color: #45566b; }
            QPushButton:pressed { background-color: #1b2430; }
        """)
        self._btn_clear.clicked.connect(self._txt_links.clear)
        btn_row.addWidget(self._btn_paste)
        btn_row.addWidget(self._btn_clear)
        input_row.addLayout(btn_row)
        link_layout.addLayout(input_row)

        self._lbl_recognition = QLabel("等待粘贴链接...")
        self._lbl_recognition.setStyleSheet("color: #555; font-size: 11px;")
        link_layout.addWidget(self._lbl_recognition)

        # ---- 下载设置 ----
        grp_settings = QGroupBox("下载设置")
        self._add_shadow(grp_settings)
        layout.addWidget(grp_settings)
        settings_layout = QHBoxLayout(grp_settings)

        # 内容类型
        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("内容类型:"))
        self._combo_content = QComboBox()
        self._combo_content.addItems(["全部媒体", "仅图片", "仅视频", "仅音频", "自定义"])
        self._combo_content.currentIndexChanged.connect(self._on_content_type_changed)
        left_col.addWidget(self._combo_content)

        self._txt_custom_ext = QLineEdit()
        self._txt_custom_ext.setPlaceholderText("jpg,png,mp4")
        self._txt_custom_ext.setVisible(False)
        left_col.addWidget(self._txt_custom_ext)

        settings_layout.addLayout(left_col)

        # 目录 + 选项
        mid_col = QVBoxLayout()
        mid_col.addWidget(QLabel("下载目录:"))
        dir_row = QHBoxLayout()
        self._txt_dir = QLineEdit()
        self._txt_dir.setPlaceholderText("D:/Downloads")
        dir_row.addWidget(self._txt_dir)
        self._btn_browse = QPushButton("📂 浏览")
        self._add_shadow(self._btn_browse, blur=6, offset=1, opacity=60)
        self._btn_browse.clicked.connect(self._browse_dir)
        dir_row.addWidget(self._btn_browse)
        mid_col.addLayout(dir_row)

        self._chk_comments = QCheckBox("下载评论区媒体")
        self._chk_comments.setToolTip("下载帖子后，自动导出并下载评论区中的媒体文件")
        mid_col.addWidget(self._chk_comments)

        self._chk_subfolder = QCheckBox("自动按帖子归档")
        self._chk_subfolder.setToolTip("按消息 ID 自动创建子文件夹，如 50063/")
        mid_col.addWidget(self._chk_subfolder)

        settings_layout.addLayout(mid_col)

        # 文件名模板
        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("文件名:"))
        self._combo_template = QComboBox()
        self._combo_template.addItems(["原始文件名", "tdl 默认"])
        self._combo_template.currentIndexChanged.connect(self._on_template_changed)
        right_col.addWidget(self._combo_template)

        # 线程/并发
        tc_row = QHBoxLayout()
        tc_row.addWidget(QLabel("线程:"))
        self._spin_threads = QSpinBox()
        self._spin_threads.setRange(1, 32)
        tc_row.addWidget(self._spin_threads)
        tc_row.addWidget(QLabel("并发:"))
        self._spin_limit = QSpinBox()
        self._spin_limit.setRange(1, 16)
        tc_row.addWidget(self._spin_limit)
        right_col.addLayout(tc_row)

        settings_layout.addLayout(right_col)

        # ---- 高级设置（折叠式） ----
        grp_advanced = QGroupBox("高级设置")
        self._add_shadow(grp_advanced)
        grp_advanced.setCheckable(True)
        grp_advanced.setChecked(True)
        grp_advanced.toggled.connect(lambda c: self._update_geometry())
        layout.addWidget(grp_advanced)
        adv_layout = QVBoxLayout(grp_advanced)

        proxy_row = QHBoxLayout()
        self._chk_proxy = QCheckBox("启用代理")
        proxy_row.addWidget(self._chk_proxy)
        self._txt_proxy = QLineEdit()
        self._txt_proxy.setPlaceholderText("socks5://127.0.0.1:7897")
        proxy_row.addWidget(self._txt_proxy)
        self._chk_proxy.toggled.connect(self._txt_proxy.setEnabled)
        adv_layout.addLayout(proxy_row)

        opts_row1 = QHBoxLayout()
        self._chk_skip_same = QCheckBox("跳过同名文件")
        self._chk_resume = QCheckBox("断点续传")
        self._chk_takeout = QCheckBox("取下载(降低限流)")
        self._chk_takeout.setToolTip("使用 Takeout 会话下载，可降低 Telegram 限流惩罚，适合大批量下载")
        self._chk_group = QCheckBox("探测相册分组")
        opts_row1.addWidget(self._chk_skip_same)
        opts_row1.addWidget(self._chk_resume)
        opts_row1.addWidget(self._chk_takeout)
        opts_row1.addWidget(self._chk_group)
        adv_layout.addLayout(opts_row1)

        # ---- 操作区 ----
        actions_layout = QHBoxLayout()
        layout.addLayout(actions_layout)

        self._btn_start = QPushButton("开始下载")
        self._add_shadow(self._btn_start, blur=8, offset=2, opacity=70)
        self._btn_start.setMinimumHeight(36)
        self._btn_start.setStyleSheet("""
            QPushButton {
                background-color: #3498db; color: white;
                font-size: 14px; font-weight: bold;
                padding: 6px 24px; border: none; border-radius: 4px;
            }
            QPushButton:disabled { background-color: #95a5a6; }
            QPushButton:hover:!disabled { background-color: #2980b9; }
        """)
        self._btn_start.clicked.connect(self._start_download)
        actions_layout.addWidget(self._btn_start)

        self._btn_stop = QPushButton("停止")
        self._add_shadow(self._btn_stop, blur=8, offset=2, opacity=70)
        self._btn_stop.setMinimumHeight(36)
        self._btn_stop.setEnabled(False)
        self._btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; color: white;
                font-weight: bold; padding: 6px 16px;
                border: none; border-radius: 4px;
            }
            QPushButton:disabled { background-color: #bdc3c7; }
            QPushButton:hover:!disabled { background-color: #c0392b; }
        """)
        self._btn_stop.clicked.connect(self._stop_download)
        actions_layout.addWidget(self._btn_stop)

        self._btn_open_dir = QPushButton("打开目录")
        self._add_shadow(self._btn_open_dir, blur=6, offset=1, opacity=60)
        self._btn_open_dir.clicked.connect(self._open_dir)
        actions_layout.addWidget(self._btn_open_dir)

        actions_layout.addStretch()

        self._lbl_current = QLabel("当前: 等待")
        self._lbl_current.setMinimumWidth(220)
        self._lbl_current.setAlignment(Qt.AlignCenter)
        self._lbl_current.setStyleSheet("font-size: 12px;")
        actions_layout.addWidget(self._lbl_current)

        # ---- 进度条 ----
        progress_layout = QHBoxLayout()
        layout.addLayout(progress_layout)
        progress_layout.addWidget(QLabel("当前文件:"))
        self._bar_current = QProgressBar()
        self._bar_current.setMaximum(100)
        progress_layout.addWidget(self._bar_current)
        progress_layout.addWidget(QLabel("总任务:"))
        self._bar_total = QProgressBar()
        progress_layout.addWidget(self._bar_total)

        # ---- tdl 原始输出 ----
        grp_log = QGroupBox("tdl 输出")
        self._add_shadow(grp_log)
        layout.addWidget(grp_log, stretch=1)
        log_layout = QVBoxLayout(grp_log)

        self._txt_output = QTextEdit()
        self._txt_output.setReadOnly(True)
        self._txt_output.setFont(QFont("Consolas", 9))
        self._txt_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e23; color: #c8d2dc;
                border: 1px solid #333; padding: 4px;
            }
        """)
        log_layout.addWidget(self._txt_output)

        # ---- 状态栏 ----
        self._lbl_status = QLabel("就绪")
        self.statusBar().addPermanentWidget(self._lbl_status)

    # ---- 事件 ----

    def _on_links_changed(self):
        text = self._txt_links.toPlainText().strip()
        if not text:
            self._lbl_recognition.setText("等待粘贴链接...")
            return
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            parsed = parse_telegram_link(lines[0])
            if parsed.kind == "unknown":
                self._lbl_recognition.setText("⚠️ 无法识别的链接格式")
            else:
                extra = f" (+{len(lines)-1} 个链接)" if len(lines) > 1 else ""
                self._lbl_recognition.setText(parsed.display() + extra)
        else:
            self._lbl_recognition.setText("等待粘贴链接...")

    def _paste_links(self):
        from PySide6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        text = clipboard.text()
        if text:
            self._txt_links.append(text)

    def _on_content_type_changed(self, idx: int):
        self._txt_custom_ext.setVisible(idx == 4)

    def _on_template_changed(self, idx: int):
        pass

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择下载目录", self._txt_dir.text())
        if d:
            self._txt_dir.setText(d)

    def _update_geometry(self):
        self.adjustSize()

    def _open_dir(self):
        d = self._txt_dir.text().strip()
        if os.path.isdir(d):
            os.startfile(d)

    # ---- 配置 ----

    def _apply_config(self):
        c = self._config
        self._txt_dir.setText(c.download_dir)
        self._chk_proxy.setChecked(c.proxy_enabled)
        self._txt_proxy.setText(c.proxy)
        self._txt_proxy.setEnabled(c.proxy_enabled)
        self._spin_threads.setValue(c.threads)
        self._spin_limit.setValue(c.limit)

        content_map = {"all": 0, "images": 1, "videos": 2, "audio": 3, "custom": 4}
        self._combo_content.setCurrentIndex(content_map.get(c.content_type, 0))
        self._txt_custom_ext.setText(c.custom_extensions)

        self._combo_template.setCurrentIndex(0 if "filenamify .FileName" in c.filename_template else 1)
        self._chk_skip_same.setChecked(c.skip_same)
        self._chk_resume.setChecked(c.resume)
        self._chk_takeout.setChecked(c.takeout)
        self._chk_group.setChecked(c.group)
        self._chk_comments.setChecked(getattr(c, "download_comments", False))
        self._chk_subfolder.setChecked(c.auto_subfolder)

    def _save_config(self):
        c = self._config
        c.download_dir = self._txt_dir.text().strip()
        c.proxy_enabled = self._chk_proxy.isChecked()
        c.proxy = self._txt_proxy.text().strip()
        c.threads = self._spin_threads.value()
        c.limit = self._spin_limit.value()

        idx = self._combo_content.currentIndex()
        content_map = {0: "all", 1: "images", 2: "videos", 3: "audio", 4: "custom"}
        c.content_type = content_map.get(idx, "all")
        c.custom_extensions = self._txt_custom_ext.text().strip()

        c.filename_template = (
            "{{ filenamify .FileName }}"
            if self._combo_template.currentIndex() == 0
            else "{{ .DialogID }}_{{ .MessageID }}_{{ filenamify .FileName }}"
        )
        c.skip_same = self._chk_skip_same.isChecked()
        c.resume = self._chk_resume.isChecked()
        c.takeout = self._chk_takeout.isChecked()
        c.group = self._chk_group.isChecked()
        c.download_comments = self._chk_comments.isChecked()
        c.auto_subfolder = self._chk_subfolder.isChecked()
        c.window_width = self.width()
        c.window_height = self.height()
        c.save()

    @staticmethod
    def _sanitize_folder_name(name: str) -> str:
        """去掉 Windows 文件名中的非法字符，并压缩多余空格。"""
        import re
        invalid = r'[\\/:*?"<>|]'
        cleaned = re.sub(invalid, " ", name)
        return re.sub(r'\s+', " ", cleaned).strip()

    def _resolve_channel_name(self, parsed) -> str:
        """根据 parsed link 返回频道显示名称，失败时回退到用户名。"""
        fallback = self._sanitize_folder_name(parsed.channel) if parsed.channel else f"c_{parsed.chat_id}"

        if not parsed.channel and not parsed.chat_id:
            return fallback

        identifier = parsed.channel or parsed.chat_id
        if identifier in self._chat_info_cache:
            return self._sanitize_folder_name(self._chat_info_cache[identifier])
        # 私有频道可能用 -100 前缀
        if parsed.chat_id and ("-100" + parsed.chat_id) in self._chat_info_cache:
            return self._sanitize_folder_name(self._chat_info_cache["-100" + parsed.chat_id])

        try:
            import subprocess, json as jsonlib
            proc = subprocess.Popen(
                [self._tdl_path, "chat", "ls", "-o", "json"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            stdout, _ = proc.communicate(timeout=15)
            chats = jsonlib.loads(stdout)
            for chat in chats:
                uname = chat.get("username", "") or ""
                cid = str(chat.get("id", ""))
                vname = self._sanitize_folder_name(chat.get("visible_name", ""))
                if uname and uname != "-":
                    self._chat_info_cache[uname] = vname
                if cid:
                    self._chat_info_cache[cid] = vname
                    # 也存 -100 前缀版本（如果是正数 ID）
                    if cid.lstrip("-").isdigit() and not cid.startswith("-100"):
                        self._chat_info_cache["-100" + cid] = vname

            if identifier in self._chat_info_cache:
                return self._sanitize_folder_name(self._chat_info_cache[identifier])
            if parsed.chat_id and ("-100" + parsed.chat_id) in self._chat_info_cache:
                return self._sanitize_folder_name(self._chat_info_cache["-100" + parsed.chat_id])
        except Exception:
            pass

        return fallback

    def closeEvent(self, event):
        if self._runner and self._runner.is_running:
            ret = QMessageBox.question(
                self, "TDLauncher",
                "当前有下载任务正在运行，关闭窗口会停止下载。确定关闭吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                event.ignore()
                return
            self._stop_download()
        self._save_config()
        super().closeEvent(event)

    # ---- 下载控制 ----

    def _start_download(self):
        text = self._txt_links.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "请先粘贴 Telegram 链接。")
            return

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return

        dir_path = self._txt_dir.text().strip()
        if not os.path.isdir(dir_path):
            QMessageBox.warning(self, "错误", f"目录不存在: {dir_path}")
            return

        if not self._tdl_path:
            QMessageBox.warning(self, "错误", "未找到 tdl.exe。")
            return

        self._save_config()

        # 构建所有任务命令
        self._task_commands = []
        self._task_labels = []

        for url in lines:
            parsed = parse_telegram_link(url)
            include_comments = self._chk_comments.isChecked()
            auto_sub = self._chk_subfolder.isChecked()

            # 如果启用归档，先用 chat ls 查显示名，再用显示名建子目录
            job_config = self._config
            if auto_sub and parsed.message_id:
                import copy
                job_config = copy.copy(self._config)
                folder_name = self._resolve_channel_name(parsed)
                sub_dir = os.path.join(self._config.download_dir, folder_name, str(parsed.message_id))
                job_config.download_dir = sub_dir

            cmds = build_download_commands(url, parsed, job_config, include_comments)

            for cmd in cmds:
                label = cmd[0]
                if label == "dl" and "-f" in cmd:
                    self._task_labels.append("下载评论区媒体")
                elif label == "chat":
                    self._task_labels.append("导出评论区列表")
                else:
                    self._task_labels.append("下载帖子媒体")

            self._task_commands.extend(cmds)

        if not self._task_commands:
            return

        self._current_task_index = 0
        self._total_tasks = len(self._task_commands)
        self._completed_tasks = 0
        self._channel_display_name = ""
        self._progress_parser.reset()

        self._bar_total.setMaximum(self._total_tasks)
        self._bar_total.setValue(0)
        self._bar_current.setValue(0)

        self._update_ui_running(True)
        self._txt_output.clear()
        self._lbl_status.setText(f"任务: 0/{self._total_tasks}")
        self._lbl_current.setText("当前: 准备中...")

        self._launch_next_task()

    def _launch_next_task(self):
        if self._current_task_index >= self._total_tasks:
            return

        args = self._task_commands[self._current_task_index]
        label = self._task_labels[self._current_task_index] if self._current_task_index < len(self._task_labels) else ""
        args_display = " ".join(args[:4]) + ("..." if len(args) > 4 else "")
        self._log_output(f"\n▶ [{self._current_task_index + 1}/{self._total_tasks}] {label}")
        self._progress_parser.reset()
        self._bar_current.setValue(0)
        self._lbl_current.setText("当前: 准备中...")

        self._runner = TdlRunner(self._tdl_path)
        self._runner.on_stdout = self._on_tdl_output
        self._runner.on_stderr = self._on_tdl_output
        self._runner.on_exit = self._on_tdl_exit
        self._runner.start(args)

    def _on_tdl_output(self, text: str):
        self._log_output(text)
        self._progress_parser.feed(text)

        # 实时更新进度
        if self._progress_parser.percent is not None:
            pct = int(self._progress_parser.percent)
            self._bar_current.setValue(min(100, max(0, pct)))

        status = self._progress_parser.summary()
        self._lbl_current.setText(f"当前: {status}")

        # 从 tdl 输出中提取频道显示名称
        if not self._channel_display_name:
            import re
            m = re.match(r"^(.+?)\(\d+\):\d+", text.lstrip())
            if m:
                self._channel_display_name = m.group(1).strip()

    def _on_tdl_exit(self, code: int):
        current = self._current_task_index + 1

        if code == 0:
            self._log_output(f"  ✅ 下载完成")
            self._completed_tasks += 1
            self._bar_current.setValue(100)
        else:
            self._log_output(f"  ❌ 下载失败 (退出码: {code})")
            self._bar_current.setValue(0)

        self._bar_total.setValue(self._completed_tasks)
        self._lbl_status.setText(f"任务: {current}/{self._total_tasks}")
        self._runner = None

        # 下一个任务
        self._current_task_index += 1
        if self._current_task_index < self._total_tasks:
            self._launch_next_task()
        else:
            self._finish_download()

    def _finish_download(self):
        self._update_ui_running(False)
        self._bar_current.setValue(100 if self._completed_tasks > 0 else 0)
        self._bar_total.setValue(self._completed_tasks)
        self._lbl_status.setText(
            f"完成: {self._completed_tasks}/{self._total_tasks}"
        )
        self._log_output(
            f"\n━━━ 全部完成: 成功 {self._completed_tasks} 个任务 ━━━"
        )

    def _stop_download(self):
        if self._runner:
            self._runner.stop()
            self._runner = None
        self._update_ui_running(False)
        self._bar_current.setValue(0)
        self._lbl_current.setText("当前: 已停止")
        self._lbl_status.setText("已停止")
        self._log_output("\n⏹ 下载已停止")

    def _update_ui_running(self, running: bool):
        self._btn_start.setEnabled(not running)
        self._btn_stop.setEnabled(running)
        self._txt_links.setReadOnly(running)
        self._combo_content.setEnabled(not running)
        self._combo_template.setEnabled(not running)
        self._spin_threads.setEnabled(not running)
        self._spin_limit.setEnabled(not running)
        self._chk_proxy.setEnabled(not running)
        self._txt_proxy.setEnabled(not running and self._chk_proxy.isChecked())

    def _log_output(self, text: str):
        self._txt_output.append(text)
        # 自动滚动到底部
        scrollbar = self._txt_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _check_login_status(self):
        """检查 tdl 登录状态。"""
        try:
            import subprocess
            proc = subprocess.Popen(
                [self._tdl_path, "chat", "ls"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            stdout, stderr = proc.communicate(timeout=10)
            if proc.returncode != 0:
                self._log_output("⚠️ 未登录或登录已过期，请运行 tdl login -T qr 重新登录")
            else:
                self._log_output("✅ 已登录，就绪")
        except Exception as e:
            self._log_output(f"⚠️ 登录检测失败: {e}")

    def _update_status_bar(self):
        if self._tdl_path:
            self.statusBar().showMessage(f"tdl: {self._tdl_path}")
