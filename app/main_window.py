import os
import re
import sys
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QFrame, QProgressBar,
    QFileDialog, QMessageBox,
    QGraphicsView, QGraphicsScene, QGraphicsDropShadowEffect,
    QScrollArea, QSizePolicy,
)

from config import Config
from link_parser import parse_telegram_link, ParsedLink
from command_builder import build_download_commands
from tdl_runner import TdlRunner
from progress_parser import ProgressParser


# 设计画布尺寸（16:9），窗口在此尺寸下为 1× 缩放
DESIGN_W, DESIGN_H = 1280, 720
ASPECT = DESIGN_W / DESIGN_H


def _find_tdl() -> Optional[str]:
    """查找 tdl.exe 路径。从源码运行时需自行安装 tdl（https://github.com/iyear/tdl）。"""
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
    for p in os.environ["PATH"].split(";"):
        full = os.path.join(p, "tdl.exe")
        if os.path.isfile(full):
            return full
    return None


# ---- 终端配色 ----
BG = "#0A0A0A"
PANEL = "#101210"
WELL = "#070907"
INK = "#B7F0B0"
DIM = "#57705A"
ACC = "#4ADE80"
ON = "#04170B"
LINE = "#1E2A1E"
WARN = "#E8A33D"

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

QSS = f"""
#Root {{ background: {BG}; }}
#Root * {{ color: {INK}; font-family: Consolas, "Cascadia Mono", "Microsoft YaHei UI", monospace; font-size: 15px; }}

#Hdr, #Panel {{ background: {PANEL}; border: 1px solid {LINE}; }}
#Brand {{ font-size: 16px; font-weight: bold; letter-spacing: 1px; }}
#Path {{ color: {DIM}; font-size: 12px; }}
#SecTitle {{ color: {DIM}; font-size: 12px; letter-spacing: 1px; }}
#SecCount {{ color: {ACC}; font-size: 12px; }}
#FieldLabel {{ color: {DIM}; font-size: 12px; }}
#Recog {{ color: {DIM}; font-size: 12px; }}
#BigTitle {{ font-size: 17px; font-weight: bold; }}
#BigUrl {{ color: {DIM}; font-size: 12px; }}
#BigPct {{ font-size: 42px; font-weight: bold; }}
#BigPctUnit {{ color: {DIM}; font-size: 15px; }}
#Meta {{ color: {DIM}; font-size: 12px; }}
#MetaVal {{ color: {INK}; font-size: 12px; }}
#Badge {{ color: {ACC}; border: 1px solid {ACC}; padding: 2px 9px; font-size: 12px; }}
#Stat {{ color: {DIM}; font-size: 12px; }}
#StatVal {{ color: {ACC}; font-size: 12px; }}
#LogTitle {{ color: {DIM}; font-size: 12px; letter-spacing: 1px; }}
#LogToggle {{ background: transparent; border: none; color: {DIM}; font-size: 12px; letter-spacing: 1px; padding: 0; text-align: left; }}
#LogToggle:hover {{ color: {ACC}; }}

QTextEdit, QLineEdit, QComboBox, QSpinBox {{
  background: {WELL}; border: 1px solid {LINE}; color: {INK};
  selection-background-color: {ACC}; selection-color: {ON};
}}
QTextEdit {{ padding: 6px 9px; }}
QLineEdit, QComboBox, QSpinBox {{ padding: 5px 9px; }}
QTextEdit:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {ACC}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
  background: {PANEL}; border: 1px solid {LINE}; color: {INK};
  selection-background-color: {ACC}; selection-color: {ON}; outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; height: 0; border: none; }}

QPushButton {{
  background: {PANEL}; color: {INK}; border: 1px solid {LINE}; padding: 9px 16px;
}}
QPushButton:hover {{ border-color: {ACC}; }}
QPushButton:pressed {{ color: {ACC}; }}
QPushButton:disabled {{ color: #33422f; border-color: #16201a; }}
QPushButton#Primary {{ background: {ACC}; color: {ON}; border-color: {ACC}; font-weight: bold; }}
QPushButton#Primary:hover {{ background: #5fe090; }}
QPushButton#Primary:disabled {{ background: #1a2a1e; color: #33422f; border-color: #1a2a1e; }}
QPushButton#Stop {{ color: {WARN}; border-color: {WARN}; font-weight: bold; background: #241a0d; }}
QPushButton#Stop:hover {{ background: {WARN}; color: {ON}; }}
QPushButton#Stop:disabled {{ color: #52432a; border-color: #33291a; background: #16110a; }}
QPushButton#Toggle {{ padding: 4px 9px; color: {DIM}; border-color: {LINE}; font-size: 12px; }}
QPushButton#Toggle:checked {{ color: {ACC}; border-color: {ACC}; }}

QProgressBar {{ background: {WELL}; border: none; }}
QProgressBar::chunk {{ background: {ACC}; }}

#QRow {{ background: transparent; border: none; border-left: 2px solid transparent; }}
#QRow[active="true"] {{ background: #16301f; border-left: 2px solid {ACC}; }}
#QMarker {{ color: {DIM}; }}
#QRow[active="true"] #QMarker {{ color: {ACC}; }}
#QName {{ color: {INK}; font-size: 13px; }}
#QRow[active="true"] #QName {{ color: {ACC}; }}
#QPct {{ color: {DIM}; font-size: 12px; }}
#FName {{ color: {INK}; font-size: 13px; }}
#FInfo {{ color: {DIM}; font-size: 12px; }}

#Scroll {{ background: transparent; border: none; }}
#Scroll > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: {WELL}; width: 9px; border: none; }}
QScrollBar::handle:vertical {{ background: {LINE}; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QLabel {{ background: transparent; }}
"""


