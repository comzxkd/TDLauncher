"""离屏渲染 TDLauncher 主窗口为 PNG，用于验证界面。

用法：python tools/preview_ui.py
输出：tools/preview/preview-1280x720.png、preview-2560x1440.png

要点：
- 用 WA_DontShowOnScreen（真实字体栈、不弹出窗口），不要用 QT_QPA_PLATFORM=offscreen（中文会变方块）。
- 只做界面渲染，不调用 _start_download，因此不会改写 config.json。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(os.path.dirname(HERE), "app")
sys.path.insert(0, APP)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import main_window as mw

# 避免弹窗/子进程阻塞渲染
mw.QMessageBox.warning = staticmethod(lambda *a, **k: None)
mw.QMessageBox.information = staticmethod(lambda *a, **k: None)
mw.MainWindow._check_login_status = lambda self: None


def seed(self):
    """填入示例数据，便于查看真实观感（仅作用于预览）。"""
    self._txt_links.setPlainText("https://t.me/photolang/50063\nhttps://t.me/photolang/50064\nhttps://t.me/photolang/50065")
    self._on_links_changed()
    self._lbl_path.setText("E:/.../vendor/tdl.exe v0.20.3")

    names = ["#50063 @photolang", "#50064 @photolang", "#50062 @photolang", "#50061 @photolang", "#50060 @photolang"]
    done = [66, 40, 100, 0, 0]
    self._clear_layout(self._queue_box, self._queue_rows)
    self._jobs = []
    rows = []
    for i, n in enumerate(names):
        r = self._add_queue_row(n, i)
        r.set_status("done" if done[i] >= 100 else "running")
        r.set_pct(done[i])
        rows.append(r)
    self._sel = 0
    for i, r in enumerate(rows):
        r.set_active(i == 0)
    self._lbl_qcount.setText("2/5 活动")

    self._clear_layout(self._files_box, self._detail_file_rows)
    self._detail_files = {}
    for n, p in [("media_001.jpg", 100), ("media_002.jpg", 100), ("media_003.jpg", 100),
                 ("media_004.mp4", 100), ("media_005.mp4", 100), ("media_006.mp4", 100),
                 ("media_007.mp4", 62), ("media_008.mp4", 0), ("media_009.png", 0)]:
        self._ensure_detail_file(n, p)

    self._lbl_current.setText("#50063 @photolang")
    self._lbl_url.setText("https://t.me/photolang/50063")
    self._lbl_badge.setText("下载中")
    self._lbl_bigpct.setText("62")
    self._cells.setValue(62)
    self._lbl_speed.setText("4.2 MB/s")
    self._lbl_eta.setText("00:48")
    self._lbl_totalcount.setText("6/9")
    self._lbl_status.setText("任务: 6/10")
    self._lbl_sstate.setText("状态: 下载中")
    self._txt_output.setPlainText(
        "[00:12:04] tdl 已登录 · Takeout 会话就绪\n"
        "[00:12:05] ▸ 解析 3 个链接 …\n"
        "[00:12:06] ✓ #50062 完成 · 24 个文件 · 用时 01:12\n"
        "[00:12:07] ▸ #50063 开始下载 · 8 线程\n"
        "[00:12:09] ✓ media_006.mp4 完成"
    )


def main():
    app = QApplication(sys.argv)
    w = mw.MainWindow()
    w.setAttribute(Qt.WA_DontShowOnScreen, True)
    seed(w)
    w.show()

    out = os.path.join(HERE, "preview")
    os.makedirs(out, exist_ok=True)
    for tag, (ww, hh) in {"1280x720": (1280, 720), "2560x1440": (2560, 1440)}.items():
        w.resize(ww, hh)
        for _ in range(8):
            app.processEvents()
        pm = w.grab()
        path = os.path.join(out, f"preview-{tag}.png")
        pm.save(path)
        print("saved", path)
    print("done")


if __name__ == "__main__":
    main()
