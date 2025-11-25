# ui/main_window.py
import asyncio
from PyQt6.QtWidgets import (QMainWindow, QWidget, QGridLayout, QStackedWidget,
                             QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
                             QDialog)  # 移除 QKeySequenceEdit 等未使用的导入
from PyQt6.QtGui import QAction, QActionGroup, QFont, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QTimer
from utils.i18n import i18n
from utils.app_settings import app_settings
from ui.preferences_dialog import PreferencesDialog
from ui.home_page import HomePage
from ui.setup_wizard import SetupWizard
from ui.score_panel import ScorePanel
from ui.window_selector import WindowSelectorDialog
from ui.overlay_window import OverlayWindow
from utils.storage import storage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1000, 700)

        # 1. 数据初始化
        self.referees = []
        self.project_name = ""
        self.overlay = None
        self.selector_dialog = None
        self.prefs_dialog = None  # 【新增】持有对话框引用，防止被垃圾回收

        # --- 初始化全局快捷键 ---
        saved_shortcut = app_settings.get("reset_shortcut")
        self.reset_shortcut = QShortcut(QKeySequence(saved_shortcut), self)
        self.reset_shortcut.activated.connect(self.confirm_reset_all)

        # 2. 堆叠窗口容器
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # 3. 菜单与文本
        self.init_menu()
        self.update_texts()
        i18n.language_changed.connect(self.update_texts)

        # 4. 页面初始化
        self.home_page = HomePage()
        self.home_page.start_project_requested.connect(self.go_to_wizard)
        self.stack.addWidget(self.home_page)

        self.wizard_page = SetupWizard()
        self.wizard_page.setup_finished.connect(self.on_setup_finished)
        self.wizard_page.back_to_home_requested.connect(self.go_to_home)
        self.stack.addWidget(self.wizard_page)

        self.dashboard_page = QWidget()
        self.stack.addWidget(self.dashboard_page)

        self.stack.setCurrentIndex(0)

    def init_menu(self):
        self.menu_bar = self.menuBar()
        self.menu_settings = self.menu_bar.addMenu("Settings")

        # --- 语言菜单 ---
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

        current_lang = app_settings.get("language")
        if current_lang == "zh":
            self.act_zh.setChecked(True)
        else:
            self.act_en.setChecked(True)

        self.menu_settings.addSeparator()

        # --- 偏好设置菜单项 ---
        self.act_preferences = QAction("Preferences", self)
        self.act_preferences.triggered.connect(self.open_preferences_dialog)
        self.menu_settings.addAction(self.act_preferences)

        self.menu_project = self.menu_bar.addMenu("Project")
        self.menu_help = self.menu_bar.addMenu("Help")

    def update_texts(self):
        if self.stack.currentIndex() == 2 and self.project_name:
            self.setWindowTitle(f"{i18n.tr('app_title')} - {self.project_name}")
        else:
            self.setWindowTitle(i18n.tr("app_title"))

        self.menu_settings.setTitle(i18n.tr("menu_settings"))
        self.menu_lang.setTitle(i18n.tr("menu_language"))
        self.act_preferences.setText(i18n.tr("menu_preferences"))
        self.menu_project.setTitle(i18n.tr("menu_project"))
        self.menu_help.setTitle(i18n.tr("menu_help"))

        if self.stack.currentIndex() == 2:
            self.setup_dashboard()

    # --- 【关键修复】使用非阻塞方式打开对话框 ---
    def open_preferences_dialog(self):
        # 创建对话框并设为 WindowModal (阻塞用户操作主窗口，但不阻塞代码执行)
        self.prefs_dialog = PreferencesDialog(self)
        self.prefs_dialog.setWindowModality(Qt.WindowModality.WindowModal)

        # 连接关闭信号，处理保存后的逻辑
        self.prefs_dialog.finished.connect(self.on_preferences_closed)

        # 使用 open() 而不是 exec()，避免卡死 asyncio 事件循环
        self.prefs_dialog.open()

    def on_preferences_closed(self, result):
        """当偏好设置对话框关闭时调用"""
        if result == QDialog.DialogCode.Accepted:
            # 重新读取配置并应用
            new_shortcut = app_settings.get("reset_shortcut")
            self.reset_shortcut.setKey(QKeySequence(new_shortcut))
            self.update_texts()

        # 清理引用
        self.prefs_dialog = None

    # --- 页面跳转与蓝牙生命周期管理 ---

    def go_to_home(self):
        """返回首页，并确保断开所有连接"""
        self.close_overlay_if_active()

        # 只有在看板页面(Page 2)才需要执行断开连接
        # 向导页面(Page 1)由向导内部控制停止扫描
        if self.stack.currentIndex() == 2:
            self.disconnect_all_devices()

        self.stack.setCurrentIndex(0)
        self.project_name = ""
        self.update_texts()

    def go_to_wizard(self):
        self.wizard_page.reset()  # 【关键】进入向导前重置状态
        self.stack.setCurrentIndex(1)

    def on_setup_finished(self, project_name, referees):
        self.project_name = project_name
        self.referees = referees
        try:
            referees_config = []
            for ref in referees:
                pri_addr = ref.primary_device.ble_device.address if ref.primary_device else "N/A"
                sec_addr = "N/A"
                if ref.secondary_device:
                    sec_addr = ref.secondary_device.ble_device.address

                ref_data = {
                    "index": ref.index,
                    "name": ref.name,
                    "mode": ref.mode,
                    "primary_device": pri_addr,
                    "secondary_device": sec_addr
                }
                referees_config.append(ref_data)

            storage.create_project(project_name, referees_config)
        except Exception as e:
            print(f"Storage Init Failed: {e}")

        self.update_texts()
        self.setup_dashboard()
        self.stack.setCurrentIndex(2)

        # 进入看板后才开始连接
        QTimer.singleShot(500, self.connect_devices)

    def setup_dashboard(self):
        if self.dashboard_page.layout():
            QWidget().setLayout(self.dashboard_page.layout())

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
            QPushButton { background-color: #95a5a6; color: white; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        self.btn_back_dash.clicked.connect(self.go_to_home)

        self.btn_overlay = QPushButton()
        self.update_overlay_btn_style()
        self.btn_overlay.clicked.connect(self.toggle_overlay)

        shortcut_text = app_settings.get('reset_shortcut')
        self.btn_reset_all = QPushButton(f"⚠ RESET ALL ({shortcut_text})")
        self.btn_reset_all.setStyleSheet("""
            QPushButton { 
                background-color: #c0392b; 
                color: white; 
                border-radius: 4px; 
                padding: 8px 16px; 
                font-weight: bold; 
            }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        self.btn_reset_all.clicked.connect(self.confirm_reset_all)

        lbl_title = QLabel(f"{i18n.tr('dash_title')} - {self.project_name}")
        lbl_title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #2c3e50;")

        top_layout.addWidget(self.btn_back_dash)
        top_layout.addSpacing(15)
        top_layout.addWidget(self.btn_overlay)

        if self.referees:
            top_layout.addSpacing(15)
            top_layout.addWidget(self.btn_reset_all)

        top_layout.addStretch()
        top_layout.addWidget(lbl_title)
        top_layout.addStretch()

        main_layout.addWidget(top_bar)

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

    def confirm_reset_all(self):
        reply = QMessageBox.question(
            self,
            "Confirm Reset All",
            "Are you sure you want to RESET ZERO for ALL devices?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            print("Resetting ALL referees...")
            for ref in self.referees:
                ref.request_reset()

    # --- Overlay Logic ---

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
        """仅在进入看板后被调用，建立连接"""
        for ref in self.referees:
            if ref.primary_device:
                asyncio.create_task(ref.primary_device.connect())
            if ref.secondary_device:
                asyncio.create_task(ref.secondary_device.connect())

    def disconnect_all_devices(self):
        """离开看板时调用，断开所有连接"""
        if not self.referees: return
        print("Disconnecting all devices...")
        for ref in self.referees:
            if ref.primary_device:
                asyncio.create_task(ref.primary_device.disconnect())
            if ref.secondary_device:
                asyncio.create_task(ref.secondary_device.disconnect())
        # 注意：这里不清空 self.referees，因为 wizard 需要保留数据，
        # 但如果是 go_to_home，会清空 ref 列表。