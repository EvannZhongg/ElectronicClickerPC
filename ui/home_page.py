# ui/home_page.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from utils.i18n import i18n


class HomePage(QWidget):
    start_project_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        i18n.language_changed.connect(self.update_texts)

    def init_ui(self):
        main_layout = QVBoxLayout()
        # 增加一些边距，让内容不要贴边
        main_layout.setContentsMargins(50, 100, 50, 100)
        main_layout.setSpacing(40)

        # 1. 大标题 (显示在中间偏上)
        self.lbl_welcome = QLabel()
        self.lbl_welcome.setFont(QFont("Microsoft YaHei", 28, QFont.Weight.Bold))
        self.lbl_welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_welcome.setStyleSheet("color: #333;")

        # 2. 巨大的新建项目按钮
        self.btn_new_project = QPushButton()
        self.btn_new_project.setMinimumHeight(80)
        self.btn_new_project.setCursor(Qt.CursorShape.PointingHandCursor)
        # 美化按钮样式
        self.btn_new_project.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-size: 22px;
                border-radius: 10px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                margin-top: 2px; /* 简单的按下效果 */
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
        """)
        self.btn_new_project.clicked.connect(self.start_project_requested.emit)

        # 布局填充： 弹簧 - 标题 - 按钮 - 弹簧
        main_layout.addStretch(1)
        main_layout.addWidget(self.lbl_welcome)
        main_layout.addWidget(self.btn_new_project)
        main_layout.addStretch(2)  # 下方留白多一点，视觉重心偏上

        self.setLayout(main_layout)
        self.update_texts()

    def update_texts(self):
        self.lbl_welcome.setText(i18n.tr("app_title"))
        self.btn_new_project.setText(i18n.tr("home_new_project"))