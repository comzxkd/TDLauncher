import json
import os
import re
import sys
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QEvent, QRectF, QPointF, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QFrame, QProgressBar, QStyle, QStyleOptionComboBox, QStylePainter,
    QFileDialog, QMessageBox,
    QGraphicsView, QGraphicsScene, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
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


# ---- 精密控制台配色（单一强调色 + 分层中性灰）----
BG = "#0B0D0E"      # 深空灰底
PANEL = "#121517"   # 面板
PANEL2 = "#171B1E"  # 抬升层（hover / 弹出 / 按下）
WELL = "#0D1012"    # 输入井
LINE = "#242A2F"    # 描边
LINE2 = "#323A41"   # hover 描边
INK = "#E4E9EE"     # 主文字
DIM = "#8A94A0"     # 次文字
FAINT = "#5A636D"   # 占位 / 禁用
ACC = "#4ADE80"     # 荧光绿（唯一强调色：状态 / 进度 / 焦点）
ACC_HI = "#7CF0A6"  # 强调色亮端（渐变 / hover）
ACC_LINE = "#3E6B4E"  # 强调色描边（40% 感）
ACC_BG = "rgba(74, 222, 128, 0.10)"   # 强调色底
ACC_BG_ROW = "rgba(74, 222, 128, 0.055)"  # 选中行底
ON = "#06130B"      # 强调色上的文字
DONE = "#3E8E62"    # 完成（低饱和绿）
WARN = "#E5B567"
FAIL = "#F87171"
FAIL_LINE = "#5C3A3F"
FAIL_BG = "rgba(248, 113, 113, 0.08)"

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

QSS = f"""
#Root {{ background: {BG}; }}
#Root * {{ color: {INK}; font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; font-size: 13px; }}
QLineEdit, QTextEdit, #Path, #BigUrl, #Stat, #QPct, #FInfo {{ font-family: Consolas, "Cascadia Mono", monospace; }}

#Hdr {{
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #161A1E, stop:0.15 {PANEL}, stop:1 #0F1214);
  border: 1px solid {LINE}; border-top-color: {LINE2}; border-radius: 10px;
}}
#Panel {{
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #15191C, stop:0.12 {PANEL}, stop:1 #0F1214);
  border: 1px solid {LINE}; border-top-color: {LINE2}; border-radius: 10px;
}}
#Brand {{ font-family: Consolas, "Cascadia Mono", monospace; font-size: 16px; font-weight: bold; letter-spacing: 2px; }}
#Path {{ color: {DIM}; font-size: 12px; }}
#SecTitle {{ color: {DIM}; font-size: 11px; font-weight: 700; letter-spacing: 2px; }}
#SecCount {{ color: {ACC}; font-size: 12px; font-weight: 700; }}
#FieldLabel {{ color: {DIM}; font-size: 11px; letter-spacing: 1px; }}
#Recog {{ color: {DIM}; font-size: 12px; }}
#BigTitle {{ font-size: 18px; font-weight: 700; }}
#BigUrl {{ color: {DIM}; font-size: 12px; }}
#BigPct {{ font-family: "Bahnschrift", "Segoe UI", "Microsoft YaHei UI", sans-serif; font-size: 44px; font-weight: 700; }}
#BigPctUnit {{ color: {DIM}; font-size: 16px; }}
#Meta {{ color: {DIM}; font-size: 12px; }}
#MetaVal {{ color: {INK}; font-family: Consolas, "Cascadia Mono", monospace; font-size: 12px; }}
#Badge {{ color: {DIM}; border: 1px solid {LINE}; border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
#Badge[status="running"] {{ color: {ACC}; border-color: {ACC_LINE}; background: {ACC_BG}; }}
#Badge[status="done"] {{ color: {DONE}; border-color: {LINE}; }}
#Badge[status="failed"], #Badge[status="stopped"] {{ color: {FAIL}; border-color: {FAIL_LINE}; background: {FAIL_BG}; }}
#Stat {{ color: {DIM}; font-size: 12px; }}
#StatVal {{ color: {ACC}; font-size: 12px; font-weight: 700; }}
#LogTitle {{ color: {DIM}; font-size: 11px; letter-spacing: 1px; }}
#LogToggle {{ background: transparent; border: none; color: {DIM}; font-size: 11px; letter-spacing: 2px; padding: 0; text-align: left; }}
#LogToggle:hover {{ color: {ACC}; }}

QTextEdit, QLineEdit, QComboBox, QSpinBox {{
  background: {WELL};
  border: 1px solid {LINE}; border-radius: 6px; color: {INK};
  selection-background-color: {ACC}; selection-color: {ON};
}}
QTextEdit {{ padding: 8px 11px; }}
QLineEdit, QComboBox, QSpinBox {{ padding: 6px 10px; min-height: 34px; }}
QTextEdit:hover, QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border-color: {LINE2}; }}
QTextEdit:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {ACC}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{ color: {FAINT}; border-color: {LINE}; background: #0B0E10; }}
QComboBox {{ padding-right: 32px; }}
QComboBox::drop-down {{
  subcontrol-origin: padding; subcontrol-position: top right; width: 30px;
  background: {PANEL2}; border: none; border-left: 1px solid {LINE};
  border-top-right-radius: 6px; border-bottom-right-radius: 6px;
}}
QComboBox QAbstractItemView {{
  background: {PANEL2}; border: 1px solid {LINE2}; color: {INK};
  selection-background-color: rgba(74, 222, 128, 0.14); selection-color: {INK}; outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; height: 0; border: none; }}

QPushButton {{
  background: transparent; color: {INK};
  border: 1px solid {LINE}; border-radius: 6px; padding: 6px 16px; min-height: 34px;
}}
QPushButton:hover {{ background: {PANEL2}; border-color: {LINE2}; }}
QPushButton:pressed {{ background: {PANEL2}; color: {ACC}; border-color: {ACC_LINE}; }}
QPushButton:disabled {{ background: transparent; color: {FAINT}; border-color: {LINE}; }}
QPushButton#Primary {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {ACC_HI}, stop:1 {ACC}); color: {ON}; border-color: {ACC_HI}; font-weight: 700; }}
QPushButton#Primary:hover {{ background: {ACC_HI}; border-color: #A6F5C3; }}
QPushButton#Primary:pressed {{ background: {ACC}; }}
QPushButton#Primary:disabled {{ background: #1C2B22; color: #4E5F54; border-color: #1C2B22; }}
QPushButton#Stop {{ color: {WARN}; border-color: #4A4030; font-weight: 600; }}
QPushButton#Stop:hover {{ background: rgba(229, 181, 103, 0.08); border-color: {WARN}; }}
QPushButton#Stop:pressed {{ background: rgba(229, 181, 103, 0.14); color: {WARN}; border-color: {WARN}; }}
QPushButton#Stop:disabled {{ color: {FAINT}; border-color: {LINE}; background: transparent; }}
QPushButton#Toggle {{
  padding: 6px 12px; color: {DIM}; border: 1px solid {LINE};
  border-radius: 6px; background: transparent; font-size: 13px; min-height: 34px;
}}
QPushButton#Toggle:hover {{ color: {INK}; border-color: {LINE2}; background: {PANEL2}; }}
QPushButton#Toggle:checked {{
  color: {ACC}; background: {ACC_BG};
  border-color: {ACC_LINE}; font-weight: 700;
}}

QMenu {{ background: {PANEL2}; color: {INK}; border: 1px solid {LINE2}; padding: 4px; border-radius: 6px; }}
QMenu::item {{ background: transparent; color: {INK}; padding: 6px 28px 6px 10px; border-radius: 4px; }}
QMenu::item:selected {{ background: rgba(74, 222, 128, 0.14); color: {ACC}; }}
QMenu::item:disabled {{ color: {FAINT}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 4px 6px; }}

QProgressBar {{ background: #171C20; border: none; border-radius: 2px; }}
QProgressBar::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACC}, stop:1 {ACC_HI}); border-radius: 2px; }}
QProgressBar[status="done"]::chunk {{ background: {DONE}; }}
QProgressBar[status="failed"]::chunk {{ background: {FAIL}; }}
QProgressBar[status="stopped"]::chunk {{ background: {FAINT}; }}

#QRow {{ background: transparent; border: none; border-radius: 6px; }}
#QRow:hover {{ background: {PANEL2}; }}
#QRow[active="true"] {{ background: {ACC_BG_ROW}; }}
#QName {{ color: {INK}; font-size: 13px; }}
#QRow[active="true"] #QName {{ color: {ACC}; font-weight: 700; }}
#QPct {{ color: {DIM}; font-size: 12px; }}
#FName {{ color: {INK}; font-family: Consolas, "Cascadia Mono", monospace; font-size: 12px; }}
#FInfo {{ color: {DIM}; font-size: 12px; }}

#Scroll {{ background: transparent; border: none; }}
#Scroll > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; border: none; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {LINE2}; border-radius: 4px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: #45505A; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QLabel {{ background: transparent; }}
"""


