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
from ui.report_page import ReportPage
from utils.storage import storage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1100, 800)
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
        self.is_free_mode = False
        self.scored_contestants = set()

        # 全局快捷键
        saved_shortcut = app_settings.get("reset_shortcut")
        self.reset_shortcut = QShortcut(QKeySequence(saved_shortcut), self)
        self.reset_shortcut.activated.connect(self.on_shortcut_reset)

        # 2. 堆叠窗口
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # 3. 菜单
        self.init_menu()
        i18n.language_changed.connect(self.update_texts)

        # 4. 页面初始化
        self.home_page = HomePage()
        self.home_page.start_project_requested.connect(self.start_new_project)
        self.home_page.open_project_requested.connect(self.open_existing_project)
        self.home_page.view_report_requested.connect(self.show_report_page)
        self.stack.addWidget(self.home_page)

        self.wizard_page = SetupWizard()
        self.wizard_page.setup_finished.connect(self.on_setup_finished)
        self.wizard_page.back_to_home_requested.connect(self.go_to_home)
        self.stack.addWidget(self.wizard_page)

        self.dashboard_page = QWidget()
        self.stack.addWidget(self.dashboard_page)

        self.report_page = ReportPage()
        self.report_page.back_requested.connect(self.go_to_home)
        self.stack.addWidget(self.report_page)

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
        idx = self.stack.currentIndex()
        if idx == 2 and self.project_name:
            self.setWindowTitle(f"{i18n.tr('app_title')} - {self.project_name}")
        elif idx == 3:
            self.setWindowTitle(f"{i18n.tr('app_title')} - {i18n.tr('report_title')}")
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

    def show_report_page(self, folder_name):
        self.report_page.load_project_data(folder_name)
        self.stack.setCurrentIndex(3)
        self.update_texts()

    def go_to_home(self):
        self.stack.setCurrentIndex(0)
        self.project_name = ""
        if hasattr(self.home_page, "refresh_list"):
            self.home_page.refresh_list()
        self.update_texts()

    def go_to_wizard_page1(self):
        self.wizard_page.stack.setCurrentIndex(0)
        self.wizard_page.lbl_title.setText(i18n.tr("wiz_p1_title"))

    def back_from_dashboard(self):
        # 1. 检查是否有未保存的分数
        current_total = 0
        for ref in self.referees:
            current_total += ref.last_total

        if current_total != 0:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(i18n.tr("title_unsaved"))
            msg_box.setText(i18n.tr("msg_unsaved"))
            msg_box.setIcon(QMessageBox.Icon.Warning)

            btn_save = msg_box.addButton(i18n.tr("btn_save_exit"), QMessageBox.ButtonRole.AcceptRole)
            btn_discard = msg_box.addButton(i18n.tr("btn_discard_exit"), QMessageBox.ButtonRole.DestructiveRole)
            btn_cancel = msg_box.addButton(i18n.tr("btn_stay"), QMessageBox.ButtonRole.RejectRole)

            msg_box.exec()

            clicked = msg_box.clickedButton()
            if clicked == btn_cancel:
                return  # 取消退出
            elif clicked == btn_save:
                self.save_current_result()
            # elif clicked == btn_discard: pass

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

        active_group_val = tournament_data.get("active_group")

        if active_group_val:
            self.is_free_mode = False
            self.active_group_name = active_group_val
            if self.active_group_name in tournament_data["groups"]:
                self.contestants = tournament_data["groups"][self.active_group_name]
            else:
                self.contestants = []
        else:
            self.is_free_mode = True
            self.active_group_name = "Free Mode"
            self.contestants = ["Player 1"]

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

        QTimer.singleShot(10, self.finalize_setup_ui)

    def finalize_setup_ui(self):
        self.setup_dashboard()

        initial_idx = 0
        if not self.is_free_mode and self.contestants:
            found_unscored = False
            for i, name in enumerate(self.contestants):
                if name not in self.scored_contestants:
                    initial_idx = i
                    found_unscored = True
                    break

            if not found_unscored and len(self.contestants) > 0:
                QMessageBox.warning(self, i18n.tr("title_warning"), i18n.tr("msg_all_contestants_scored"))

        self.load_contestant(initial_idx, force=True)
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

        display_group_name = i18n.tr('val_free_mode') if self.is_free_mode else self.active_group_name
        lbl_grp_info = QLabel(f"{i18n.tr('lbl_curr_group')}: {display_group_name}")
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

        if self.is_free_mode:
            self.btn_prev.setEnabled(True)
            self.btn_next.setEnabled(True)
            self.combo_players.setEnabled(True)
            self.chk_auto_next.setEnabled(True)
            self.chk_auto_next.setChecked(True)
        else:
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
        self.btn_reset_all.clicked.connect(self.on_btn_reset_clicked)

        ctrl_layout.addWidget(lbl_grp_info)
        ctrl_layout.addWidget(self.btn_prev)
        ctrl_layout.addWidget(self.combo_players)
        ctrl_layout.addWidget(self.btn_next)
        ctrl_layout.addWidget(self.chk_auto_next)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_reset_all)

        main_layout.addWidget(control_bar)

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
                self.scored_contestants.add(current_name)

    def load_contestant(self, idx, force=False):
        if not self.contestants: return

        if 0 <= idx < len(self.contestants):
            target_name = self.contestants[idx]

            # 覆盖提醒逻辑
            if not force and idx != self.current_idx and target_name in self.scored_contestants:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle(i18n.tr("title_scored"))
                msg_box.setText(i18n.tr("msg_want_to_overwrite", target_name))
                msg_box.setIcon(QMessageBox.Icon.Question)

                btn_overwrite = msg_box.addButton(i18n.tr("btn_overwrite"), QMessageBox.ButtonRole.AcceptRole)
                btn_finish = msg_box.addButton(i18n.tr("btn_finish_match"), QMessageBox.ButtonRole.DestructiveRole)
                btn_stay = msg_box.addButton(i18n.tr("btn_stay"), QMessageBox.ButtonRole.RejectRole)

                msg_box.exec()

                clicked = msg_box.clickedButton()

                if clicked == btn_stay:
                    self.combo_players.blockSignals(True)
                    restore_idx = self.current_idx if self.current_idx >= 0 else 0
                    self.combo_players.setCurrentIndex(restore_idx)
                    self.combo_players.blockSignals(False)
                    return

                elif clicked == btn_finish:
                    self.back_from_dashboard()
                    return

            self.current_idx = idx
            self.combo_players.blockSignals(True)
            self.combo_players.setCurrentIndex(idx)
            self.combo_players.blockSignals(False)

            for ref in self.referees:
                ref.set_contestant(target_name)

            if self.overlay:
                self.overlay.update_title(target_name)

            self.reset_devices_only()

    # 1. 按钮点击：强制仅归零，不跳转
    def on_btn_reset_clicked(self):
        self.perform_reset_logic(force_no_jump=True)

    # 2. 快捷键 (Ctrl+G)：根据连赛模式决定是否跳转
    def on_shortcut_reset(self):
        self.perform_reset_logic(force_no_jump=False)

    # 3. 通用复位逻辑执行者
    def perform_reset_logic(self, force_no_jump=False):
        auto_jump = (not force_no_jump) and self.chk_auto_next.isChecked() and len(self.contestants) > 0

        should_confirm = not app_settings.get("suppress_reset_confirm")
        proceed = True

        if should_confirm:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(i18n.tr("title_reset"))
            msg_box.setIcon(QMessageBox.Icon.Question)

            text = i18n.tr("msg_reset_confirm")
            if auto_jump:
                curr_name = self.contestants[self.current_idx] if self.contestants else "Current"
                text += i18n.tr("msg_reset_auto_suffix", curr_name)

            msg_box.setText(text)
            chk_dont_ask = QCheckBox(i18n.tr("chk_dont_ask_again"))
            msg_box.setCheckBox(chk_dont_ask)

            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)

            ret = msg_box.exec()

            if ret != QMessageBox.StandardButton.Yes:
                proceed = False

            if chk_dont_ask.isChecked():
                app_settings.set("suppress_reset_confirm", True)

        if proceed:
            if auto_jump:
                self.save_current_result()
                self.switch_contestant(1)
            else:
                self.reset_devices_only()

    # 4. 智能切换选手逻辑
    def switch_contestant(self, delta):
        if not self.contestants: return

        # --- 自由模式 ---
        if self.is_free_mode:
            new_idx = self.current_idx + delta
            if new_idx < 0: return
            if new_idx >= len(self.contestants):
                new_name = f"Player {new_idx + 1}"
                self.contestants.append(new_name)
                self.combo_players.addItem(new_name)
                self.load_contestant(new_idx)
            else:
                self.load_contestant(new_idx)
            return

        # --- 赛事模式 ---
        count = len(self.contestants)

        if delta < 0:
            new_idx = (self.current_idx + delta) % count
            self.load_contestant(new_idx)
            return

        next_idx = -1
        found_unscored = False

        for i in range(1, count + 1):
            check_idx = (self.current_idx + i) % count
            name = self.contestants[check_idx]

            if check_idx == self.current_idx:
                break

            if name not in self.scored_contestants:
                next_idx = check_idx
                found_unscored = True
                break

        if found_unscored:
            self.load_contestant(next_idx)
        else:
            self.handle_all_scored()

    def handle_all_scored(self):
        """处理所有选手都已完赛的情况"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(i18n.tr("title_warning"))
        msg_box.setText(i18n.tr("msg_match_finished"))
        msg_box.setIcon(QMessageBox.Icon.Information)

        # 【核心修改】将按钮动作从“导出”改为“保存并返回配置页”
        btn_finish = msg_box.addButton(i18n.tr("btn_finish_return"), QMessageBox.ButtonRole.AcceptRole)
        btn_review = msg_box.addButton(i18n.tr("btn_review"), QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()

        if msg_box.clickedButton() == btn_finish:
            # 执行“保存并返回”逻辑：
            # 1. 关闭资源
            self.close_overlay_if_active()
            self.disconnect_all_devices()

            # 2. 跳转到向导页 (Index 1) 的配置步 (Index 0)
            self.stack.setCurrentIndex(1)
            self.wizard_page.stack.setCurrentIndex(0)
            self.wizard_page.retranslate_ui()  # 刷新标题状态
        else:
            # 留在当前页面回顾，跳回第一位
            self.load_contestant(0, force=True)

    def jump_to_contestant(self, idx):
        self.load_contestant(idx)

    def save_current_result(self):
        total_score = 0
        details = []
        for ref in self.referees:
            score = ref.last_total
            total_score += score
            details.append(f"{ref.name}={score}:{ref.last_plus}:{ref.last_minus}")

        contestant = self.contestants[self.current_idx]
        details_str = " | ".join(details)
        storage.save_result(self.active_group_name, contestant, total_score, details_str)

    def reset_devices_only(self):
        for ref in self.referees:
            ref.request_reset()

    # --- Overlay / Window Selection ---
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
        if self.contestants and 0 <= self.current_idx < len(self.contestants):
            self.overlay.update_title(self.contestants[self.current_idx])
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