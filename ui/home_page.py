# ui/home_page.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QListWidget, QListWidgetItem, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from utils.i18n import i18n
from utils.storage import storage


class HomePage(QWidget):
    start_project_requested = pyqtSignal()
    open_project_requested = pyqtSignal(str)  # folder_name
    view_report_requested = pyqtSignal(str)  # folder_name

    def __init__(self):
        super().__init__()
        self.init_ui()
        i18n.language_changed.connect(self.update_texts)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- 左侧: 历史项目列表 ---
        left_panel = QWidget()
        left_panel.setStyleSheet("background-color: #2c3e50; color: white;")
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)

        self.lbl_history = QLabel()
        self.lbl_history.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        left_layout.addWidget(self.lbl_history)

        self.list_projects = QListWidget()
        self.list_projects.setStyleSheet("""
            QListWidget { border: none; background: transparent; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #34495e; color: #bdc3c7; }
            QListWidget::item:selected { background-color: #3498db; color: white; }
            QListWidget::item:hover { background-color: #34495e; }
        """)
        self.list_projects.itemClicked.connect(self.on_project_selected)
        left_layout.addWidget(self.list_projects)

        # --- 右侧: 详情与操作区 ---
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #ecf0f1;")
        self.right_layout = QVBoxLayout(right_panel)
        self.right_layout.setContentsMargins(50, 50, 50, 50)

        # 顶部: 新建项目按钮
        self.btn_new = QPushButton()
        self.btn_new.setMinimumSize(200, 50)
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; border-radius: 6px; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        self.btn_new.clicked.connect(self.start_project_requested.emit)

        top_bar = QHBoxLayout()
        top_bar.addStretch()
        top_bar.addWidget(self.btn_new)
        self.right_layout.addLayout(top_bar)

        self.right_layout.addSpacing(40)

        # 项目详情卡片
        self.detail_container = QFrame()
        self.detail_container.setStyleSheet(
            "QFrame { background-color: white; border-radius: 10px; border: 1px solid #dcdcdc; }")
        self.detail_container.setVisible(False)  # 初始隐藏，选中项目后显示

        detail_layout = QVBoxLayout(self.detail_container)
        detail_layout.setContentsMargins(40, 40, 40, 40)

        # 1. 标题和时间
        self.lbl_proj_title = QLabel()
        self.lbl_proj_title.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
        self.lbl_proj_title.setStyleSheet("color: #2c3e50; border: none;")

        self.lbl_proj_time = QLabel()
        self.lbl_proj_time.setStyleSheet("color: #7f8c8d; font-size: 14px; border: none;")

        # 2. 按钮区域 (修复显示问题)
        action_layout = QHBoxLayout()
        action_layout.setSpacing(20)

        self.btn_continue = QPushButton("Continue")
        self.btn_report = QPushButton("Report")

        # 设置显式的最小尺寸，确保可见
        btn_base_style = """
            QPushButton { 
                padding: 10px 20px; 
                border-radius: 5px; 
                font-weight: bold; 
                font-size: 14px; 
                min-width: 120px;
                min-height: 20px;
            }
        """
        self.btn_continue.setStyleSheet(btn_base_style + "background-color: #3498db; color: white;")
        self.btn_report.setStyleSheet(btn_base_style + "background-color: #f39c12; color: white;")

        # 连接点击事件
        self.btn_continue.clicked.connect(self.on_continue_clicked)
        self.btn_report.clicked.connect(self.on_report_clicked)

        action_layout.addWidget(self.btn_continue)
        action_layout.addWidget(self.btn_report)
        action_layout.addStretch()  # 按钮靠左排列

        # 将组件添加到详情布局
        detail_layout.addWidget(self.lbl_proj_title)
        detail_layout.addSpacing(10)
        detail_layout.addWidget(self.lbl_proj_time)
        detail_layout.addSpacing(40)  # 增加标题和按钮的间距
        detail_layout.addLayout(action_layout)  # 【关键】确保此行存在
        detail_layout.addStretch()

        # 占位符 (未选择项目时显示)
        self.lbl_placeholder = QLabel()
        self.lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_placeholder.setStyleSheet("color: #95a5a6; font-size: 18px;")

        # 添加到右侧主布局
        self.right_layout.addWidget(self.detail_container, 1)
        self.right_layout.addWidget(self.lbl_placeholder, 1)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

        self.update_texts()
        self.refresh_list()

    def update_texts(self):
        self.lbl_history.setText(i18n.tr("lbl_history_list"))
        self.btn_new.setText(f"+ {i18n.tr('home_new_project')}")
        self.btn_continue.setText(f"▶ {i18n.tr('home_continue_match')}")
        self.btn_report.setText(f"📊 {i18n.tr('home_view_report')}")
        self.lbl_placeholder.setText(i18n.tr("msg_select_project"))

        # 如果当前已经选中了项目，刷新一下显示
        if self.detail_container.isVisible() and hasattr(self, 'current_project_data'):
            self.on_project_selected(self.list_projects.currentItem())

    def refresh_list(self):
        self.list_projects.clear()
        projects = storage.list_projects()
        for p in projects:
            item = QListWidgetItem()
            # 列表项显示两行：项目名 + 时间
            item.setText(f"{p['name']}\n{p['time']}")
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.list_projects.addItem(item)

    def on_project_selected(self, item):
        if not item: return
        data = item.data(Qt.ItemDataRole.UserRole)
        self.current_project_data = data

        self.lbl_placeholder.setVisible(False)
        self.detail_container.setVisible(True)

        self.lbl_proj_title.setText(data['name'])

        time_text = f"{i18n.tr('lbl_create_time')} {data['time']}"
        if data.get('updated'):
            time_text += f"  |  {i18n.tr('lbl_last_update')} {data['updated']}"
        self.lbl_proj_time.setText(time_text)

    def on_continue_clicked(self):
        if hasattr(self, 'current_project_data'):
            folder = self.current_project_data['folder']
            self.open_project_requested.emit(folder)

    def on_report_clicked(self):
        if hasattr(self, 'current_project_data'):
            folder = self.current_project_data['folder']
            self.view_report_requested.emit(folder)