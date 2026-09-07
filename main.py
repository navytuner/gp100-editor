import sys

from PySide6.QtWidgets import QApplication

from mainwindow import GP100Editor
from style import GLOBAL_CSS, apply_dark_palette


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_CSS)
    apply_dark_palette(app)

    win = GP100Editor()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