class TipLabel(QLabel):
    """带阴影的悬浮提示，配色与终端主题一致。"""

    def __init__(self):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setObjectName("Tip")
        self.setStyleSheet(
            f"#Tip {{ background:{PANEL}; color:{INK}; border:1px solid {ACC}; "
            f"padding:7px 11px; font-family:Consolas,'Microsoft YaHei UI',monospace; font-size:13px; }}"
        )
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(20)
        sh.setOffset(0, 5)
        sh.setColor(QColor(0, 0, 0, 190))
        self.setGraphicsEffect(sh)


class CellsBar(QWidget):
    """把进度画成 24 格可见的量。"""

    def __init__(self, count: int = 24, parent=None):
        super().__init__(parent)
        self._count = count
        self._value = 0
        self._on = 0
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)
        self._cells = []
        off = f"background:{WELL}; border:1px solid {LINE};"
        for _ in range(count):
            c = QFrame()
            c.setFixedHeight(14)
            c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            c.setStyleSheet(off)
            lay.addWidget(c)
            self._cells.append(c)

    def setValue(self, v: int) -> None:
        v = max(0, min(100, int(v)))
        if v == self._value:
            return
        self._value = v
        on = round(v / 100 * self._count)
        if on == self._on:
            return
        lo, hi = sorted((self._on, on))
        self._on = on
        on_css = f"background:{ACC}; border:1px solid {ACC};"
        off_css = f"background:{WELL}; border:1px solid {LINE};"
        for i in range(lo, hi):
            self._cells[i].setStyleSheet(on_css if i < on else off_css)

    def value(self) -> int:
        return self._value


