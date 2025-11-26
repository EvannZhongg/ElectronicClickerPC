# ui/setup_wizard.py
import asyncio
from bleak import BleakScanner
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QRadioButton, QSpinBox, QButtonGroup,
                             QPushButton, QStackedWidget, QComboBox, QFormLayout,
                             QScrollArea, QGroupBox, QListWidget, QPlainTextEdit, QMessageBox, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from logic.referee import Referee
from core.device_node import DeviceNode
from config import DEVICE_NAME_PREFIX
from utils.i18n import i18n


class SetupWizard(QWidget):
    setup_finished = pyqtSignal(str, list, dict)
    back_to_home_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_name = ""
        self.scanned_devices = []
        self.is_scanning = False
        self.scan_task = None
        self.ref_cards = []

        # 数据结构:
        # groups_data: { "GroupA": ["P1", "P2"] } (兼容旧结构)
        # groups_config: { "GroupA": {"ref_count": 2} } (新增配置)
        self.groups_data = {}
        self.groups_config = {}
        self._pending_ref_configs = []

        self.init_ui()
        i18n.language_changed.connect(self.retranslate_ui)

    def reset(self):
        """重置为新建项目状态"""
        self.stop_scan_safe()
        self.stack.setCurrentIndex(0)
        self.input_proj_name.setText("My Match")

        # 默认选中自由模式
        self.rb_mode_free.setChecked(True)
        self.spin_global_ref_count.setValue(2)
        self.spin_global_ref_count.setEnabled(True)

        self.lbl_error_msg.setText("")
        self.groups_data = {}
        self.groups_config = {}
        self.list_groups.clear()
        self.txt_names.clear()
        self.combo_start_group.clear()
        self.update_ui_state_by_mode()

        self._pending_ref_configs = []
        self.lbl_title.setText(i18n.tr("wiz_p1_title"))

    def restore_state(self, config_data):
        """从历史记录恢复状态"""
        self.reset()

        # 1. Page 1 基础信息
        self.project_name = config_data.get("project_name", "My Match")
        self.input_proj_name.setText(self.project_name)

        # 2. 恢复裁判配置缓存 (用于 Page 2)
        refs_data = config_data.get("referees", [])
        self._pending_ref_configs = refs_data

        # 3. 恢复组别和配置
        t_data = config_data.get("tournament_data", {})
        self.groups_data = t_data.get("groups", {})
        self.groups_config = t_data.get("group_configs", {})  # 读取新字段

        active_grp = t_data.get("active_group")

        # 判定模式
        if not self.groups_data:
            # 无组别 -> 自由模式
            self.rb_mode_free.setChecked(True)
            self.spin_global_ref_count.setValue(len(refs_data) if refs_data else 2)
        else:
            # 有组别 -> 赛事模式
            self.rb_mode_tourn.setChecked(True)
            for grp in self.groups_data.keys():
                self.list_groups.addItem(grp)

            # 刷新下拉框
            self.refresh_start_group_combo()

            # 选中之前的组
            if active_grp:
                idx = self.combo_start_group.findText(active_grp)
                if idx >= 0:
                    self.combo_start_group.setCurrentIndex(idx)

        self.update_ui_state_by_mode()
        print("Wizard state restored.")

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)

        # Nav
        nav_layout = QHBoxLayout()
        self.btn_nav_back = QPushButton()
        self.btn_nav_back.clicked.connect(self.on_nav_back)
        self.btn_nav_back.setFixedWidth(100)

        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")

        nav_layout.addWidget(self.btn_nav_back)
        nav_layout.addWidget(self.lbl_title)
        nav_layout.addStretch()
        self.main_layout.addLayout(nav_layout)

        # Stack
        self.stack = QStackedWidget()
        self.page1 = self.create_page1()
        self.page2 = self.create_page2()
        self.stack.addWidget(self.page1)
        self.stack.addWidget(self.page2)
        self.main_layout.addWidget(self.stack)

        # Error Msg
        self.lbl_error_msg = QLabel("")
        self.lbl_error_msg.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        self.lbl_error_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.lbl_error_msg)

        self.retranslate_ui()

    def show_error(self, msg):
        self.lbl_error_msg.setText(msg)
        asyncio.get_event_loop().call_later(3, lambda: self.lbl_error_msg.setText(""))

    def create_page1(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # --- 1. 顶部：模式选择 ---
        mode_group_box = QGroupBox("Mode Selection")
        mode_layout = QHBoxLayout(mode_group_box)

        self.rb_mode_free = QRadioButton("Free Mode (Basic)")
        self.rb_mode_tourn = QRadioButton("Tournament Mode (Groups)")
        self.rb_mode_free.setChecked(True)

        self.btn_group_mode = QButtonGroup(page)
        self.btn_group_mode.addButton(self.rb_mode_free, 0)
        self.btn_group_mode.addButton(self.rb_mode_tourn, 1)
        self.btn_group_mode.idToggled.connect(self.update_ui_state_by_mode)

        mode_layout.addWidget(self.rb_mode_free)
        mode_layout.addWidget(self.rb_mode_tourn)
        layout.addWidget(mode_group_box)

        # --- 2. 基础设置 (Free Mode) ---
        self.grp_basic = QGroupBox("Basic Settings")
        form_layout = QFormLayout(self.grp_basic)

        self.input_proj_name = QLineEdit("My Match")
        self.lbl_proj_name = QLabel()
        form_layout.addRow(self.lbl_proj_name, self.input_proj_name)

        self.lbl_ref_count = QLabel()
        self.spin_global_ref_count = QSpinBox()
        self.spin_global_ref_count.setRange(1, 10)
        self.spin_global_ref_count.setValue(2)
        form_layout.addRow(self.lbl_ref_count, self.spin_global_ref_count)

        layout.addWidget(self.grp_basic)

        # --- 3. 赛事配置 (Tournament Mode) ---
        self.grp_contestants = QGroupBox()
        contestant_layout = QVBoxLayout(self.grp_contestants)

        # 工具栏：添加组别
        tool_layout = QHBoxLayout()
        self.btn_add_group = QPushButton("+ New Group")
        self.btn_add_group.clicked.connect(self.add_group_dialog)
        self.btn_del_group = QPushButton("- Delete")
        self.btn_del_group.clicked.connect(self.del_group)

        tool_layout.addWidget(self.btn_add_group)
        tool_layout.addWidget(self.btn_del_group)
        tool_layout.addStretch()
        contestant_layout.addLayout(tool_layout)

        # 左右分栏
        h_split = QHBoxLayout()

        # 左侧：组别列表
        left_box = QVBoxLayout()
        self.lbl_group_list = QLabel()
        self.list_groups = QListWidget()
        self.list_groups.currentItemChanged.connect(self.on_group_selected)
        left_box.addWidget(self.lbl_group_list)
        left_box.addWidget(self.list_groups)

        # 右侧：名单编辑 + 该组的裁判配置
        right_box = QVBoxLayout()

        # 组别特定的裁判数量设置
        grp_setting_layout = QHBoxLayout()
        self.lbl_grp_ref_count = QLabel("Referees for this group:")
        self.spin_grp_ref_count = QSpinBox()
        self.spin_grp_ref_count.setRange(1, 10)
        self.spin_grp_ref_count.setValue(2)
        self.spin_grp_ref_count.valueChanged.connect(self.save_current_group_config)

        grp_setting_layout.addWidget(self.lbl_grp_ref_count)
        grp_setting_layout.addWidget(self.spin_grp_ref_count)
        grp_setting_layout.addStretch()
        right_box.addLayout(grp_setting_layout)

        self.lbl_names_edit = QLabel()
        self.txt_names = QPlainTextEdit()
        self.txt_names.setPlaceholderText("Name 1\nName 2\n...")
        self.txt_names.textChanged.connect(self.save_current_group_names)
        self.txt_names.setEnabled(False)
        self.spin_grp_ref_count.setEnabled(False)  # 初始禁用，选中组后启用

        right_box.addWidget(self.lbl_names_edit)
        right_box.addWidget(self.txt_names)

        h_split.addLayout(left_box, 1)
        h_split.addLayout(right_box, 2)
        contestant_layout.addLayout(h_split)

        # 底部：初始组别选择
        start_grp_layout = QHBoxLayout()
        self.lbl_start_group = QLabel("Start with Group:")
        self.combo_start_group = QComboBox()
        start_grp_layout.addWidget(self.lbl_start_group)
        start_grp_layout.addWidget(self.combo_start_group, 1)
        contestant_layout.addLayout(start_grp_layout)

        layout.addWidget(self.grp_contestants)
        layout.addStretch()

        self.btn_next = QPushButton()
        self.btn_next.setMinimumHeight(40)
        self.btn_next.clicked.connect(self.go_to_page2)
        self.btn_next.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; font-weight: bold;")
        layout.addWidget(self.btn_next)

        return page

    def update_ui_state_by_mode(self):
        is_free = self.rb_mode_free.isChecked()

        # 自由模式：启用全局设置，禁用组别面板
        self.spin_global_ref_count.setEnabled(is_free)
        self.grp_contestants.setEnabled(not is_free)

        if is_free:
            self.grp_contestants.setTitle(f"{i18n.tr('grp_contestants')} (Disabled in Free Mode)")
        else:
            self.grp_contestants.setTitle(i18n.tr("grp_contestants"))

    # --- 名单管理逻辑 ---
    def add_group_dialog(self):
        # 弹窗输入组名
        name, ok = QInputDialog.getText(self, i18n.tr("btn_add_group"), i18n.tr("placeholder_group_name"))
        if ok and name.strip():
            key = name.strip()
            if key in self.groups_data:
                self.show_error(f"Group '{key}' already exists!")
                return

            # 询问该组裁判数量
            count, ok_count = QInputDialog.getInt(self, "Referee Count", f"Referees for group '{key}':", 2, 1, 10)
            if not ok_count: count = 2

            # 初始化数据
            self.groups_data[key] = []
            self.groups_config[key] = {"ref_count": count}

            self.list_groups.addItem(key)
            self.list_groups.setCurrentRow(self.list_groups.count() - 1)
            self.refresh_start_group_combo()

    def del_group(self):
        row = self.list_groups.currentRow()
        if row < 0: return
        item = self.list_groups.takeItem(row)
        key = item.text()
        if key in self.groups_data: del self.groups_data[key]
        if key in self.groups_config: del self.groups_config[key]

        self.refresh_start_group_combo()
        if self.list_groups.count() == 0:
            self.txt_names.clear()
            self.txt_names.setEnabled(False)
            self.spin_grp_ref_count.setEnabled(False)

    def on_group_selected(self, current, previous):
        if not current:
            self.txt_names.clear()
            self.txt_names.setEnabled(False)
            self.spin_grp_ref_count.setEnabled(False)
            return

        key = current.text()
        self.txt_names.setEnabled(True)
        self.spin_grp_ref_count.setEnabled(True)

        # Load names
        names = self.groups_data.get(key, [])
        self.txt_names.setPlainText("\n".join(names))

        # Load ref count
        cfg = self.groups_config.get(key, {"ref_count": 2})
        self.spin_grp_ref_count.blockSignals(True)
        self.spin_grp_ref_count.setValue(cfg.get("ref_count", 2))
        self.spin_grp_ref_count.blockSignals(False)

    def save_current_group_names(self):
        current = self.list_groups.currentItem()
        if not current: return
        key = current.text()
        text = self.txt_names.toPlainText()
        names = [line.strip() for line in text.split('\n') if line.strip()]
        self.groups_data[key] = names

    def save_current_group_config(self):
        current = self.list_groups.currentItem()
        if not current: return
        key = current.text()
        count = self.spin_grp_ref_count.value()
        if key not in self.groups_config: self.groups_config[key] = {}
        self.groups_config[key]["ref_count"] = count

    def refresh_start_group_combo(self):
        curr_text = self.combo_start_group.currentText()
        self.combo_start_group.clear()
        for grp in self.groups_data.keys():
            self.combo_start_group.addItem(grp)

        idx = self.combo_start_group.findText(curr_text)
        if idx >= 0: self.combo_start_group.setCurrentIndex(idx)

    def create_page2(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        tool_layout = QHBoxLayout()
        self.lbl_scan_status = QLabel()
        self.lbl_scan_status.setStyleSheet("color: #7f8c8d;")
        self.btn_rescan = QPushButton()
        self.btn_rescan.clicked.connect(self.start_scan)
        tool_layout.addWidget(self.lbl_scan_status)
        tool_layout.addStretch()
        tool_layout.addWidget(self.btn_rescan)
        layout.addLayout(tool_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.addStretch()
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

        self.btn_finish = QPushButton()
        self.btn_finish.setMinimumHeight(50)
        self.btn_finish.clicked.connect(self.on_finish)
        self.btn_finish.setStyleSheet(
            "background-color: #2ecc71; color: white; border-radius: 5px; font-weight: bold; font-size: 16px;")
        layout.addWidget(self.btn_finish)
        return page

    def retranslate_ui(self):
        self.btn_nav_back.setText(i18n.tr("btn_back"))
        is_p1 = self.stack.currentIndex() == 0
        self.lbl_title.setText(i18n.tr("wiz_p1_title") if is_p1 else i18n.tr("wiz_p2_title"))

        self.rb_mode_free.setText(i18n.tr("val_free_mode"))
        self.rb_mode_tourn.setText(i18n.tr("mode_multi_player"))  # 借用多组模式文案，或新增

        self.lbl_proj_name.setText(i18n.tr("lbl_proj_name"))
        self.lbl_ref_count.setText(i18n.tr("lbl_ref_count"))

        self.grp_contestants.setTitle(i18n.tr("grp_contestants"))
        self.lbl_group_list.setText(i18n.tr("lbl_group_list"))
        self.btn_add_group.setText(i18n.tr("btn_add_group"))
        self.btn_del_group.setText(i18n.tr("btn_del_group"))
        self.lbl_names_edit.setText(i18n.tr("lbl_names_edit"))

        self.btn_next.setText(i18n.tr("btn_next"))
        self.btn_rescan.setText(i18n.tr("btn_rescan"))
        self.btn_finish.setText(i18n.tr("btn_finish"))

        if not self.scanned_devices: self.lbl_scan_status.setText(i18n.tr("status_no_dev"))
        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), RefereeConfigCard): item.widget().retranslate_ui()

    def on_nav_back(self):
        self.stop_scan_safe()
        self.lbl_error_msg.setText("")
        if self.stack.currentIndex() == 1:
            self.stack.setCurrentIndex(0)
            self.lbl_title.setText(i18n.tr("wiz_p1_title"))
        else:
            self.back_to_home_requested.emit()

    def go_to_page2(self):
        self.lbl_error_msg.setText("")
        self.project_name = self.input_proj_name.text() or "Match"

        # 核心逻辑：确定裁判数量
        ref_count = 1
        if self.rb_mode_free.isChecked():
            # 自由模式：直接读取全局设置
            ref_count = self.spin_global_ref_count.value()
        else:
            # 赛事模式：检查组别
            if not self.groups_data:
                self.show_error("Please create at least one group for Tournament Mode.")
                return

            # 计算所有组别中需求的最大值
            max_needed = 0
            for k in self.groups_data.keys():
                cfg = self.groups_config.get(k, {})
                c = cfg.get("ref_count", 2)
                if c > max_needed: max_needed = c

            if max_needed == 0: max_needed = 1
            ref_count = max_needed

        print(f"Generating cards for {ref_count} referees.")
        self.generate_referee_cards(ref_count)

        # 恢复暂存的配置 (如果有)
        if self._pending_ref_configs:
            for i, card in enumerate(self.ref_cards):
                if i < len(self._pending_ref_configs):
                    prev = self._pending_ref_configs[i]
                    mode_idx = card.combo_mode.findData(prev.get("mode", "SINGLE"))
                    if mode_idx >= 0: card.combo_mode.setCurrentIndex(mode_idx)

        self.stack.setCurrentIndex(1)
        self.lbl_title.setText(i18n.tr("wiz_p2_title"))
        self.start_scan()

    def generate_referee_cards(self, count):
        while self.cards_layout.count() > 1:
            child = self.cards_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        self.ref_cards = []
        for i in range(count):
            card = RefereeConfigCard(i + 1)
            self.cards_layout.insertWidget(i, card)
            self.ref_cards.append(card)

    def stop_scan_safe(self):
        if self.scan_task and not self.scan_task.done(): self.scan_task.cancel()
        self.is_scanning = False
        self.btn_rescan.setEnabled(True)

    def start_scan(self):
        if self.is_scanning: return
        self.is_scanning = True
        self.lbl_scan_status.setText(i18n.tr("status_scanning"))
        self.btn_rescan.setEnabled(False)
        self.scan_task = asyncio.create_task(self.run_ble_scan())

    async def run_ble_scan(self):
        try:
            devices = await BleakScanner.discover(timeout=4.0)
            if not self.is_scanning: return
            self.scanned_devices = [d for d in devices if d.name and DEVICE_NAME_PREFIX in d.name]
            for card in self.ref_cards: card.update_devices(self.scanned_devices)
            self.lbl_scan_status.setText(i18n.tr("status_found", len(self.scanned_devices)))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.lbl_scan_status.setText(f"Error: {e}")
        finally:
            self.is_scanning = False
            self.btn_rescan.setEnabled(True)

    def on_finish(self):
        final_referees = []
        used_addresses = set()

        for card in self.ref_cards:
            if not card.validate_selection():
                self.show_error(i18n.tr("msg_select_all"))
                return

            pri_addr = card.combo_pri.currentData().address
            if pri_addr in used_addresses:
                self.show_error(i18n.tr("msg_duplicate_dev", pri_addr))
                return
            used_addresses.add(pri_addr)

            if card.is_dual_mode():
                sec_addr = card.combo_sec.currentData().address
                if sec_addr in used_addresses:
                    self.show_error(i18n.tr("msg_duplicate_dev", sec_addr))
                    return
                used_addresses.add(sec_addr)

            ref = card.get_configured_referee()
            final_referees.append(ref)

        # 准备 Tournament Data
        if self.rb_mode_free.isChecked():
            active_group = None
        else:
            active_group = self.combo_start_group.currentText()

        tournament_data = {
            "groups": self.groups_data,
            "group_configs": self.groups_config,  # 保存组别裁判配置
            "active_group": active_group
        }

        self.stop_scan_safe()
        self.lbl_error_msg.setText("")
        self.setup_finished.emit(self.project_name, final_referees, tournament_data)


class RefereeConfigCard(QGroupBox):
    def __init__(self, index):
        super().__init__()
        self.index = index
        self.devices = []
        self.init_ui()
        self.retranslate_ui()

    def init_ui(self):
        self.setStyleSheet(
            "QGroupBox { border: 1px solid #ddd; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        layout = QFormLayout(self)
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Single", "SINGLE")
        self.combo_mode.addItem("Dual", "DUAL")
        self.combo_mode.currentIndexChanged.connect(self.on_mode_change)
        layout.addRow(QLabel("Mode:"), self.combo_mode)
        self.combo_pri = QComboBox()
        self.combo_pri.currentIndexChanged.connect(self.update_secondary_list)
        self.lbl_pri = QLabel("Primary:")
        layout.addRow(self.lbl_pri, self.combo_pri)
        self.combo_sec = QComboBox()
        self.lbl_sec = QLabel("Secondary:")
        layout.addRow(self.lbl_sec, self.combo_sec)
        self.on_mode_change()

    def retranslate_ui(self):
        self.setTitle(f"{i18n.tr('header_referee')} {self.index}")
        self.combo_mode.setItemText(0, i18n.tr("mode_single_dev"))
        self.combo_mode.setItemText(1, i18n.tr("mode_dual_dev"))
        layout = self.layout()
        if layout.itemAt(0, QFormLayout.ItemRole.LabelRole):
            layout.itemAt(0, QFormLayout.ItemRole.LabelRole).widget().setText(i18n.tr("header_mode"))
        self.lbl_pri.setText(i18n.tr("header_dev_pri"))
        self.lbl_sec.setText(i18n.tr("header_dev_sec"))

    def on_mode_change(self):
        is_dual = (self.combo_mode.currentData() == "DUAL")
        self.lbl_sec.setVisible(is_dual)
        self.combo_sec.setVisible(is_dual)
        if is_dual: self.update_secondary_list()

    def update_devices(self, devices):
        self.devices = devices
        cur_pri_addr = self.combo_pri.currentData().address if self.combo_pri.currentData() else None
        self.combo_pri.blockSignals(True)
        self.combo_pri.clear()
        self.combo_pri.addItem(i18n.tr("placeholder_select"), None)
        for d in devices: self.combo_pri.addItem(f"{d.name} ({d.address})", d)
        if cur_pri_addr: self.set_combo_by_addr(self.combo_pri, cur_pri_addr)
        self.combo_pri.blockSignals(False)
        self.update_secondary_list()

    def update_secondary_list(self):
        if not self.combo_sec.isVisible(): return
        cur_sec_addr = self.combo_sec.currentData().address if self.combo_sec.currentData() else None
        pri_addr = self.combo_pri.currentData().address if self.combo_pri.currentData() else None
        self.combo_sec.blockSignals(True)
        self.combo_sec.clear()
        self.combo_sec.addItem(i18n.tr("placeholder_select"), None)
        for d in self.devices:
            if pri_addr and d.address == pri_addr: continue
            self.combo_sec.addItem(f"{d.name} ({d.address})", d)
        if cur_sec_addr: self.set_combo_by_addr(self.combo_sec, cur_sec_addr)
        self.combo_sec.blockSignals(False)

    def set_combo_by_addr(self, combo, addr):
        for i in range(combo.count()):
            data = combo.itemData(i)
            if data and data.address == addr:
                combo.setCurrentIndex(i)
                break

    def validate_selection(self):
        if not self.combo_pri.currentData(): return False
        if self.is_dual_mode() and not self.combo_sec.currentData(): return False
        return True

    def is_dual_mode(self):
        return self.combo_mode.currentData() == "DUAL"

    def get_configured_referee(self):
        name = f"{i18n.tr('referee_name')} {self.index}"
        mode = self.combo_mode.currentData()
        ref = Referee(self.index, name, mode)
        d_pri = self.combo_pri.currentData()
        node_pri = DeviceNode(d_pri)
        node_sec = None
        if mode == "DUAL":
            d_sec = self.combo_sec.currentData()
            if d_sec:
                node_sec = DeviceNode(d_sec)
        ref.set_devices(primary=node_pri, secondary=node_sec)
        return ref