class ComboBox(QComboBox):
    """带清晰箭头槽的下拉框。"""

    def paintEvent(self, event) -> None:
        painter = QStylePainter(self)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        option.subControls &= ~QStyle.SC_ComboBoxArrow
        painter.drawComplexControl(QStyle.CC_ComboBox, option)
        painter.drawControl(QStyle.CE_ComboBoxLabel, option)

        arrow = self.rect().adjusted(self.width() - 30, 1, -1, -1)
        painter.fillRect(arrow, QColor(PANEL2))
        painter.setPen(QPen(QColor(LINE), 1))
        painter.drawLine(arrow.topLeft(), arrow.bottomLeft())
        painter.setPen(QPen(QColor(ACC_HI if self.underMouse() else ACC), 2))
        center = QPointF(arrow.center().x(), arrow.center().y() - 1)
        painter.drawLine(QPointF(center.x() - 4, center.y() - 2), QPointF(center.x(), center.y() + 2))
        painter.drawLine(QPointF(center.x(), center.y() + 2), QPointF(center.x() + 4, center.y() - 2))


class TipLabel(QLabel):
    """带阴影的悬浮提示，配色与终端主题一致。"""

    def __init__(self):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setObjectName("Tip")
        self.setStyleSheet(
            f"#Tip {{ background:{PANEL2}; color:{INK}; border:1px solid {ACC_LINE}; border-radius:6px; "
            f"padding:7px 11px; font-family:Consolas,'Microsoft YaHei UI',monospace; font-size:12px; }}"
        )
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(20)
        sh.setOffset(0, 5)
        sh.setColor(QColor(0, 0, 0, 190))
        self.setGraphicsEffect(sh)


class CellsBar(QWidget):
    """把进度画成轻量的分段指示条。"""

    def __init__(self, count: int = 24, parent=None):
        super().__init__(parent)
        self._count = count
        self._value = 0
        self._display_value = 0.0
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(240)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.valueChanged.connect(self._set_display_value)
        self.setMinimumHeight(10)

    def setValue(self, v: int) -> None:
        v = max(0, min(100, int(v)))
        if v == self._value:
            return
        self._value = v
        if not self.isVisible():
            self._display_value = float(v)
            self.update()
            return
        self._animation.stop()
        self._animation.setStartValue(self._display_value)
        self._animation.setEndValue(float(v))
        self._animation.start()

    def _set_display_value(self, value) -> None:
        self._display_value = float(value)
        self.update()

    def value(self) -> int:
        return self._value

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds = self.rect().adjusted(0, 1, 0, -1)
        gap = 4
        cell_width = max(1.0, (bounds.width() - gap * (self._count - 1)) / self._count)
        on = self._display_value / 100.0 * self._count
        active = QColor(ACC)
        active.setAlpha(90)
        painter.setPen(Qt.NoPen)
        for i in range(self._count):
            x = bounds.x() + i * (cell_width + gap)
            rect = QRectF(x, bounds.y(), cell_width, bounds.height())
            painter.setBrush(QColor("#1B2126"))
            painter.drawRoundedRect(rect, 2.5, 2.5)
            fill = max(0.0, min(1.0, on - i))
            if fill > 0:
                painter.setBrush(active if fill < 1 else QColor(ACC))
                painter.drawRoundedRect(QRectF(rect.x(), rect.y(), rect.width() * fill, rect.height()), 2.5, 2.5)


