# ui/main_window.py
import asyncio
from PyQt6.QtWidgets import (QMainWindow, QWidget, QGridLayout, QStackedWidget,
                             QVBoxLayout, QHBoxLayout, QPushButton, QLabel)
from PyQt6.QtGui import QAction, QActionGroup, QFont
from PyQt6.QtCore import Qt, QTimer  # 【关键】导入 QTimer
from utils.i18n import i18n
from ui.home_page import HomePage
from ui.setup_wizard import SetupWizard
from ui.score_panel import ScorePanel
from ui.window_selector import WindowSelectorDialog
from ui.overlay_window import OverlayWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1000, 700)

        # 1. 数据初始化
        self.referees = []
        self.project_name = ""
        self.overlay = None
        self.selector_dialog = None

        # 2. 堆叠窗口容器
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # 3. 菜单与文本
        self.init_menu()
        self.update_texts()
        i18n.language_changed.connect(self.update_texts)

        # 4. 页面初始化
        # Page 0: Home
        self.home_page = HomePage()
        self.home_page.start_project_requested.connect(self.go_to_wizard)
        self.stack.addWidget(self.home_page)

        # Page 1: Wizard
        self.wizard_page = SetupWizard()
        self.wizard_page.setup_finished.connect(self.on_setup_finished)
        self.wizard_page.back_to_home_requested.connect(self.go_to_home)
        self.stack.addWidget(self.wizard_page)

        # Page 2: Dashboard (作为永久容器，不再删除重建，而是清空内容)
        self.dashboard_page = QWidget()
        self.stack.addWidget(self.dashboard_page)

        self.stack.setCurrentIndex(0)

    # ... (init_menu, update_texts, go_to_home, go_to_wizard 保持不变) ...
    # ... 请直接复制之前的代码 ...

    def init_menu(self):
        self.menu_bar = self.menuBar()
        self.menu_settings = self.menu_bar.addMenu("Settings")
        self.menu_lang = self.menu_settings.addMenu("Language")
        lang_group = QActionGroup(self)

        self.act_zh = QAction("简体中文", self, checkable=True)
        self.act_zh.triggered.connect(lambda: i18n.set_language("zh"))
        self.menu_lang.addAction(self.act_zh)
        lang_group.addAction(self.act_zh)

        self.act_en = QAction("English", self, checkable=True)
        self.act_en.triggered.connect(lambda: i18n.set_language("en"))
        self.menu_lang.addAction(self.act_en)
        lang_group.addAction(self.act_en)

        if i18n.current_lang == "zh":
            self.act_zh.setChecked(True)
        else:
            self.act_en.setChecked(True)

        self.menu_project = self.menu_bar.addMenu("Project")
        self.menu_help = self.menu_bar.addMenu("Help")

    def update_texts(self):
        if self.stack.currentIndex() == 2 and self.project_name:
            self.setWindowTitle(f"{i18n.tr('app_title')} - {self.project_name}")
        else:
            self.setWindowTitle(i18n.tr("app_title"))

        self.menu_settings.setTitle(i18n.tr("menu_settings"))
        self.menu_lang.setTitle(i18n.tr("menu_language"))
        self.menu_project.setTitle(i18n.tr("menu_project"))
        self.menu_help.setTitle(i18n.tr("menu_help"))

        if self.stack.currentIndex() == 2:
            self.setup_dashboard()

    def go_to_home(self):
        self.close_overlay_if_active()
        if self.stack.currentIndex() == 2:
            self.disconnect_all_devices()
        self.stack.setCurrentIndex(0)
        self.project_name = ""
        self.update_texts()

    def go_to_wizard(self):
        self.stack.setCurrentIndex(1)

    # --- 核心修复区 ---

    def on_setup_finished(self, project_name, referees):
        self.project_name = project_name
        self.referees = referees

        self.update_texts()
        self.setup_dashboard()
        self.stack.setCurrentIndex(2)

        # 【核心修复】延迟 500ms 连接，防止与停止扫描的后台任务冲突导致崩溃
        QTimer.singleShot(500, self.connect_devices)

    def setup_dashboard(self):
        """安全重建看板布局"""
        # 1. 安全清空布局，而不是删除 Widget 本身
        if self.dashboard_page.layout():
            # 这是一个高效清空布局的小技巧：将布局重新设置给一个临时 Widget
            QWidget().setLayout(self.dashboard_page.layout())

        # 2. 重新创建布局
        main_layout = QVBoxLayout(self.dashboard_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Bar ---
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: #ecf0f1; border-bottom: 1px solid #bdc3c7;")
        top_bar.setFixedHeight(60)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)

        self.btn_back_dash = QPushButton(i18n.tr("btn_stop_match"))
        self.btn_back_dash.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.btn_back_dash.clicked.connect(self.go_to_home)

        self.btn_overlay = QPushButton()
        self.update_overlay_btn_style()
        self.btn_overlay.clicked.connect(self.toggle_overlay)

        lbl_title = QLabel(f"{i18n.tr('dash_title')} - {self.project_name}")
        lbl_title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #2c3e50;")

        top_layout.addWidget(self.btn_back_dash)
        top_layout.addSpacing(15)
        top_layout.addWidget(self.btn_overlay)
        top_layout.addStretch()
        top_layout.addWidget(lbl_title)
        top_layout.addStretch()

        main_layout.addWidget(top_bar)

        # --- Grid ---
        content_widget = QWidget()
        grid_layout = QGridLayout(content_widget)
        grid_layout.setContentsMargins(30, 30, 30, 30)
        grid_layout.setSpacing(30)

        row, col = 0, 0
        count = len(self.referees)
        max_cols = 1 if count == 1 else (2 if count <= 4 else 3)

        for ref in self.referees:
            panel = ScorePanel(ref)
            grid_layout.addWidget(panel, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        content_wrapper = QVBoxLayout()
        content_wrapper.addWidget(content_widget)
        content_wrapper.addStretch()
        main_layout.addLayout(content_wrapper)

    # --- 悬浮窗逻辑 ---

    def update_overlay_btn_style(self):
        if self.overlay:
            self.btn_overlay.setText("❌ 关闭悬浮窗")
            self.btn_overlay.setStyleSheet("""
                QPushButton { background-color: #f39c12; color: white; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
                QPushButton:hover { background-color: #d68910; }
            """)
        else:
            self.btn_overlay.setText("📺 " + i18n.tr("btn_overlay"))
            self.btn_overlay.setStyleSheet("""
                QPushButton { background-color: #3498db; color: white; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
                QPushButton:hover { background-color: #2980b9; }
            """)

    def toggle_overlay(self):
        if self.overlay:
            self.close_overlay_if_active()
        else:
            self.start_overlay_flow()

    def start_overlay_flow(self):
        if not self.selector_dialog:
            self.selector_dialog = WindowSelectorDialog(self)
            self.selector_dialog.window_selected.connect(self.enter_overlay_mode)
        self.selector_dialog.show()

    def enter_overlay_mode(self, target_window):
        self.overlay = OverlayWindow(target_window, self.referees)

        # 连接新的关闭信号
        self.overlay.closed_signal.connect(self.on_overlay_closed_passive)

        self.overlay.show()
        self.update_overlay_btn_style()

    def close_overlay_if_active(self):
        if self.overlay:
            self.overlay.close()
            self.overlay = None
            self.update_overlay_btn_style()

    def on_overlay_closed_passive(self):
        self.overlay = None
        self.update_overlay_btn_style()

    # --- 连接管理 ---

    def connect_devices(self):
        for ref in self.referees:
            if ref.primary_device:
                asyncio.create_task(ref.primary_device.connect())
            if ref.secondary_device:
                asyncio.create_task(ref.secondary_device.connect())

    def disconnect_all_devices(self):
        if not self.referees: return
        for ref in self.referees:
            if ref.primary_device:
                asyncio.create_task(ref.primary_device.disconnect())
            if ref.secondary_device:
                asyncio.create_task(ref.secondary_device.disconnect())
        self.referees = []