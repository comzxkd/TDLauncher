# main.py
import sys
import os

# 确保能找到 app 包内的模块
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TDLauncher")

    # 图标
    icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
