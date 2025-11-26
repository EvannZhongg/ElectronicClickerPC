# ui/main_window.py
import asyncio
from PyQt6.QtWidgets import (QMainWindow, QWidget, QGridLayout, QStackedWidget,
                             QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
                             QDialog, QComboBox, QCheckBox, QFrame)
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
        self.resize(1000, 750)
        self.setStyleSheet("QMainWindow { background-color: #2b2b2b; }")

        # 1. 数据初始化
        self.referees = []
        self.project_name = ""
        self.overlay = None
        self.selector_dialog = None
        self.prefs_dialog = None

        self.tournament_data = {}
        self.active_group_name = None
        self.contestants = []
        self.current_idx = -1

        # 内存中维护已打分（即接收过 BLE 数据）的选手集合
        self.scored_contestants = set()

        # 全局快捷键
        saved_shortcut = app_settings.get("reset_shortcut")
        self.reset_shortcut = QShortcut(QKeySequence(saved_shortcut), self)
        self.reset_shortcut.activated.connect(self.confirm_reset_all)

        # 2. 堆叠窗口
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # 3. 菜单
        self.init_menu()
        i18n.language_changed.connect(self.update_texts)

        # 4. 页面
        self.home_page = HomePage()
        self.home_page.start_project_requested.connect(self.start_new_project)
        self.home_page.open_project_requested.connect(self.open_existing_project)
        self.stack.addWidget(self.home_page)  # Index 0

        self.wizard_page = SetupWizard()
        self.wizard_page.setup_finished.connect(self.on_setup_finished)
        self.wizard_page.back_to_home_requested.connect(self.go_to_home)
        self.stack.addWidget(self.wizard_page)  # Index 1

        self.dashboard_page = QWidget()
        self.stack.addWidget(self.dashboard_page)  # Index 2

        self.stack.setCurrentIndex(0)
        self.update_texts()

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
        current_lang = app_settings.get("language")
        if current_lang == "zh":
            self.act_zh.setChecked(True)
        else:
            self.act_en.setChecked(True)
        self.menu_settings.addSeparator()
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
        if self.stack.currentIndex() == 2 and hasattr(self, 'lbl_title_dash'):
            self.lbl_title_dash.setText(f"{i18n.tr('dash_title')} - {self.project_name}")
            self.btn_back_dash.setText(i18n.tr("btn_stop_match"))
            self.chk_auto_next.setText(i18n.tr("chk_auto_next"))
            self.update_overlay_btn_style()

    def open_preferences_dialog(self):
        self.prefs_dialog = PreferencesDialog(self)
        self.prefs_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.prefs_dialog.finished.connect(self.on_preferences_closed)
        self.prefs_dialog.open()

    def on_preferences_closed(self, result):
        if result == QDialog.DialogCode.Accepted:
            new_shortcut = app_settings.get("reset_shortcut")
            self.reset_shortcut.setKey(QKeySequence(new_shortcut))
            if hasattr(self, 'btn_reset_all'):
                self.btn_reset_all.setText(f"⚠ RESET ALL ({new_shortcut})")
        self.prefs_dialog = None

    def start_new_project(self):
        storage.current_project_path = None
        self.scored_contestants.clear()
        self.wizard_page.reset()
        self.stack.setCurrentIndex(1)
        self.go_to_wizard_page1()

    def open_existing_project(self, folder_name):
        storage.set_current_project(folder_name)
        data = storage.load_project_config(folder_name)
        if data:
            self.wizard_page.restore_state(data)
            self.stack.setCurrentIndex(1)
            self.go_to_wizard_page1()
        else:
            QMessageBox.warning(self, "Error", "Failed to load project config.")

    def go_to_home(self):
        self.stack.setCurrentIndex(0)
        self.project_name = ""
        self.update_texts()

    def go_to_wizard_page1(self):
        self.wizard_page.stack.setCurrentIndex(0)
        self.wizard_page.lbl_title.setText(i18n.tr("wiz_p1_title"))

    def back_from_dashboard(self):
        self.close_overlay_if_active()
        self.disconnect_all_devices()
        self.stack.setCurrentIndex(1)
        self.wizard_page.stack.setCurrentIndex(1)
        self.wizard_page.lbl_title.setText(i18n.tr("wiz_p2_title"))
        self.wizard_page.start_scan()

    def on_setup_finished(self, project_name, referees, tournament_data):
        self.project_name = project_name
        self.referees = referees
        self.tournament_data = tournament_data

        self.active_group_name = tournament_data.get("active_group")
        if self.active_group_name and self.active_group_name in tournament_data["groups"]:
            self.contestants = tournament_data["groups"][self.active_group_name]
        else:
            self.contestants = []

        self.current_idx = -1

        try:
            referees_config = []
            for ref in referees:
                pri_addr = ref.primary_device.ble_device.address if ref.primary_device else "N/A"
                sec_addr = "N/A"
                if ref.secondary_device:
                    sec_addr = ref.secondary_device.ble_device.address
                ref_data = {"index": ref.index, "name": ref.name, "mode": ref.mode, "primary_device": pri_addr,
                            "secondary_device": sec_addr}
                referees_config.append(ref_data)

            if not storage.current_project_path:
                storage.create_project(project_name, referees_config, tournament_data)
                self.scored_contestants.clear()
            else:
                storage.update_project_config(project_name, referees_config, tournament_data)
                self.scored_contestants = storage.get_existing_contestants()

        except Exception as e:
            print(f"Storage Init Failed: {e}")

        self.setup_dashboard()

        initial_idx = 0
        found_unscored = False
        if self.contestants:
            for i, name in enumerate(self.contestants):
                if name not in self.scored_contestants:
                    initial_idx = i
                    found_unscored = True
                    break

            if not found_unscored and len(self.contestants) > 0:
                QMessageBox.warning(self, i18n.tr("title_warning"), i18n.tr("msg_all_contestants_scored"))

        self.load_contestant(initial_idx)
        self.update_texts()
        self.stack.setCurrentIndex(2)
        QTimer.singleShot(500, self.connect_devices)

    def setup_dashboard(self):
        if self.dashboard_page.layout():
            QWidget().setLayout(self.dashboard_page.layout())

        main_layout = QVBoxLayout(self.dashboard_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Bar
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: #2c3e50; border-bottom: 1px solid #1a252f;")
        top_bar.setFixedHeight(60)
        top_layout = QHBoxLayout(top_bar)

        self.btn_back_dash = QPushButton(i18n.tr("btn_stop_match"))
        self.btn_back_dash.setStyleSheet("""
            QPushButton { background-color: #7f8c8d; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #95a5a6; }
        """)
        self.btn_back_dash.clicked.connect(self.back_from_dashboard)

        self.btn_overlay = QPushButton()
        self.update_overlay_btn_style()
        self.btn_overlay.clicked.connect(self.toggle_overlay)

        self.lbl_title_dash = QLabel(f"{i18n.tr('dash_title')} - {self.project_name}")
        self.lbl_title_dash.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self.lbl_title_dash.setStyleSheet("color: #ecf0f1; border: none;")

        top_layout.addWidget(self.btn_back_dash)
        top_layout.addSpacing(15)
        top_layout.addWidget(self.btn_overlay)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_title_dash)
        top_layout.addStretch()
        main_layout.addWidget(top_bar)

        # Control Bar
        control_bar = QFrame()
        control_bar.setStyleSheet("background-color: #34495e; border-bottom: 1px solid #2c3e50;")
        control_bar.setFixedHeight(70)
        ctrl_layout = QHBoxLayout(control_bar)
        ctrl_layout.setContentsMargins(20, 10, 20, 10)

        lbl_grp_info = QLabel(f"{i18n.tr('lbl_curr_group')}: {self.active_group_name or i18n.tr('val_free_mode')}")
        lbl_grp_info.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        lbl_grp_info.setStyleSheet("color: #bdc3c7; margin-right: 20px; border: none;")

        btn_style = """
            QPushButton { background-color: #2980b9; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #3498db; }
            QPushButton:disabled { background-color: #555; color: #aaa; }
        """

        self.btn_prev = QPushButton(i18n.tr("btn_prev_player"))
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.clicked.connect(lambda: self.switch_contestant(-1))

        self.combo_players = QComboBox()
        self.combo_players.setMinimumWidth(250)
        self.combo_players.setMinimumHeight(30)
        self.combo_players.addItems(self.contestants)
        self.combo_players.setStyleSheet("""
            QComboBox { 
                background-color: #ecf0f1; color: #2c3e50; border-radius: 4px; padding: 5px; font-size: 14px; font-weight: bold; 
            }
            QComboBox::drop-down { border: none; }
        """)
        self.combo_players.activated.connect(self.jump_to_contestant)

        self.btn_next = QPushButton(i18n.tr("btn_next_player"))
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.clicked.connect(lambda: self.switch_contestant(1))

        self.chk_auto_next = QPushButton(i18n.tr("chk_auto_next"))
        self.chk_auto_next.setCheckable(True)
        self.chk_auto_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_auto_next.setStyleSheet("""
            QPushButton { 
                background-color: #7f8c8d; 
                color: #ecf0f1; 
                border-radius: 4px; 
                padding: 6px 12px; 
                font-weight: bold; 
                margin-left: 15px;
                text-align: center;
            }
            QPushButton:checked {
                background-color: #2ecc71; 
                color: white;
                border: 1px solid #27ae60;
            }
            QPushButton:hover {
                border: 1px solid #bdc3c7;
            }
        """)

        has_list = len(self.contestants) > 0
        self.btn_prev.setEnabled(has_list)
        self.btn_next.setEnabled(has_list)
        self.combo_players.setEnabled(has_list)
        self.chk_auto_next.setEnabled(has_list)
        self.chk_auto_next.setChecked(has_list)

        shortcut_text = app_settings.get('reset_shortcut')
        self.btn_reset_all = QPushButton(f"⚠ RESET ALL ({shortcut_text})")
        self.btn_reset_all.setStyleSheet("""
            QPushButton { background-color: #c0392b; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px; font-size: 12px;}
            QPushButton:hover { background-color: #e74c3c; }
        """)
        self.btn_reset_all.clicked.connect(self.confirm_reset_all)

        ctrl_layout.addWidget(lbl_grp_info)
        ctrl_layout.addWidget(self.btn_prev)
        ctrl_layout.addWidget(self.combo_players)
        ctrl_layout.addWidget(self.btn_next)
        ctrl_layout.addWidget(self.chk_auto_next)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_reset_all)

        main_layout.addWidget(control_bar)

        # Score Panels
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        grid_layout = QGridLayout(content_widget)
        grid_layout.setContentsMargins(40, 40, 40, 40)
        grid_layout.setSpacing(40)

        row, col = 0, 0
        count = len(self.referees)
        max_cols = 1 if count == 1 else (2 if count <= 4 else 3)
        for ref in self.referees:
            panel = ScorePanel(ref)
            grid_layout.addWidget(panel, row, col)
            ref.score_updated.connect(self.on_score_received_for_tracking)
            col += 1
            if col >= max_cols: col = 0; row += 1
        main_layout.addWidget(content_widget)
        main_layout.addStretch()

    def on_score_received_for_tracking(self):
        if self.contestants and 0 <= self.current_idx < len(self.contestants):
            current_name = self.contestants[self.current_idx]
            if current_name not in self.scored_contestants:
                print(f"Marking {current_name} as scored.")
                self.scored_contestants.add(current_name)

    def load_contestant(self, idx, force=False):
        """
        加载指定索引的选手，包含重复检查和设备重置。
        """
        if not self.contestants: return

        # 确保索引合法
        if 0 <= idx < len(self.contestants):
            target_name = self.contestants[idx]

            # 1. 检查是否重复打分 (非强制加载且目标已在记录中)
            # 注意：idx != self.current_idx 判断是防止点击“当前人”也触发弹窗
            # 但初始化时 current_idx = -1，所以如果第0人已打分，也会触发检查，符合逻辑。
            if not force and idx != self.current_idx and target_name in self.scored_contestants:
                reply = QMessageBox.question(
                    self,
                    i18n.tr("title_scored"),
                    i18n.tr("msg_contestant_scored", target_name),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    # 用户取消跳转，UI 恢复显示当前选手
                    self.combo_players.blockSignals(True)
                    # 恢复到原来的位置，如果原来是 -1 (还没选人)，那就保持 -1 或者强行选一个？
                    # 这种情况下通常保持原样即可。但 ComboBox 可能已经变了，需要变回来。
                    restore_idx = self.current_idx if self.current_idx >= 0 else 0
                    self.combo_players.setCurrentIndex(restore_idx)
                    self.combo_players.blockSignals(False)
                    return  # 中止切换

            # 2. 执行切换
            self.current_idx = idx
            self.combo_players.setCurrentIndex(idx)
            for ref in self.referees:
                ref.set_contestant(target_name)
            if self.overlay:
                self.overlay.update_title(target_name)

            # 3. 切换成功，发送重置信号给设备
            self.reset_devices_only()

    def switch_contestant(self, delta):
        if not self.contestants: return

        count = len(self.contestants)
        # 【关键修改】使用取模运算实现循环跳转
        # (当前索引 + 偏移量) % 总数
        # 例如 3人(0,1,2)，当前2，delta=1 -> (2+1)%3 = 0 (回到A)
        # 当前0，delta=-1 -> (0-1)%3 = 2 (回到C)
        new_idx = (self.current_idx + delta) % count

        self.load_contestant(new_idx)

    def jump_to_contestant(self, idx):
        self.load_contestant(idx)

    def confirm_reset_all(self):
        is_auto_next = self.chk_auto_next.isChecked() and len(self.contestants) > 0
        msg = "Are you sure you want to RESET ZERO?"
        if is_auto_next: msg += f"\n\n[Auto-Switch] This will SAVE results for '{self.contestants[self.current_idx]}' and switch to NEXT."
        reply = QMessageBox.question(self, "Confirm Reset", msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if is_auto_next:
                self.save_current_result()
                # 这里先保存，然后 switch_contestant 会负责 reset devices 和 load next
                # 注意：switch_contestant 内部调用 load_contestant 会再次 reset devices
                # 所以这里可以省略显式的 reset，或者为了保险保留也无妨 (Reset指令通常幂等)
                self.reset_devices_only()
                self.switch_contestant(1)
            else:
                self.reset_devices_only()

    def save_current_result(self):
        total_score = 0
        details = []
        for ref in self.referees:
            score = ref.last_total
            total_score += score
            details.append(f"{ref.name}:{score}")
        contestant = self.contestants[self.current_idx]
        details_str = " | ".join(details)
        storage.save_result(self.active_group_name, contestant, total_score, details_str)

    def reset_devices_only(self):
        for ref in self.referees:
            ref.request_reset()

    # ... (Overlay/Connection 保持不变) ...
    def update_overlay_btn_style(self):
        if self.overlay:
            self.btn_overlay.setText("❌ " + i18n.tr("btn_exit_overlay"))
            self.btn_overlay.setStyleSheet(
                "background-color: #f39c12; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;")
        else:
            self.btn_overlay.setText("📺 " + i18n.tr("btn_overlay"))
            self.btn_overlay.setStyleSheet(
                "background-color: #3498db; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;")

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
        if self.contestants: self.overlay.update_title(self.contestants[self.current_idx])
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

    def connect_devices(self):
        for ref in self.referees:
            if ref.primary_device: asyncio.create_task(ref.primary_device.connect())
            if ref.secondary_device: asyncio.create_task(ref.secondary_device.connect())

    def disconnect_all_devices(self):
        if not self.referees: return
        print("Disconnecting all devices...")
        for ref in self.referees:
            if ref.primary_device: asyncio.create_task(ref.primary_device.disconnect())
            if ref.secondary_device: asyncio.create_task(ref.secondary_device.disconnect())