# ui/window_selector.py
import pygetwindow as gw
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QPushButton,
                             QLabel, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import pyqtSignal, Qt
from utils.i18n import i18n


class WindowSelectorDialog(QDialog):
    # 改用信号传递选择结果
    window_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("title_select_window"))
        self.resize(400, 500)

        # 【关键】设置为模态，但不要用 exec()
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(i18n.tr("lbl_window_list")))

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.list_widget)

        # 获取窗口列表
        try:
            windows = gw.getAllTitles()
            my_title = self.parent().windowTitle() if self.parent() else ""
            for title in windows:
                if title.strip() and title != my_title:
                    self.list_widget.addItem(title)
        except Exception:
            pass

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton(i18n.tr("btn_back"))
        btn_cancel.clicked.connect(self.close)  # 直接关闭

        btn_ok = QPushButton(i18n.tr("btn_confirm_overlay"))
        btn_ok.clicked.connect(self.accept_selection)
        btn_ok.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def accept_selection(self):
        current_item = self.list_widget.currentItem()
        if not current_item:
            return

        title = current_item.text()
        try:
            wins = gw.getWindowsWithTitle(title)
            if wins:
                # 发射信号并关闭
                self.window_selected.emit(wins[0])
                self.close()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))