class QueueRow(QFrame):
    """队列里的一行：标记 + 名称 + 百分比 + 迷你进度条。"""

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("QRow")
        self.setProperty("active", "false")
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 6, 8, 7)
        v.setSpacing(5)
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.marker = QLabel("◦")
        self.marker.setObjectName("QMarker")
        self.marker.setFixedWidth(12)
        self.name = QLabel(name)
        self.name.setObjectName("QName")
        self.pct = QLabel("")
        self.pct.setObjectName("QPct")
        h.addWidget(self.marker)
        h.addWidget(self.name, 1)
        h.addWidget(self.pct)
        v.addLayout(h)
        self.bar = QProgressBar()
        self.bar.setFixedHeight(4)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        v.addWidget(self.bar)

    def set_active(self, on: bool) -> None:
        self.setProperty("active", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if on:
            self.marker.setText("▸")
        elif self.marker.text() != "✓":
            self.marker.setText("◦")

    def set_done(self) -> None:
        self.marker.setText("✓")

    def set_pct(self, v: int) -> None:
        self.bar.setValue(v)
        self.pct.setText(f"{v}%")


class FileRow(QFrame):
    """进度区里的一行文件：名称 + 进度条 + 状态。"""

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        g = QGridLayout(self)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(0)
        self.name = QLabel(name)
        self.name.setObjectName("FName")
        self.bar = QProgressBar()
        self.bar.setFixedHeight(8)
        self.bar.setFixedWidth(150)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.info = QLabel("")
        self.info.setObjectName("FInfo")
        self.info.setFixedWidth(60)
        g.addWidget(self.name, 0, 0)
        g.setColumnStretch(0, 1)
        g.addWidget(self.bar, 0, 1)
        g.addWidget(self.info, 0, 2)

    def set_pct(self, v: int) -> None:
        self.bar.setValue(v)
        self.info.setText(f"{v}%" if v < 100 else "完成")

    def set_size(self, txt: str) -> None:
        if self.info.text() == "":
            self.info.setText(txt)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TDLauncher")
        self._in_resize = False

        self._config = Config.load()
        self._tdl_path = _find_tdl()
        self._runner: Optional[TdlRunner] = None
        self._progress_parser = ProgressParser()

        self._current_task_index = 0
        self._task_commands: list = []
        self._task_labels: list = []
        self._task_link: list = []          # 每个命令对应的链接序号
        self._link_names: list = []         # 每个链接的显示名
        self._link_total: list = []         # 每个链接的命令总数
        self._link_done: list = []          # 每个链接已完成命令数
        self._queue_rows: list = []
        self._file_rows: dict = {}
        self._total_tasks = 0
        self._completed_tasks = 0
        self._channel_display_name: str = ""
        self._chat_info_cache: dict = {}
        self._tip = TipLabel()
        self._tip_texts: dict = {}

        # 固定画布 + 等比缩放
        self._design = QWidget()
        self._design.setObjectName("Root")
        self._build_ui()
        self._design.setFixedSize(DESIGN_W, DESIGN_H)

        self._scene = QGraphicsScene()
        self._scene.setSceneRect(0, 0, DESIGN_W, DESIGN_H)
        self._scene.setBackgroundBrush(QColor("#050505"))
        self._proxy = self._scene.addWidget(self._design)

        self._view = QGraphicsView(self._scene)
        self._view.setFrameShape(QFrame.NoFrame)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setAlignment(Qt.AlignCenter)
        self._view.setStyleSheet("background:#050505; border:none;")
        self.setCentralWidget(self._view)

        self._apply_theme()

        self.setMinimumSize(DESIGN_W, DESIGN_H)
        w = self._config.window_width or DESIGN_W
        w = max(DESIGN_W, int(w))
        self.resize(w, round(w / ASPECT))

        self._apply_config()
        self._update_status_bar()

        if not self._tdl_path:
            QMessageBox.warning(self, "TDLauncher", "未找到 tdl.exe，请确认安装路径。")
        else:
            self._check_login_status()

        QTimer.singleShot(0, self._fit)

    # ---- 窗口等比缩放 ----

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._in_resize and not (self.isMaximized() or self.isFullScreen()):
            self._in_resize = True
            w = self.width()
            h = round(w / ASPECT)
            if abs(h - self.height()) > 1:
                self.resize(w, h)
            self._in_resize = False
        self._fit()

    def _fit(self):
        if hasattr(self, "_view"):
            self._view.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    # ---- 主题 ----

    def _apply_theme(self):
        self._design.setStyleSheet(QSS)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(
                f"QToolTip {{ background:{PANEL}; color:{INK}; border:1px solid {ACC}; "
                f"padding:6px 9px; font-family:Consolas,'Microsoft YaHei UI',monospace; font-size:13px; }}"
            )

    # ---- 悬浮提示（带阴影）----

    def eventFilter(self, obj, event):
        if obj in self._tip_texts:
            if event.type() == QEvent.Enter:
                self._show_tip(obj, self._tip_texts[obj])
            elif event.type() in (QEvent.Leave, QEvent.MouseButtonPress):
                self._tip.hide()
        return super().eventFilter(obj, event)

    def _show_tip(self, w, text):
        self._tip.setText(text)
        self._tip.adjustSize()
        gp = w.mapToGlobal(w.rect().bottomLeft())
        self._tip.move(gp.x(), gp.y() + 6)
        self._tip.show()

    # ---- 小工具 ----

    @staticmethod
    def _field(label: str, ctrl: QWidget) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        lb = QLabel(label)
        lb.setObjectName("FieldLabel")
        v.addWidget(lb)
        v.addWidget(ctrl)
        return w

    def _toggle(self, text: str, checked: bool = False, tip: str = "") -> QPushButton:
        b = QPushButton()
        b.setObjectName("Toggle")
        b.setCheckable(True)
        b.setChecked(checked)
        if tip:
            self._tip_texts[b] = tip
            b.installEventFilter(self)

        def sync():
            b.setText(("[×] " if b.isChecked() else "[ ] ") + text)

        b.toggled.connect(sync)
        sync()
        return b

    def _scroll(self) -> tuple[QScrollArea, QVBoxLayout]:
        sa = QScrollArea()
        sa.setObjectName("Scroll")
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        box = QVBoxLayout(inner)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)
        box.addStretch(1)
        sa.setWidget(inner)
        return sa, box

    @staticmethod
    def _insert(box: QVBoxLayout, w: QWidget) -> None:
        box.insertWidget(box.count() - 1, w)

    # ---- UI 构建 ----

    def _build_ui(self):
        root = QVBoxLayout(self._design)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(9)

        # ---- 顶栏 ----
        hdr = QFrame()
        hdr.setObjectName("Hdr")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 8, 12, 8)
        self._lbl_brand = QLabel('▚ TDLauncher<span style="color:%s">_</span>' % ACC)
        self._lbl_brand.setObjectName("Brand")
        hl.addWidget(self._lbl_brand)
        hl.addStretch(1)
        self._lbl_path = QLabel("tdl")
        self._lbl_path.setObjectName("Path")
        hl.addWidget(self._lbl_path)
        root.addWidget(hdr)

        body = QHBoxLayout()
        body.setSpacing(9)
        root.addLayout(body, 1)

        # 左：下载链接
        links = QFrame()
        links.setObjectName("Panel")
        ll = QVBoxLayout(links)
        ll.setContentsMargins(12, 10, 12, 10)
        ll.setSpacing(8)
        t = QLabel("下载链接 · 每行一个任务")
        t.setObjectName("SecTitle")
        ll.addWidget(t)
        self._txt_links = QTextEdit()
        self._txt_links.setPlaceholderText("https://t.me/telegram/193")
        self._txt_links.setFont(QFont("Consolas", 10))
        self._txt_links.textChanged.connect(self._on_links_changed)
        ll.addWidget(self._txt_links, 1)
        lfoot = QHBoxLayout()
        lfoot.setSpacing(10)
        self._lbl_recognition = QLabel("等待粘贴链接...")
        self._lbl_recognition.setObjectName("Recog")
        lfoot.addWidget(self._lbl_recognition, 1)
        self._btn_clear = QPushButton("清空")
        self._btn_clear.clicked.connect(self._txt_links.clear)
        lfoot.addWidget(self._btn_clear, 0, Qt.AlignBottom)
        ll.addLayout(lfoot)
        body.addWidget(links, 1)

        right = QVBoxLayout()
        right.setSpacing(9)
        body.addLayout(right, 3)

        # 参数
        params = QFrame()
        params.setObjectName("Panel")
        pl = QVBoxLayout(params)
        pl.setContentsMargins(12, 10, 12, 10)
        pl.setSpacing(9)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        for i, s in enumerate([14, 10, 11, 7, 7]):
            grid.setColumnStretch(i, s)

        self._combo_content = QComboBox()
        self._combo_content.addItems(["全部媒体", "仅图片", "仅视频", "仅音频", "自定义"])
        self._combo_content.currentIndexChanged.connect(self._on_content_type_changed)
        grid.addWidget(self._field("内容类型", self._combo_content), 0, 0)
        self._txt_custom_ext = QLineEdit()
        self._txt_custom_ext.setPlaceholderText("jpg,png,mp4")
        grid.addWidget(self._field("自定义扩展名", self._txt_custom_ext), 0, 1)
        self._combo_template = QComboBox()
        self._combo_template.addItems(["原始文件名", "tdl 默认"])
        self._combo_template.currentIndexChanged.connect(self._on_template_changed)
        grid.addWidget(self._field("文件名", self._combo_template), 0, 2)
        self._spin_threads = QSpinBox()
        self._spin_threads.setRange(1, 32)
        grid.addWidget(self._field("线程", self._spin_threads), 0, 3)
        self._spin_limit = QSpinBox()
        self._spin_limit.setRange(1, 16)
        grid.addWidget(self._field("并发", self._spin_limit), 0, 4)

        dirw = QWidget()
        dh = QHBoxLayout(dirw)
        dh.setContentsMargins(0, 0, 0, 0)
        dh.setSpacing(7)
        self._txt_dir = QLineEdit()
        self._txt_dir.setPlaceholderText("D:/Downloads")
        dh.addWidget(self._txt_dir, 1)
        self._btn_browse = QPushButton("浏览")
        self._btn_browse.clicked.connect(self._browse_dir)
        dh.addWidget(self._btn_browse, 0)
        grid.addWidget(self._field("下载目录", dirw), 1, 0, 1, 3)

        self._txt_proxy = QLineEdit()
        self._txt_proxy.setPlaceholderText("socks5://127.0.0.1:7897")
        grid.addWidget(self._field("代理地址", self._txt_proxy), 1, 3, 1, 2)
        pl.addLayout(grid)

        toggles = QHBoxLayout()
        toggles.setSpacing(6)
        self._chk_comments = self._toggle("评论区", tip="下载帖子后，自动导出并下载评论区中的媒体文件")
        self._chk_subfolder = self._toggle("自动归档", tip="按频道显示名 + 消息 ID 自动归档")
        self._chk_skip_same = self._toggle("跳过同名")
        self._chk_resume = self._toggle("断点续传")
        self._chk_takeout = self._toggle("Takeout", tip="使用 Takeout 会话下载，可降低限流惩罚")
        self._chk_group = self._toggle("探测分组")
        self._chk_proxy = self._toggle("代理")
        for w in (self._chk_comments, self._chk_subfolder, self._chk_skip_same,
                  self._chk_resume, self._chk_takeout, self._chk_group, self._chk_proxy):
            toggles.addWidget(w)
        toggles.addStretch(1)
        pl.addLayout(toggles)
        right.addWidget(params)

        # 中段
        work = QHBoxLayout()
        work.setSpacing(9)
        right.addLayout(work, 1)

        # 队列
        queue = QFrame()
        queue.setObjectName("Panel")
        ql = QVBoxLayout(queue)
        ql.setContentsMargins(12, 10, 12, 10)
        ql.setSpacing(6)
        qhead = QHBoxLayout()
        qh = QLabel("队列")
        qh.setObjectName("SecTitle")
        qhead.addWidget(qh)
        qhead.addStretch(1)
        self._lbl_qcount = QLabel("0/0 活动")
        self._lbl_qcount.setObjectName("SecCount")
        qhead.addWidget(self._lbl_qcount)
        ql.addLayout(qhead)
        self._queue_scroll, self._queue_box = self._scroll()
        ql.addWidget(self._queue_scroll, 1)
        work.addWidget(queue, 2)

        # 进度
        prog = QFrame()
        prog.setObjectName("Panel")
        prl = QVBoxLayout(prog)
        prl.setContentsMargins(12, 10, 12, 10)
        prl.setSpacing(9)

        dhead = QHBoxLayout()
        dhead.setSpacing(10)
        self._lbl_current = QLabel("等待任务")
        self._lbl_current.setObjectName("BigTitle")
        dhead.addWidget(self._lbl_current)
        self._lbl_url = QLabel("")
        self._lbl_url.setObjectName("BigUrl")
        self._lbl_url.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        dhead.addWidget(self._lbl_url, 1)
        self._lbl_badge = QLabel("就绪")
        self._lbl_badge.setObjectName("Badge")
        dhead.addWidget(self._lbl_badge, 0)
        prl.addLayout(dhead)

        amount = QHBoxLayout()
        amount.setSpacing(18)
        big = QHBoxLayout()
        big.setSpacing(2)
        self._lbl_bigpct = QLabel("0")
        self._lbl_bigpct.setObjectName("BigPct")
        big.addWidget(self._lbl_bigpct, 0, Qt.AlignBottom)
        u = QLabel("%")
        u.setObjectName("BigPctUnit")
        big.addWidget(u, 0, Qt.AlignBottom)
        amount.addLayout(big, 0)
        ar = QVBoxLayout()
        ar.setSpacing(8)
        self._cells = CellsBar(24)
        ar.addWidget(self._cells)
        meta = QHBoxLayout()
        meta.setSpacing(20)
        self._lbl_speed = QLabel("—")
        self._lbl_speed.setObjectName("MetaVal")
        meta.addWidget(self._mkmeta("速度", self._lbl_speed))
        self._lbl_eta = QLabel("—")
        self._lbl_eta.setObjectName("MetaVal")
        meta.addWidget(self._mkmeta("剩余", self._lbl_eta))
        self._lbl_totalcount = QLabel("0/0")
        self._lbl_totalcount.setObjectName("MetaVal")
        meta.addWidget(self._mkmeta("文件", self._lbl_totalcount))
        meta.addStretch(1)
        ar.addLayout(meta)
        amount.addLayout(ar, 1)
        prl.addLayout(amount)

        # 逐文件列表
        self._files_scroll, self._files_box = self._scroll()
        prl.addWidget(self._files_scroll, 1)

        # 底部：tdl 输出 + 按钮（同一行）
        pfoot = QHBoxLayout()
        pfoot.setSpacing(14)
        logcol = QVBoxLayout()
        logcol.setSpacing(6)
        self._btn_log = QPushButton("tdl 输出 ▾")
        self._btn_log.setObjectName("LogToggle")
        self._btn_log.setCheckable(True)
        self._btn_log.setChecked(True)
        self._btn_log.toggled.connect(self._toggle_log)
        logcol.addWidget(self._btn_log, 0, Qt.AlignLeft)
        self._txt_output = QTextEdit()
        self._txt_output.setReadOnly(True)
        self._txt_output.setFont(QFont("Consolas", 9))
        self._txt_output.setFixedHeight(82)
        logcol.addWidget(self._txt_output)
        pfoot.addLayout(logcol, 1)

        self._lbl_status = QLabel("就绪")
        self._lbl_status.setObjectName("StatVal")

        rightbtns = QVBoxLayout()
        rightbtns.setSpacing(8)
        self._btn_open_dir = QPushButton("打开目录")
        self._btn_open_dir.clicked.connect(self._open_dir)
        rightbtns.addWidget(self._btn_open_dir, 0, Qt.AlignRight)
        botrow = QHBoxLayout()
        botrow.setSpacing(8)
        self._btn_stop = QPushButton("停止")
        self._btn_stop.setObjectName("Stop")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop_download)
        botrow.addWidget(self._btn_stop)
        self._btn_start = QPushButton("开始下载")
        self._btn_start.setObjectName("Primary")
        self._btn_start.clicked.connect(self._start_download)
        botrow.addWidget(self._btn_start)
        rightbtns.addLayout(botrow)
        pfoot.addLayout(rightbtns, 0)
        prl.addLayout(pfoot)

        work.addWidget(prog, 5)

        # ---- 状态栏 ----
        sb = QFrame()
        sb.setObjectName("Hdr")
        sbl = QHBoxLayout(sb)
        sbl.setContentsMargins(12, 6, 12, 6)
        self._lbl_tdlpath = QLabel("tdl: —")
        self._lbl_tdlpath.setObjectName("Stat")
        sbl.addWidget(self._lbl_tdlpath)
        sbl.addStretch(1)
        sbl.addWidget(self._lbl_status)
        sbl.addSpacing(24)
        self._lbl_sstate = QLabel("状态: 就绪")
        self._lbl_sstate.setObjectName("Stat")
        sbl.addWidget(self._lbl_sstate)
        root.addWidget(sb)

        # 隐藏的聚合进度条（供既有逻辑使用）
        self._bar_current = QProgressBar()
        self._bar_current.setMaximum(100)
        self._bar_total = QProgressBar()
        self._bar_current.valueChanged.connect(self._sync_progress)
        self._bar_total.valueChanged.connect(self._sync_progress)

    def _mkmeta(self, label, val_widget):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        l = QLabel(label)
        l.setObjectName("Meta")
        h.addWidget(l)
        h.addWidget(val_widget)
        return w

    def _toggle_log(self, on: bool):
        self._txt_output.setVisible(on)
        self._btn_log.setText("tdl 输出 ▾" if on else "tdl 输出 ▸")

    def _sync_progress(self):
        v = self._bar_current.value()
        self._lbl_bigpct.setText(str(v))
        self._cells.setValue(v)
        self._sync_filecount()

    def _sync_filecount(self):
        total = len(self._file_rows)
        done = sum(1 for r in self._file_rows.values() if r.bar.value() >= 100)
        self._lbl_totalcount.setText(f"{done}/{total}")

    # ---- 事件 ----

    def _on_links_changed(self):
        text = self._txt_links.toPlainText().strip()
        if not text:
            self._lbl_recognition.setText("等待粘贴链接...")
            return
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            self._lbl_recognition.setText("等待粘贴链接...")
            return
        parsed = parse_telegram_link(lines[0])
        n = len(lines)
        if parsed.kind == "unknown":
            self._lbl_recognition.setText("无法识别的链接格式")
            return
        who = f"@{parsed.channel}" if parsed.channel else "私有频道"
        extra = f"  +{n-1}" if n > 1 else ""
        self._lbl_recognition.setText(f"识别 {n} 个链接 · {who} #{parsed.message_id}{extra}")

    def _paste_links(self):
        from PySide6.QtGui import QGuiApplication
        text = QGuiApplication.clipboard().text()
        if text:
            self._txt_links.append(text)

    def _on_content_type_changed(self, idx: int):
        pass

    def _on_template_changed(self, idx: int):
        pass

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择下载目录", self._txt_dir.text())
        if d:
            self._txt_dir.setText(d)

    def _update_geometry(self):
        self._fit()

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
        import re as _re
        cleaned = _re.sub(r'[\\/:*?"<>|]', " ", name)
        return _re.sub(r'\s+', " ", cleaned).strip()

    def _resolve_channel_name(self, parsed) -> str:
        fallback = self._sanitize_folder_name(parsed.channel) if parsed.channel else f"c_{parsed.chat_id}"
        if not parsed.channel and not parsed.chat_id:
            return fallback
        identifier = parsed.channel or parsed.chat_id
        if identifier in self._chat_info_cache:
            return self._sanitize_folder_name(self._chat_info_cache[identifier])
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

    # ---- 队列 / 文件列表 ----

    def _clear_layout(self, box, store):
        for w in list(store):
            w.setParent(None)
        store.clear()

    def _add_queue_row(self, name: str) -> QueueRow:
        row = QueueRow(name)
        self._insert(self._queue_box, row)
        self._queue_rows.append(row)
        return row

    def _add_file_row(self, name: str) -> FileRow:
        row = FileRow(name)
        self._insert(self._files_box, row)
        self._file_rows[name] = row
        return row

    def _set_queue_active(self, idx: int):
        for i, r in enumerate(self._queue_rows):
            r.set_active(i == idx)

    def _feed_files(self, text: str):
        s = ANSI.sub("", text).strip()
        m = re.match(r"^(?P<name>.+?)\s+(?P<pct>\d+(?:\.\d+)?)%\s*\[", s)
        if not m:
            return
        name = m.group("name").strip().split(" -> ")[0].strip()
        if len(name) > 46:
            name = name[:44] + "…"
        pct = int(float(m.group("pct")))
        key = name
        row = self._file_rows.get(key)
        if row is None:
            if len(self._file_rows) >= 80:
                return
            row = self._add_file_row(key)
        row.set_pct(pct)
        self._sync_filecount()

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

        self._task_commands = []
        self._task_labels = []
        self._task_link = []
        self._link_names = []
        self._link_total = []
        self._link_done = []
        self._clear_layout(self._queue_box, self._queue_rows)
        self._clear_layout(self._files_box, self._file_rows)

        for li, url in enumerate(lines):
            parsed = parse_telegram_link(url)
            include_comments = self._chk_comments.isChecked()
            auto_sub = self._chk_subfolder.isChecked()

            if parsed.channel:
                disp = f"#{parsed.message_id} @{parsed.channel}" if parsed.message_id else f"@{parsed.channel}"
            else:
                disp = f"#{parsed.message_id}" if parsed.message_id else url
            self._link_names.append(disp)
            row = self._add_queue_row(disp)
            row.pct.setText("排队")

            job_config = self._config
            if auto_sub and parsed.message_id:
                import copy
                job_config = copy.copy(self._config)
                folder_name = self._resolve_channel_name(parsed)
                sub_dir = os.path.join(self._config.download_dir, folder_name, str(parsed.message_id))
                job_config.download_dir = sub_dir

            cmds = build_download_commands(url, parsed, job_config, include_comments)
            self._link_total.append(len(cmds))
            self._link_done.append(0)
            for cmd in cmds:
                label = cmd[0]
                if label == "dl" and "-f" in cmd:
                    self._task_labels.append("下载评论区媒体")
                elif label == "chat":
                    self._task_labels.append("导出评论区列表")
                else:
                    self._task_labels.append("下载帖子媒体")
                self._task_link.append(li)
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
        self._lbl_qcount.setText(f"0/{len(self._link_names)} 活动")
        self._lbl_sstate.setText("状态: 下载中")
        self._lbl_badge.setText("下载中")
        self._lbl_current.setText(self._link_names[0] if self._link_names else "准备中...")
        self._lbl_url.setText(lines[0] if lines else "")

        self._launch_next_task()

    def _launch_next_task(self):
        if self._current_task_index >= self._total_tasks:
            return
        args = self._task_commands[self._current_task_index]
        label = self._task_labels[self._current_task_index] if self._current_task_index < len(self._task_labels) else ""
        self._log_output(f"\n▶ [{self._current_task_index + 1}/{self._total_tasks}] {label}")
        self._progress_parser.reset()
        self._bar_current.setValue(0)

        if self._current_task_index < len(self._task_link):
            li = self._task_link[self._current_task_index]
            self._set_queue_active(li)
            if li < len(self._link_names) and self._channel_display_name == "":
                self._lbl_current.setText(self._link_names[li])

        self._runner = TdlRunner(self._tdl_path)
        self._runner.on_stdout = self._on_tdl_output
        self._runner.on_stderr = self._on_tdl_output
        self._runner.on_exit = self._on_tdl_exit
        self._runner.start(args)

    def _on_tdl_output(self, text: str):
        # tdl 用 \r 原地刷新进度，按 \r 拆帧后逐个分流
        for frame in text.split("\r"):
            frame = frame.strip()
            if frame:
                self._process_frame(frame)

    @staticmethod
    def _is_progress(s: str) -> bool:
        return bool(re.search(r"\d+(?:\.\d+)?%\s*\[", s) or re.match(r"^\[[\s.#]+\]", s))

    def _process_frame(self, clean: str):
        clean = ANSI.sub("", clean).strip()
        if not clean:
            return
        low = clean.lower()
        # 1) 逐文件进度帧 → 只更新 UI，不写日志
        if self._is_progress(clean):
            self._progress_parser.feed(clean)
            self._feed_files(clean)
            if self._progress_parser.percent is not None:
                pct = int(self._progress_parser.percent)
                self._bar_current.setValue(min(100, max(0, pct)))
            self._lbl_speed.setText(self._progress_parser.speed or "—")
            m = re.search(r"ETA[:：]?\s*([0-9][0-9hmsHMS.]*)", clean)
            if m:
                self._lbl_eta.setText(m.group(1))
            if not self._channel_display_name:
                mm = re.match(r"^(.+?)\(\d+\):\d+", clean.lstrip())
                if mm:
                    self._channel_display_name = mm.group(1).strip()
                    self._lbl_current.setText(self._channel_display_name)
            return
        # 2) CPU 资源状态 → 丢弃（噪音）
        if clean.lstrip().startswith("CPU:"):
            return
        # 3) 其余是真正的消息（错误/状态/摘要）→ 写日志
        self._log_output(clean)
        if any(k in low for k in ("error", "flood", "failed", "panic")) or "失败" in clean:
            if not self._btn_log.isChecked():
                self._btn_log.setChecked(True)

    def _on_tdl_exit(self, code: int):
        current = self._current_task_index + 1
        li = self._task_link[self._current_task_index] if self._current_task_index < len(self._task_link) else 0

        if code == 0:
            self._log_output("  ✓ 下载完成")
            self._completed_tasks += 1
            self._bar_current.setValue(100)
            if li < len(self._link_done):
                self._link_done[li] += 1
                done = self._link_done[li]
                tot = self._link_total[li] if li < len(self._link_total) else 1
                pct = int(round(done / tot * 100)) if tot else 100
                if li < len(self._queue_rows):
                    self._queue_rows[li].set_pct(pct)
                    if pct >= 100:
                        self._queue_rows[li].set_done()
        else:
            self._log_output(f"  ✗ 下载失败 (退出码: {code})")
            self._bar_current.setValue(0)

        self._bar_total.setValue(self._completed_tasks)
        active = sum(1 for i, d in enumerate(self._link_done) if 0 < d < self._link_total[i]) if self._link_done else 0
        self._lbl_qcount.setText(f"{active}/{len(self._link_names)} 活动")
        self._lbl_status.setText(f"任务: {current}/{self._total_tasks}")
        self._runner = None

        self._current_task_index += 1
        if self._current_task_index < self._total_tasks:
            self._launch_next_task()
        else:
            self._finish_download()

    def _finish_download(self):
        self._update_ui_running(False)
        self._bar_current.setValue(100 if self._completed_tasks > 0 else 0)
        self._bar_total.setValue(self._completed_tasks)
        self._lbl_status.setText(f"完成: {self._completed_tasks}/{self._total_tasks}")
        self._lbl_sstate.setText("状态: 完成")
        self._lbl_badge.setText("已完成")
        for r in self._queue_rows:
            if r.bar.value() >= 100:
                r.set_done()
        self._log_output(f"\n━━ 全部完成: 成功 {self._completed_tasks} 个任务 ━━")

    def _stop_download(self):
        if self._runner:
            self._runner.stop()
            self._runner = None
        self._update_ui_running(False)
        self._bar_current.setValue(0)
        self._lbl_current.setText("已停止")
        self._lbl_status.setText("已停止")
        self._lbl_sstate.setText("状态: 已停止")
        self._lbl_badge.setText("已停止")
        self._log_output("\n■ 下载已停止")

    def _update_ui_running(self, running: bool):
        self._btn_start.setText("下载中…" if running else "开始下载")
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
        sb = self._txt_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _check_login_status(self):
        try:
            import subprocess
            proc = subprocess.Popen(
                [self._tdl_path, "chat", "ls"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            proc.communicate(timeout=20)
            if proc.returncode != 0:
                self._log_output("⚠ 未登录或登录已过期，请运行 tdl login -T qr 重新登录")
            else:
                self._log_output("✓ 已登录，就绪")
        except Exception as e:
            self._log_output(f"⚠ 登录检测失败: {e}")

    def _update_status_bar(self):
        if self._tdl_path:
            self._lbl_tdlpath.setText(f"tdl: {self._tdl_path}")
            QTimer.singleShot(60, self._load_tdl_version)
        else:
            self._lbl_tdlpath.setText("tdl: 未找到")

    def _load_tdl_version(self):
        if not self._tdl_path:
            return
        try:
            import subprocess
            out = subprocess.run(
                [self._tdl_path, "version"], capture_output=True, text=True, timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).stdout
            m = re.search(r"Version:\s*([\w.]+)", out)
            ver = f" v{m.group(1)}" if m else ""
            self._lbl_path.setText(f"{self._tdl_path}{ver}")
        except Exception:
            self._lbl_path.setText(self._tdl_path)