class StatusMark(QWidget):
    """队列行状态图标：矢量绘制，粗细对齐，不用文本符号。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._status = "queued"
        self._active = False

    def set_status(self, status: str) -> None:
        self._status = status
        self.update()

    def set_active(self, on: bool) -> None:
        self._active = on
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = {"running": ACC, "done": DONE, "failed": FAIL,
                 "stopped": DIM}.get(self._status, ACC if self._active else DIM)
        pen = QPen(QColor(color), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        c = self.rect().center()
        if self._status == "running":
            painter.setBrush(QColor(color))
            painter.drawPolygon([QPointF(c.x() - 3, c.y() - 4),
                                 QPointF(c.x() - 3, c.y() + 4),
                                 QPointF(c.x() + 4.5, c.y())])
        elif self._status == "done":
            painter.drawPolyline([QPointF(c.x() - 4.5, c.y() + 0.5),
                                  QPointF(c.x() - 1, c.y() + 4),
                                  QPointF(c.x() + 5, c.y() - 4)])
        elif self._status == "failed":
            painter.drawLine(QPointF(c.x() - 4, c.y() - 4), QPointF(c.x() + 4, c.y() + 4))
            painter.drawLine(QPointF(c.x() + 4, c.y() - 4), QPointF(c.x() - 4, c.y() + 4))
        elif self._status == "stopped":
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(c.x() - 3.5, c.y() - 3.5, 7, 7), 1.5, 1.5)
        else:
            painter.drawEllipse(QPointF(c.x(), c.y()), 4, 4)


class QueueRow(QFrame):
    """队列里的一行：标记 + 名称 + 百分比 + 迷你进度条。"""

    def __init__(self, name: str, index: int = -1, on_click=None, parent=None):
        super().__init__(parent)
        self.setObjectName("QRow")
        self.setProperty("active", "false")
        self.setCursor(Qt.PointingHandCursor)
        self._index = index
        self._on_click = on_click
        self._row_animation = QVariantAnimation(self)
        self._row_animation.setDuration(160)
        self._row_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._row_animation.valueChanged.connect(self._set_row_opacity)
        self._row_opacity = 0.0
        self._bar_value = 0
        self._bar_animation = QVariantAnimation(self)
        self._bar_animation.setDuration(220)
        self._bar_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._bar_animation.valueChanged.connect(self._set_bar_value)
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 6, 8, 7)
        v.setSpacing(5)
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.marker = StatusMark()
        self.name = QLabel(name)
        self.name.setObjectName("QName")
        self.pct = QLabel("")
        self.pct.setObjectName("QPct")
        h.addWidget(self.marker, 0, Qt.AlignVCenter)
        h.addWidget(self.name, 1)
        h.addWidget(self.pct)
        v.addLayout(h)
        self.bar = QProgressBar()
        self.bar.setFixedHeight(4)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        v.addWidget(self.bar)

    def mousePressEvent(self, event):
        if self._on_click is not None:
            self._on_click(self._index)
        super().mousePressEvent(event)

    def _set_row_opacity(self, value):
        self._row_opacity = float(value)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._row_opacity <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._row_opacity)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(ACC))
        painter.drawRoundedRect(QRectF(0, 0, 3, self.height()), 1.5, 1.5)

    def set_active(self, on: bool) -> None:
        self._row_animation.stop()
        if not self.isVisible():
            self._row_opacity = 1.0 if on else 0.0
            self.update()
        else:
            self._row_animation.setStartValue(self._row_opacity)
            self._row_animation.setEndValue(1.0 if on else 0.0)
            self._row_animation.start()
        self.marker.set_active(on)
        self.setProperty("active", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_status(self, status: str) -> None:
        self.marker.set_status(status)
        self.setProperty("status", status)
        self.style().unpolish(self)
        self.style().polish(self)

    def _set_bar_value(self, value):
        self._bar_value = round(value)
        self.bar.setValue(self._bar_value)

    def set_pct(self, v: int) -> None:
        v = max(0, min(100, int(v)))
        if v != self._bar_value:
            if not self.isVisible():
                self._bar_value = v
                self.bar.setValue(v)
            else:
                self._bar_animation.stop()
                self._bar_animation.setStartValue(self._bar_value)
                self._bar_animation.setEndValue(v)
                self._bar_animation.start()
        if v >= 100 and self._bar_value >= 100:
            self.bar.setProperty("status", "done")
        elif v <= 0 and self._bar_value <= 0:
            self.bar.setProperty("status", "")
        self.bar.style().unpolish(self.bar)
        self.bar.style().polish(self.bar)
        self.pct.setText(f"{v}%")


class Job:
    """一个链接的下载任务（含其若干命令，顺序执行）。"""

    def __init__(self, name: str, url: str, commands: list, labels: list, msgid: int = 0):
        self.name = name
        self.url = url
        self.commands = commands
        self.labels = labels
        self.msgid = msgid
        self.status = "queued"      # queued | running | done | failed | stopped
        self.cur = 0
        self.done = 0
        self.pct = 0
        self.command_pct = 0.0
        self.command_file_progress: dict = {}
        self.command_log_start = 0
        self.stage_progress = [0.0] * len(commands)
        download_count = sum(1 for command in commands if command and command[0] == "dl")
        self.download_stage_count = download_count
        if download_count:
            weight = 1.0 / download_count
            self.stage_weights = [weight if command and command[0] == "dl" else 0.0
                                  for command in commands]
        else:
            weight = 1.0 / max(1, len(commands))
            self.stage_weights = [weight] * len(commands)
        self.speed = "—"
        self.eta = "—"
        self.channel = ""
        self.log: list = []
        self.files: dict = {}       # 文件名 -> 百分比
        self.file_identities: dict = {}  # (peer ID, message ID) -> 文件行键集合
        self.parser = ProgressParser()
        self.runner = None
        self.qrow = None


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
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(220)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.valueChanged.connect(self._set_bar_value)
        self._display_pct = 0
        self.info = QLabel("")
        self._bar_value = 0
        self.info.setObjectName("FInfo")
        self.info.setFixedWidth(60)
        g.addWidget(self.name, 0, 0)
        g.setColumnStretch(0, 1)
        g.addWidget(self.bar, 0, 1)
        g.addWidget(self.info, 0, 2)

    def _set_bar_value(self, value):
        self._bar_value = round(value)
        self.bar.setValue(self._bar_value)

    def set_pct(self, v: int) -> None:
        v = max(0, min(100, int(v)))
        if v != self._display_pct:
            if not self.isVisible():
                self._bar_value = v
                self.bar.setValue(v)
                self._display_pct = v
            else:
                self._animation.stop()
                self._animation.setStartValue(self._bar_value)
                self._animation.setEndValue(v)
                self._animation.start()
                self._display_pct = v
        if v >= 100:
            self.bar.setProperty("status", "done")
        elif v <= 0:
            self.bar.setProperty("status", "")
        self.bar.style().unpolish(self.bar)
        self.bar.style().polish(self.bar)
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

        self._jobs: list = []
        self._max_parallel = 1
        self._sel = 0
        self._queue_rows: list = []
        self._detail_files: dict = {}
        self._detail_file_rows: list = []
        self._total_tasks = 0
        self._chat_info_cache: dict = {}
        self._tip = TipLabel()
        self._tip_texts: dict = {}
        self._app_log: list = []

        # 固定画布 + 等比缩放
        self._design = QWidget()
        self._design.setObjectName("Root")
        self._build_ui()
        self._design.setFixedSize(DESIGN_W, DESIGN_H)

        self._scene = QGraphicsScene()
        self._scene.setSceneRect(0, 0, DESIGN_W, DESIGN_H)
        self._scene.setBackgroundBrush(QColor(BG))
        self._proxy = self._scene.addWidget(self._design)

        self._view = QGraphicsView(self._scene)
        self._view.setFrameShape(QFrame.NoFrame)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setAlignment(Qt.AlignCenter)
        self._view.setStyleSheet(f"background:{BG}; border:none;")
        self.setCentralWidget(self._view)

        self._apply_theme()

        self.setMinimumSize(DESIGN_W, DESIGN_H)
        w = self._config.window_width or DESIGN_W
        w = max(DESIGN_W, int(w))
        self.resize(w, round(w / ASPECT))

        self._apply_config()
        if self._tdl_path:
            QTimer.singleShot(60, self._load_tdl_version)

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
        pal = self._design.palette()
        pal.setColor(pal.ColorRole.PlaceholderText, QColor(FAINT))
        self._design.setPalette(pal)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(
                f"QToolTip {{ background:{PANEL2}; color:{INK}; border:1px solid {ACC_LINE}; border-radius:6px; "
                f"padding:6px 9px; font-family:Consolas,'Microsoft YaHei UI',monospace; font-size:12px; }}"
                f"QMenu {{ background:{PANEL2}; color:{INK}; border:1px solid {LINE2}; padding:4px; border-radius:6px; }}"
                f"QMenu::item {{ background:transparent; color:{INK}; padding:6px 28px 6px 10px; border-radius:4px; }}"
                f"QMenu::item:selected {{ background:rgba(74,222,128,0.14); color:{ACC}; }}"
                f"QMenu::item:disabled {{ color:{FAINT}; }}"
                f"QMenu::separator {{ height:1px; background:{LINE}; margin:4px 6px; }}"
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
        b = QPushButton(text)
        b.setObjectName("Toggle")
        b.setCheckable(True)
        b.setChecked(checked)
        if tip:
            self._tip_texts[b] = tip
            b.installEventFilter(self)
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
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ---- 顶栏 ----
        hdr = QFrame()
        hdr.setObjectName("Hdr")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 10, 16, 10)
        self._lbl_brand = QLabel('TDLauncher<span style="color:%s">_</span>' % ACC)
        self._lbl_brand.setObjectName("Brand")
        hl.addWidget(self._lbl_brand)
        hl.addStretch(1)
        self._lbl_path = QLabel("tdl")
        self._lbl_path.setObjectName("Path")
        hl.addWidget(self._lbl_path)
        root.addWidget(hdr)

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        # 左：下载链接
        links = QFrame()
        links.setObjectName("Panel")
        ll = QVBoxLayout(links)
        ll.setContentsMargins(16, 14, 16, 14)
        ll.setSpacing(10)
        t = QLabel("下载链接 · 每行一个任务")
        t.setObjectName("SecTitle")
        ll.addWidget(t)
        self._txt_links = QTextEdit()
        self._txt_links.setPlaceholderText("https://t.me/telegram/193")
        self._txt_links.setFont(QFont("Consolas", 12))
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
        body.addWidget(links, 5)

        right = QVBoxLayout()
        right.setSpacing(12)
        body.addLayout(right, 14)

        # 参数
        params = QFrame()
        params.setObjectName("Panel")
        pl = QVBoxLayout(params)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.setSpacing(10)
        params_title = QLabel("下载参数")
        params_title.setObjectName("SecTitle")
        pl.addWidget(params_title)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        for i, s in enumerate([16, 12, 12, 8, 8]):
            grid.setColumnStretch(i, s)

        self._combo_content = ComboBox()
        self._combo_content.addItems(["全部媒体", "仅图片", "仅视频", "仅音频", "自定义"])
        self._combo_content.currentIndexChanged.connect(self._on_content_type_changed)
        grid.addWidget(self._field("内容类型", self._combo_content), 0, 0)
        self._txt_custom_ext = QLineEdit()
        self._txt_custom_ext.setPlaceholderText("jpg,png,mp4")
        grid.addWidget(self._field("自定义扩展名", self._txt_custom_ext), 0, 1)
        self._combo_template = ComboBox()
        self._combo_template.addItems(["原始文件名", "tdl 默认"])
        self._combo_template.currentIndexChanged.connect(self._on_template_changed)
        grid.addWidget(self._field("文件名", self._combo_template), 0, 2)
        self._spin_threads = QSpinBox()
        self._spin_threads.setRange(1, 32)
        self._spin_threads.setMinimumWidth(64)
        grid.addWidget(self._field("线程", self._spin_threads), 0, 3)
        self._spin_limit = QSpinBox()
        self._spin_limit.setRange(1, 16)
        self._spin_limit.setMinimumWidth(64)
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
        toggles.setSpacing(8)
        self._chk_comments = self._toggle("评论区下载", tip="下载帖子媒体后，继续导出并下载该帖评论中的媒体。")
        self._chk_subfolder = self._toggle("按帖归档", tip="将每条链接的媒体保存到“频道名称/消息 ID”独立目录。")
        self._chk_skip_same = self._toggle("跳过重复文件", tip="跳过下载目录中已存在且名称、大小相同的文件。")
        self._chk_resume = self._toggle("断点续传", tip="继续下载未完成的文件，避免从头重新传输。")
        self._chk_takeout = self._toggle("Takeout 模式", tip="使用 Telegram Takeout 会话下载，适合批量获取媒体。")
        self._chk_group = self._toggle("下载相册分组", tip="识别并按 Telegram 媒体组处理相册内容。")
        self._chk_proxy = self._toggle("启用代理", tip="通过下方填写的代理地址连接 Telegram。")
        for w in (self._chk_comments, self._chk_subfolder, self._chk_skip_same,
                  self._chk_resume, self._chk_takeout, self._chk_group, self._chk_proxy):
            toggles.addWidget(w)
        toggles.addStretch(1)
        pl.addLayout(toggles)
        right.addWidget(params)

        # 中段
        work = QHBoxLayout()
        work.setSpacing(12)
        right.addLayout(work, 1)

        # 队列
        queue = QFrame()
        queue.setObjectName("Panel")
        ql = QVBoxLayout(queue)
        ql.setContentsMargins(16, 14, 16, 14)
        ql.setSpacing(8)
        qhead = QHBoxLayout()
        qh = QLabel("下载队列")
        qh.setObjectName("SecTitle")
        qhead.addWidget(qh)
        qhead.addStretch(1)
        self._lbl_qcount = QLabel("0/0 活动")
        self._lbl_qcount.setObjectName("SecCount")
        qhead.addWidget(self._lbl_qcount)
        ql.addLayout(qhead)
        self._queue_scroll, self._queue_box = self._scroll()
        ql.addWidget(self._queue_scroll, 1)
        work.addWidget(queue, 5)

        # 进度
        prog = QFrame()
        prog.setObjectName("Panel")
        prl = QVBoxLayout(prog)
        prl.setContentsMargins(16, 14, 16, 14)
        prl.setSpacing(10)
        self._lbl_progress_title = QLabel("下载状态")
        self._lbl_progress_title.setObjectName("SecTitle")
        prl.addWidget(self._lbl_progress_title)

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
        amount.setSpacing(20)
        big = QHBoxLayout()
        big.setSpacing(3)
        self._lbl_bigpct = QLabel("0")
        self._lbl_bigpct.setObjectName("BigPct")
        self._bigpct_display = 0.0
        self._bigpct_animation = QVariantAnimation(self)
        self._bigpct_animation.setDuration(180)
        self._bigpct_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._bigpct_animation.valueChanged.connect(self._set_bigpct_display)
        big.addWidget(self._lbl_bigpct, 0, Qt.AlignBottom)
        u = QLabel("%")
        u.setObjectName("BigPctUnit")
        big.addWidget(u, 0, Qt.AlignBottom)
        amount.addLayout(big, 0)
        ar = QVBoxLayout()
        ar.setSpacing(10)
        self._cells = CellsBar(24)
        ar.addWidget(self._cells)
        meta = QHBoxLayout()
        meta.setSpacing(24)
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
        self._btn_log = QPushButton("下载日志 ▾")
        self._btn_log.setObjectName("LogToggle")
        self._btn_log.setCheckable(True)
        self._btn_log.setChecked(True)
        self._btn_log.toggled.connect(self._toggle_log)
        logcol.addWidget(self._btn_log, 0, Qt.AlignLeft)
        self._txt_output = QTextEdit()
        self._txt_output.setReadOnly(True)
        self._txt_output.setFont(QFont("Consolas", 10))
        self._log_height = 88
        self._txt_output.setFixedHeight(self._log_height)
        self._txt_output.setVisible(True)
        self._log_animation = QVariantAnimation(self)
        self._log_animation.setDuration(180)
        self._log_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._log_animation.valueChanged.connect(self._animate_log_height)
        self._log_animation.finished.connect(self._hide_log_output)
        self._log_animation.finished.connect(self._fit)
        logcol.addWidget(self._txt_output)
        pfoot.addLayout(logcol, 1)

        self._lbl_status = QLabel("就绪", self)
        self._lbl_status.setObjectName("StatVal")
        self._lbl_status.hide()
        self._lbl_tdlpath = QLabel("tdl: —", self)
        self._lbl_tdlpath.setObjectName("Stat")
        self._lbl_tdlpath.hide()
        self._lbl_sstate = QLabel("状态: 就绪", self)
        self._lbl_sstate.setObjectName("Stat")
        self._lbl_sstate.hide()

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

        work.addWidget(prog, 12)

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

    def _animate_log_height(self, value):
        self._log_height = max(0, round(value))
        self._txt_output.setFixedHeight(self._log_height)
        if self._log_height == 0:
            self._txt_output.setVisible(False)
        elif self._btn_log.isChecked():
            self._txt_output.setVisible(True)

    def _toggle_log(self, on: bool):
        self._log_animation.stop()
        self._btn_log.setText("下载日志 ▾" if on else "下载日志 ▸")
        self._log_animation.setStartValue(self._log_height)
        self._log_animation.setEndValue(88 if on else 0)
        if on:
            self._txt_output.setVisible(True)
        self._log_animation.start()

    def _hide_log_output(self):
        if not self._btn_log.isChecked():
            self._txt_output.setFixedHeight(0)
            self._txt_output.setVisible(False)

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
        if any(j.status == "running" for j in self._jobs):
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

    # ---- 队列 / 详情 ----

    def _clear_layout(self, box, store):
        for w in list(store):
            w.setParent(None)
        store.clear()

    def _add_queue_row(self, name: str, index: int) -> QueueRow:
        row = QueueRow(name, index, self._select_job)
        self._insert(self._queue_box, row)
        self._queue_rows.append(row)
        return row

    def _ensure_detail_file(self, name: str, pct: int):
        row = self._detail_files.get(name)
        if row is None:
            row = FileRow(name)
            self._insert(self._files_box, row)
            self._detail_files[name] = row
            self._detail_file_rows.append(row)
        row.set_pct(pct)

    def _selected_job(self):
        if 0 <= self._sel < len(self._jobs):
            return self._jobs[self._sel]
        return None

    def _select_job(self, idx: int):
        self._sel = idx
        for i, j in enumerate(self._jobs):
            if j.qrow is not None:
                j.qrow.set_active(i == idx)
        self._show_detail(self._selected_job())

    def _set_bigpct_display(self, value):
        self._bigpct_display = float(value)
        self._lbl_bigpct.setText(str(round(self._bigpct_display)))

    def _animate_bigpct(self, value):
        value = max(0, min(100, int(value)))
        if not self._lbl_bigpct.isVisible():
            self._bigpct_display = float(value)
            self._lbl_bigpct.setText(str(value))
            return
        self._bigpct_animation.stop()
        self._bigpct_animation.setStartValue(self._bigpct_display)
        self._bigpct_animation.setEndValue(float(value))
        self._bigpct_animation.start()

    def _show_detail(self, job):
        self._clear_layout(self._files_box, self._detail_file_rows)
        self._detail_files = {}
        if job is None:
            return
        self._lbl_current.setText(job.channel or job.name)
        self._lbl_url.setText(job.url)
        self._lbl_badge.setText({"running": "下载中", "done": "已完成", "failed": "失败",
                                 "queued": "排队", "stopped": "已停止"}.get(job.status, job.status))
        self._lbl_badge.setProperty("status", job.status)
        self._lbl_badge.style().unpolish(self._lbl_badge)
        self._lbl_badge.style().polish(self._lbl_badge)
        self._set_badge_breathing(job.status == "running")
        self._animate_bigpct(job.pct)
        self._cells.setValue(job.pct)
        self._lbl_speed.setText(job.speed or "—")
        self._lbl_eta.setText(job.eta or "—")
        for name, pct in job.files.items():
            self._ensure_detail_file(name, pct)
        self._sync_filecount(job)
        self._txt_output.setPlainText("\n".join(self._app_log + job.log))
        self._btn_log.setText("下载日志 ▾" if self._btn_log.isChecked() else "下载日志 ▸")

    def _refresh_detail_progress(self, job):
        self._animate_bigpct(job.pct)
        self._cells.setValue(job.pct)
        self._lbl_speed.setText(job.speed or "—")
        self._lbl_eta.setText(job.eta or "—")

    def _sync_filecount(self, job):
        total = len(job.files)
        done = sum(1 for v in job.files.values() if v >= 100)
        self._lbl_totalcount.setText(f"{done}/{total}")

    def _append_log(self, text: str):
        self._txt_output.append(text)
        sb = self._txt_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ---- 下载控制（多链接并行）----

    def _start_download(self):
        text = self._txt_links.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "请先粘贴 Telegram 链接。")
            return
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        dir_path = self._txt_dir.text().strip()
        if not os.path.isdir(dir_path):
            QMessageBox.warning(self, "错误", f"目录不存在: {dir_path}")
            return
        if not self._tdl_path:
            QMessageBox.warning(self, "错误", "未找到 tdl.exe。")
            return

        self._save_config()

        self._jobs = []
        self._clear_layout(self._queue_box, self._queue_rows)
        self._clear_layout(self._files_box, self._detail_file_rows)
        self._detail_files = {}
        self._total_tasks = 0
        self._sel = 0

        for li, url in enumerate(lines):
            parsed = parse_telegram_link(url)
            include_comments = self._chk_comments.isChecked()
            auto_sub = self._chk_subfolder.isChecked()
            if parsed.channel:
                disp = f"#{parsed.message_id} @{parsed.channel}" if parsed.message_id else f"@{parsed.channel}"
            else:
                disp = f"#{parsed.message_id}" if parsed.message_id else url
            job_config = self._config
            if auto_sub and parsed.message_id:
                import copy
                job_config = copy.copy(self._config)
                folder_name = self._resolve_channel_name(parsed)
                sub_dir = os.path.join(self._config.download_dir, folder_name, str(parsed.message_id))
                job_config.download_dir = sub_dir
            cmds = build_download_commands(url, parsed, job_config, include_comments)
            labels = []
            for cmd in cmds:
                if cmd[0] == "dl" and "-f" in cmd:
                    labels.append("下载评论区媒体")
                elif cmd[0] == "chat":
                    labels.append("导出评论区列表")
                else:
                    labels.append("下载帖子媒体")
            job = Job(disp, url, cmds, labels, parsed.message_id or 0)
            job.qrow = self._add_queue_row(disp, li)
            job.qrow.pct.setText("排队")
            self._jobs.append(job)
            self._total_tasks += len(cmds)

        if not self._jobs or self._total_tasks == 0:
            return

        self._update_ui_running(True)
        self._txt_output.clear()
        self._lbl_qcount.setText(f"0/{len(self._jobs)} 活动")
        self._select_job(0)

        # tdl 的 session 是独占锁，多个进程不能同时开，因此逐条串行执行
        self._max_parallel = 1
        self._pump()

    def _pump(self):
        active = sum(1 for j in self._jobs if j.status == "running")
        queued = [j for j in self._jobs if j.status == "queued"]
        while active < self._max_parallel and queued:
            j = queued.pop(0)
            self._start_job(j)
            active += 1
        if not any(j.status == "running" for j in self._jobs) and not any(j.status == "queued" for j in self._jobs):
            self._finish_all()

    def _start_job(self, job):
        job.status = "running"
        job.cur = 0
        job.parser.reset()
        if job.qrow is not None:
            job.qrow.set_status("running")
        self._refresh_active_count()
        if job is self._selected_job():
            self._show_detail(job)
        self._run_job_cmd(job)

    def _run_job_cmd(self, job):
        if job.cur >= len(job.commands):
            job.status = "done" if job.done == len(job.commands) else "failed"
            self._on_job_done(job)
            return
        job.parser.reset()
        job.command_pct = 0.0
        job.command_file_progress.clear()
        job.command_log_start = len(job.log)
        job.speed = "—"
        job.eta = "—"
        args = job.commands[job.cur]
        job.runner = TdlRunner(self._tdl_path)
        job.runner.on_stdout = lambda t, j=job: self._on_job_output(j, t)
        job.runner.on_stderr = lambda t, j=job: self._on_job_output(j, t)
        job.runner.on_exit = lambda c, j=job: self._on_job_cmd_exit(j, c)
        job.runner.start(args)

    def _on_job_cmd_exit(self, job, code):
        job.runner = None
        export_empty = code == 0 and self._export_has_no_messages(job)
        no_comment_group = code != 0 and self._is_no_comment_group_error(job)
        skip_index = None
        if export_empty:
            skip_index = self._empty_comment_download_index(job, job.cur)
        elif no_comment_group:
            skip_index = self._comment_download_index(job, job.cur)
        skipped_comment_stage = export_empty or no_comment_group
        if code == 0 or skipped_comment_stage:
            job.done += 1
            if 0 <= job.cur < len(job.stage_progress):
                job.stage_progress[job.cur] = 100.0
            # 下载命令成功后，只将本命令观察到的文件标记为完成。
            if code == 0 and 0 <= job.cur < len(job.commands) and job.commands[job.cur][0] == "dl":
                for k in job.command_file_progress:
                    job.files[k] = 100
                    job.command_file_progress[k] = 100.0
            self._update_job_progress(job)
        job.cur += 1
        if skip_index == job.cur:
            job.done += 1
            job.stage_progress[job.cur] = 100.0
            message = "评论区没有可下载媒体，已跳过下载" if export_empty else "帖子没有关联评论区，已跳过评论下载"
            job.log.append(message)
            if job is self._selected_job():
                self._append_log(message)
            job.cur += 1
        elif code != 0 and not skipped_comment_stage:
            job.status = "failed"
            job.cur = len(job.commands)
        self._update_job_row(job)
        if job.cur >= len(job.commands):
            if job.status != "failed":
                job.status = "done" if job.done == len(job.commands) else "failed"
            self._on_job_done(job)
        else:
            job.parser.reset()
            if job is self._selected_job():
                self._show_detail(job)
            self._run_job_cmd(job)

    @staticmethod
    def _comment_download_index(job, export_index):
        if not 0 <= export_index < len(job.commands):
            return None
        export_cmd = job.commands[export_index]
        if export_cmd[:2] != ["chat", "export"]:
            return None
        download_index = export_index + 1
        if download_index >= len(job.commands):
            return None
        download_cmd = job.commands[download_index]
        if download_cmd[:1] != ["dl"] or "-f" not in download_cmd:
            return None
        try:
            output_path = export_cmd[export_cmd.index("-o") + 1]
            file_index = download_cmd.index("-f") + 1
        except IndexError:
            return None
        if file_index >= len(download_cmd) or download_cmd[file_index] != output_path:
            return None
        return download_index

    def _is_no_comment_group_error(self, job):
        if not 0 <= job.cur < len(job.commands):
            return False
        command = job.commands[job.cur]
        if command[:2] != ["chat", "export"]:
            return False
        text = "\n".join(job.log[job.command_log_start:]).lower()
        patterns = (
            "no linked group",
            "message_id_invalid",
            "msg_id_invalid",
            "replies not found",
            "reply message not found",
            "message to reply not found",
            "comments are not available",
        )
        return any(pattern in text for pattern in patterns)

    def _export_has_no_messages(self, job):
        if not 0 <= job.cur < len(job.commands):
            return False
        export_cmd = job.commands[job.cur]
        if export_cmd[:2] != ["chat", "export"] or "-o" not in export_cmd:
            return False
        # 仅在导出命令成功退出后调用，此时 tdl 已写出该文件。
        try:
            output_path = export_cmd[export_cmd.index("-o") + 1]
            with open(output_path, "r", encoding="utf-8") as f:
                exported = json.load(f)
        except (OSError, ValueError, IndexError):
            return False
        return isinstance(exported, dict) and exported.get("messages") == []

    @staticmethod
    def _empty_comment_download_index(job, export_index):
        if not 0 <= export_index < len(job.commands):
            return None
        export_cmd = job.commands[export_index]
        if export_cmd[:2] != ["chat", "export"] or "-o" not in export_cmd:
            return None
        try:
            output_path = export_cmd[export_cmd.index("-o") + 1]
            with open(output_path, "r", encoding="utf-8") as f:
                exported = json.load(f)
        except (OSError, ValueError, IndexError):
            return None
        if not isinstance(exported, dict) or exported.get("messages") != []:
            return None

        download_index = export_index + 1
        if download_index >= len(job.commands):
            return None
        download_cmd = job.commands[download_index]
        if download_cmd[:1] != ["dl"] or "-f" not in download_cmd:
            return None
        file_index = download_cmd.index("-f") + 1
        if file_index >= len(download_cmd) or download_cmd[file_index] != output_path:
            return None
        return download_index

    def _on_job_done(self, job):
        if job.status == "done":
            job.pct = 100
        self._update_job_row(job)
        self._refresh_active_count()
        if job is self._selected_job():
            self._show_detail(job)
        self._pump()

    def _set_row_pct(self, job):
        if job.qrow is not None:
            job.qrow.set_pct(job.pct)

    def _update_job_row(self, job):
        if job.qrow is None:
            return
        if job.status == "done":
            job.qrow.set_pct(100)
            job.qrow.set_status("done")
        elif job.status == "failed":
            job.qrow.set_status("failed")
        else:
            self._set_row_pct(job)
            job.qrow.set_status(job.status)

    def _refresh_active_count(self):
        active = sum(1 for j in self._jobs if j.status == "running")
        self._lbl_qcount.setText(f"{active}/{len(self._jobs)} 活动")

    def _finish_all(self):
        self._update_ui_running(False)
        ok = sum(1 for j in self._jobs if j.status == "done")
        failed = sum(1 for j in self._jobs if j.status == "failed")
        if failed:
            summary = f"━━ 全部结束: {ok}/{len(self._jobs)} 个链接成功，失败 {failed} 个 ━━"
        else:
            summary = f"━━ 全部完成: {ok}/{len(self._jobs)} 个链接成功 ━━"
        self._app_log.append(summary)
        self._show_detail(self._selected_job())

    def _on_job_output(self, job, text):
        for frame in text.split("\r"):
            frame = frame.strip()
            if frame:
                self._process_job_frame(job, frame)

    @staticmethod
    def _is_progress(s: str) -> bool:
        return bool(re.search(r"\d+(?:\.\d+)?%\s*\[", s) or re.match(r"^\[[\s.#]+\]", s))

    def _process_job_frame(self, job, frame):
        clean = ANSI.sub("", frame).strip()
        if not clean:
            return
        low = clean.lower()
        if self._is_progress(clean):
            self._apply_progress_frame(job, clean)
            if "done!" in low:
                self._mark_completed_file(job, clean)
            if not job.channel:
                mm = re.match(r"^(.+?)\(\d+\):\d+", clean.lstrip())
                if mm:
                    job.channel = mm.group(1).strip()
                    if job is self._selected_job():
                        self._lbl_current.setText(job.channel)
            if job.qrow is not None and job.status == "running":
                self._set_row_pct(job)
            if job is self._selected_job():
                self._refresh_detail_progress(job)
            return
        if clean.lstrip().startswith("CPU:"):
            return
        job.log.append(clean)
        if job is self._selected_job():
            self._append_log(clean)
        if "done!" in low:
            self._mark_completed_file(job, clean)
        if any(k in low for k in ("error", "flood", "failed", "panic")) or "失败" in clean:
            if not self._btn_log.isChecked():
                self._btn_log.setChecked(True)

    def _mark_completed_file(self, job, clean):
        identity_match = re.search(r"\((?P<peer>\d+)\):(?P<message>\d+)", clean)
        if identity_match:
            identity = (identity_match.group("peer"), identity_match.group("message"))
            keys = job.file_identities.get(identity, ())
            if not keys:
                descriptor = clean.split("->", 1)[0].strip()
                descriptor = re.sub(r"\s*(?:done!|failed!)\s*$", "", descriptor, flags=re.IGNORECASE)
                name = self._desc_key(descriptor)
                job.files[name] = 100
                job.command_file_progress[name] = 100.0
                job.file_identities.setdefault(identity, set()).add(name)
                keys = (name,)
        else:
            descriptor = clean.split("->", 1)[0].strip()
            descriptor = re.sub(r"\s*(?:done!|failed!)\s*$", "", descriptor, flags=re.IGNORECASE)
            key = self._desc_key(descriptor)
            if key not in job.files:
                return
            job.files[key] = 100
            job.command_file_progress[key] = 100.0
            keys = (key,)
        for key in keys:
            job.files[key] = 100
            if key in job.command_file_progress:
                job.command_file_progress[key] = 100.0
            if job is self._selected_job():
                self._ensure_detail_file(key, 100)
        if keys:
            if job is self._selected_job():
                self._sync_filecount(job)
            self._update_job_progress(job)

    def _apply_progress_frame(self, job, clean):
        job.parser.feed(clean)
        if job.parser.percent is not None:
            job.command_pct = max(job.command_pct, job.parser.percent)
        spd = job.parser.speed
        if spd and ";" in spd:
            spd = spd.rsplit(";", 1)[-1].strip()
        if spd:
            job.speed = spd
        m = re.search(r"ETA[:：]?\s*([0-9][0-9hmsHMS.:]*)", clean)
        if m:
            job.eta = m.group(1)
        self._job_feed_file(job, clean)
        self._update_job_progress(job)

    @staticmethod
    def _desc_key(text):
        key = re.split(r"\s*(?:->|→)\s*", text.strip())[0].strip()
        if key.isdigit():
            key = "#" + key
        if len(key) > 46:
            key = key[:44] + "…"
        return key

    def _job_feed_file(self, job, clean):
        m = re.match(r"^(?P<name>.+?)\s+(?P<pct>\d+(?:\.\d+)?)%\s*\[", clean)
        if not m:
            return
        name = self._desc_key(m.group("name"))
        pct = int(float(m.group("pct")))
        if name not in job.files and len(job.files) >= 200:
            return
        job.files[name] = max(job.files.get(name, 0), pct)
        job.command_file_progress[name] = max(job.command_file_progress.get(name, 0.0), float(pct))
        identity_match = re.search(r"\((?P<peer>\d+)\):(?P<message>\d+)", clean)
        if identity_match:
            identity = (identity_match.group("peer"), identity_match.group("message"))
            job.file_identities.setdefault(identity, set()).add(name)
        if job is self._selected_job():
            self._ensure_detail_file(name, job.files[name])
            self._sync_filecount(job)

    def _update_job_progress(self, job):
        if job.status == "done":
            job.pct = 100
        elif 0 <= job.cur < len(job.stage_progress):
            if job.commands[job.cur][0] == "dl":
                if job.command_file_progress:
                    current = sum(job.command_file_progress.values()) / len(job.command_file_progress)
                else:
                    current = job.command_pct
                current = max(job.stage_progress[job.cur], min(99.0, current))
                job.stage_progress[job.cur] = current
            total_weight = sum(job.stage_weights)
            total = sum(pct * weight for pct, weight in zip(job.stage_progress, job.stage_weights)) / total_weight
            job.pct = min(99, max(job.pct, int(total)))
        self._set_row_pct(job)
        if job is self._selected_job():
            self._refresh_detail_progress(job)

    def _stop_download(self):
        for j in self._jobs:
            if j.runner is not None:
                j.runner.stop()
                j.runner = None
            if j.status in ("queued", "running"):
                j.status = "stopped"
                if j.qrow is not None:
                    j.qrow.set_status("stopped")
        self._update_ui_running(False)
        self._refresh_active_count()
        job = self._selected_job()
        if job is not None:
            self._show_detail(job)
        self._app_log.append("■ 下载已停止")
        self._append_log("■ 下载已停止")

    def _set_badge_breathing(self, on: bool):
        if not hasattr(self, "_badge_fx"):
            self._badge_fx = QGraphicsOpacityEffect(self._lbl_badge)
            self._lbl_badge.setGraphicsEffect(self._badge_fx)
            self._badge_anim = QVariantAnimation(self)
            self._badge_anim.setDuration(1600)
            self._badge_anim.setStartValue(1.0)
            self._badge_anim.setEndValue(0.55)
            self._badge_anim.setEasingCurve(QEasingCurve.InOutSine)
            self._badge_anim.setLoopCount(-1)
            self._badge_anim.valueChanged.connect(self._badge_fx.setOpacity)
        self._badge_anim.stop()
        if on:
            self._badge_anim.start()
        else:
            self._badge_fx.setOpacity(1.0)

    def _update_ui_running(self, running: bool):
        if not running:
            self._set_badge_breathing(False)
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
        self._app_log.append(text)
        self._append_log(text)

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
