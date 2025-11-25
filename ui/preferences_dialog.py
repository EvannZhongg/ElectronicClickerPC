# ui/preferences_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTabWidget, QWidget, QKeySequenceEdit, QFormLayout)
from PyQt6.QtGui import QKeySequence
from utils.app_settings import app_settings
from utils.i18n import i18n


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("prefs_title"))
        self.resize(450, 300)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. 选项卡控件
        self.tabs = QTabWidget()

        # --- 快捷键页签 ---
        self.tab_shortcuts = QWidget()
        self.init_shortcuts_tab()
        self.tabs.addTab(self.tab_shortcuts, i18n.tr("tab_shortcuts"))

        # (未来可以在这里添加更多页签)

        main_layout.addWidget(self.tabs)

        # 2. 底部按钮区 (保存/取消)
        btn_layout = QHBoxLayout()
        btn_save = QPushButton(i18n.tr("btn_save"))
        btn_cancel = QPushButton(i18n.tr("btn_cancel"))

        # 美化保存按钮
        btn_save.setStyleSheet(
            "background-color: #3498db; color: white; font-weight: bold; border-radius: 4px; padding: 6px 16px;")

        btn_save.clicked.connect(self.save_settings)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)

        main_layout.addLayout(btn_layout)

    def init_shortcuts_tab(self):
        layout = QFormLayout(self.tab_shortcuts)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 全局重置快捷键设置
        current_key = app_settings.get("reset_shortcut")
        # QKeySequenceEdit 是 PyQt 专门用于录入快捷键的控件
        self.key_editor_reset = QKeySequenceEdit(QKeySequence(current_key))

        layout.addRow(QLabel(i18n.tr("lbl_reset_all_shortcut")), self.key_editor_reset)

    def save_settings(self):
        """保存所有设置项并关闭对话框"""
        # 1. 获取快捷键输入
        new_key_seq = self.key_editor_reset.keySequence()
        # 转换为本地可读的字符串 (例如 "Ctrl+G")
        new_key_str = new_key_seq.toString(QKeySequence.SequenceFormat.NativeText)

        if new_key_str:
            app_settings.set("reset_shortcut", new_key_str)

        # 保存成功，返回 Accepted 状态
        self.accept()