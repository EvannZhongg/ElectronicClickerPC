# ui/setup_wizard.py
import asyncio
from bleak import BleakScanner
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QRadioButton, QSpinBox, QButtonGroup,
                             QPushButton, QStackedWidget, QComboBox, QFormLayout,
                             QScrollArea, QGroupBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QInputDialog, QAbstractItemView,
                             QDialog, QDialogButtonBox, QPlainTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from logic.referee import Referee
from core.device_node import DeviceNode
from config import DEVICE_NAME_PREFIX
from utils.i18n import i18n


# ============================================================================
# 子组件：名单编辑弹窗
# ============================================================================
class NamesEditorDialog(QDialog):
    def __init__(self, group_name, current_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("title_edit_names", group_name))
        self.resize(400, 500)
        self.names = []

        layout = QVBoxLayout(self)
        self.lbl_info = QLabel(i18n.tr("lbl_names_input"))
        layout.addWidget(self.lbl_info)

        self.txt_edit = QPlainTextEdit()
        self.txt_edit.setPlainText("\n".join(current_names))
        layout.addWidget(self.txt_edit)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_names(self):
        text = self.txt_edit.toPlainText()
        # 过滤空行和空白字符
        return [line.strip() for line in text.split('\n') if line.strip()]


# ============================================================================
# 子组件：组别管理器
# ============================================================================
class GroupManagerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 数据结构: { "GroupA": {"ref_count": 3, "names": ["P1", "P2"]} }
        self.groups_config = {}
        self.init_ui()
        # 监听语言切换
        i18n.language_changed.connect(self.retranslate_ui)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton()
        self.btn_add.clicked.connect(self.add_group_dialog)

        self.btn_edit = QPushButton()  # 新增编辑按钮
        self.btn_edit.clicked.connect(self.edit_group_names)

        self.btn_del = QPushButton()
        self.btn_del.clicked.connect(self.del_group)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_del)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 表格展示：组名 | 裁判数 | 选手人数
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.edit_group_names)  # 双击也可以编辑
        layout.addWidget(self.table)

        self.lbl_hint = QLabel()
        self.lbl_hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.lbl_hint)

        self.retranslate_ui()

    def retranslate_ui(self):
        self.btn_add.setText(i18n.tr("btn_add_group"))
        self.btn_edit.setText(i18n.tr("btn_edit_names"))
        self.btn_del.setText(i18n.tr("btn_del_group"))
        self.table.setHorizontalHeaderLabels([
            i18n.tr("header_group_name"),
            i18n.tr("header_ref_count"),
            i18n.tr("header_player_count")
        ])
        self.lbl_hint.setText(i18n.tr("msg_dbl_click_hint"))

    def add_group_dialog(self):
        # 1. 输入组名
        name, ok = QInputDialog.getText(self, i18n.tr("dialog_add_group"), i18n.tr("dialog_group_name_input"))
        if not ok or not name.strip(): return
        group_name = name.strip()

        if group_name in self.groups_config:
            QMessageBox.warning(self, "Error", i18n.tr("error_group_exists"))
            return

        # 2. 输入该组裁判数量
        count, ok = QInputDialog.getInt(self, i18n.tr("dialog_ref_count"),
                                        i18n.tr("dialog_ref_count_msg"), 2, 1, 10)
        if not ok: return

        # 3. 保存并刷新
        self.groups_config[group_name] = {
            "ref_count": count,
            "names": []
        }
        self.refresh_table()
        self.table.selectRow(self.table.rowCount() - 1)

        # 自动弹出编辑名单窗口，方便用户
        self.edit_group_names()

    def edit_group_names(self):
        row = self.table.currentRow()
        if row < 0:
            # 如果没选中，提示或者不操作
            if self.table.rowCount() > 0:
                QMessageBox.warning(self, "Tip", i18n.tr("error_select_group"))
            return

        group_name = self.table.item(row, 0).text()
        current_data = self.groups_config.get(group_name, {})
        current_names = current_data.get("names", [])

        dialog = NamesEditorDialog(group_name, current_names, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_names = dialog.get_names()
            self.groups_config[group_name]["names"] = new_names
            self.refresh_table()
            # 保持选中状态
            items = self.table.findItems(group_name, Qt.MatchFlag.MatchExactly)
            if items:
                self.table.setCurrentItem(items[0])

    def del_group(self):
        row = self.table.currentRow()
        if row < 0: return
        group_name = self.table.item(row, 0).text()
        del self.groups_config[group_name]
        self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(0)
        for name, cfg in self.groups_config.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(cfg.get("ref_count", 2))))
            # 显示该组有多少人
            player_count = len(cfg.get("names", []))
            self.table.setItem(row, 2, QTableWidgetItem(str(player_count)))

    def get_selected_group(self):
        row = self.table.currentRow()
        if row < 0: return None
        return self.table.item(row, 0).text()

    def get_group_config(self, group_name):
        return self.groups_config.get(group_name)


# ============================================================================
# 主设置向导
# ============================================================================
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
        self._temp_ref_configs = []

        self.init_ui()
        # 连接语言切换信号
        i18n.language_changed.connect(self.retranslate_ui)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)

        # --- 导航栏 ---
        nav_layout = QHBoxLayout()
        self.btn_nav_back = QPushButton()
        self.btn_nav_back.clicked.connect(self.on_nav_back)
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        nav_layout.addWidget(self.btn_nav_back)
        nav_layout.addWidget(self.lbl_title)
        nav_layout.addStretch()
        self.main_layout.addLayout(nav_layout)

        # --- 多页堆叠 ---
        self.stack = QStackedWidget()
        self.page1 = self.create_page1_settings()
        self.page2 = self.create_page2_binding()
        self.stack.addWidget(self.page1)
        self.stack.addWidget(self.page2)
        self.main_layout.addWidget(self.stack)

        # 错误提示区
        self.lbl_error = QLabel()
        self.lbl_error.setStyleSheet("color: red;")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.lbl_error)

        # 初始化文本
        self.retranslate_ui()

    def retranslate_ui(self):
        # 导航
        self.btn_nav_back.setText(i18n.tr("btn_back"))
        is_p1 = self.stack.currentIndex() == 0
        if is_p1:
            self.lbl_title.setText(i18n.tr("wiz_p1_title"))
        else:
            self.lbl_title.setText(i18n.tr("wiz_p2_title"))

        # Page 1
        self.mode_box.setTitle(i18n.tr("wiz_step1_mode"))
        self.rb_mode_free.setText(i18n.tr("wiz_mode_free"))
        self.rb_mode_tourn.setText(i18n.tr("wiz_mode_tourn"))

        self.basic_box.setTitle(i18n.tr("wiz_step2_basic"))
        self.lbl_proj_name_field.setText(i18n.tr("wiz_lbl_proj_name"))

        self.container_free.setTitle(i18n.tr("wiz_free_settings"))
        self.lbl_free_ref.setText(i18n.tr("wiz_lbl_free_ref_count"))

        self.container_tourn.setTitle(i18n.tr("wiz_tourn_settings"))
        self.btn_next.setText(i18n.tr("btn_next_bind"))

        # Page 2
        self.btn_rescan.setText(i18n.tr("btn_rescan"))
        self.btn_finish.setText(i18n.tr("btn_finish"))
        if not self.is_scanning:
            if not self.scanned_devices:
                self.lbl_scan_status.setText(i18n.tr("status_no_dev"))
            else:
                self.lbl_scan_status.setText(i18n.tr("status_found", len(self.scanned_devices)))
        else:
            self.lbl_scan_status.setText(i18n.tr("status_scanning"))

        # 刷新子组件
        if hasattr(self, 'group_manager'):
            self.group_manager.retranslate_ui()
        for card in self.ref_cards:
            if hasattr(card, 'retranslate_ui'):
                card.retranslate_ui()

    def reset(self):
        self.stack.setCurrentIndex(0)
        self.input_proj_name.setText("New Match")
        self.rb_mode_free.setChecked(True)
        self.group_manager.groups_config = {}
        self.group_manager.refresh_table()
        self.stop_scan_safe()
        self.update_mode_ui()
        self.retranslate_ui()

    def restore_state(self, config_data):
        self.reset()
        self.input_proj_name.setText(config_data.get("project_name", "Match"))
        t_data = config_data.get("tournament_data", {})
        grp_configs = t_data.get("group_configs", {})

        # 恢复名单和裁判数配置
        # 注意：save时 group_configs 结构为 {name: {ref_count: N}}, groups 为 {name: [p1, p2]}
        # 这里我们需要合并回 group_manager 的数据结构 {name: {ref_count: N, names: []}}
        names_data = t_data.get("groups", {})

        merged_config = {}
        # 先合并配置
        for name, cfg in grp_configs.items():
            merged_config[name] = {
                "ref_count": cfg.get("ref_count", 2),
                "names": names_data.get(name, [])
            }

        if merged_config:
            self.rb_mode_tourn.setChecked(True)
            self.group_manager.groups_config = merged_config
            self.group_manager.refresh_table()
        else:
            self.rb_mode_free.setChecked(True)
            refs = config_data.get("referees", [])
            if refs:
                self.spin_free_ref_count.setValue(len(refs))

        self._temp_ref_configs = config_data.get("referees", [])
        self.update_mode_ui()

    def create_page1_settings(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        # 1. 模式选择
        self.mode_box = QGroupBox()
        mode_layout = QHBoxLayout(self.mode_box)
        self.rb_mode_free = QRadioButton()
        self.rb_mode_tourn = QRadioButton()
        self.rb_mode_free.setChecked(True)
        self.btn_grp_mode = QButtonGroup()
        self.btn_grp_mode.addButton(self.rb_mode_free)
        self.btn_grp_mode.addButton(self.rb_mode_tourn)
        self.btn_grp_mode.idToggled.connect(self.update_mode_ui)
        mode_layout.addWidget(self.rb_mode_free)
        mode_layout.addWidget(self.rb_mode_tourn)
        layout.addWidget(self.mode_box)

        # 2. 基础信息
        self.basic_box = QGroupBox()
        form = QFormLayout(self.basic_box)
        self.input_proj_name = QLineEdit("New Match")
        self.lbl_proj_name_field = QLabel()
        form.addRow(self.lbl_proj_name_field, self.input_proj_name)
        layout.addWidget(self.basic_box)

        # 3. 自由模式配置区
        self.container_free = QGroupBox()
        free_layout = QFormLayout(self.container_free)
        self.spin_free_ref_count = QSpinBox()
        self.spin_free_ref_count.setRange(1, 10)
        self.spin_free_ref_count.setValue(2)
        self.lbl_free_ref = QLabel()
        free_layout.addRow(self.lbl_free_ref, self.spin_free_ref_count)
        layout.addWidget(self.container_free)

        # 4. 赛事模式配置区
        self.container_tourn = QGroupBox()
        tourn_layout = QVBoxLayout(self.container_tourn)
        self.group_manager = GroupManagerWidget()
        tourn_layout.addWidget(self.group_manager)
        layout.addWidget(self.container_tourn)

        layout.addStretch()

        # 下一步
        self.btn_next = QPushButton()
        self.btn_next.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 10px;")
        self.btn_next.clicked.connect(self.go_to_page2)
        layout.addWidget(self.btn_next)

        return page

    def update_mode_ui(self):
        is_free = self.rb_mode_free.isChecked()
        self.container_free.setVisible(is_free)
        self.container_tourn.setVisible(not is_free)
        self.lbl_error.setText("")

    def create_page2_binding(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # 扫描栏
        scan_bar = QHBoxLayout()
        self.lbl_scan_status = QLabel()
        self.btn_rescan = QPushButton()
        self.btn_rescan.clicked.connect(self.start_scan)
        scan_bar.addWidget(self.lbl_scan_status)
        scan_bar.addStretch()
        scan_bar.addWidget(self.btn_rescan)
        layout.addLayout(scan_bar)

        # 卡片容器
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.addStretch()
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

        # 完成按钮
        self.btn_finish = QPushButton()
        self.btn_finish.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 12px;")
        self.btn_finish.clicked.connect(self.on_finish)
        layout.addWidget(self.btn_finish)

        return page

    def go_to_page2(self):
        target_ref_count = 0
        self.active_group_name = None

        if self.rb_mode_free.isChecked():
            target_ref_count = self.spin_free_ref_count.value()
            self.active_group_name = None  # 自由模式不传递 active_group
        else:
            selected_group = self.group_manager.get_selected_group()
            if not selected_group:
                self.show_error(i18n.tr("error_select_group"))
                return

            cfg = self.group_manager.get_group_config(selected_group)
            target_ref_count = cfg.get("ref_count", 2)
            self.active_group_name = selected_group

        self.generate_cards(target_ref_count)
        self.stack.setCurrentIndex(1)
        self.retranslate_ui()  # 确保标题更新
        self.start_scan()

    def generate_cards(self, count):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        self.ref_cards = []
        for i in range(count):
            card = RefereeConfigCard(i + 1)
            self.cards_layout.insertWidget(i, card)
            self.ref_cards.append(card)

    def on_finish(self):
        final_referees = []
        used_addrs = set()

        for card in self.ref_cards:
            if not card.validate_selection():
                self.show_error(i18n.tr("msg_select_all"))
                return

            ref = card.get_configured_referee()

            # 简单的地址查重
            p = ref.primary_device.ble_device.address
            if p in used_addrs:
                self.show_error(i18n.tr("msg_duplicate_dev", p))
                return
            used_addrs.add(p)

            final_referees.append(ref)

        tournament_data = {}
        if self.rb_mode_free.isChecked():
            tournament_data = {
                "groups": {},
                "group_configs": {},
                "active_group": None
            }
        else:
            raw_configs = self.group_manager.groups_config
            groups_map = {}
            configs_map = {}
            for name, data in raw_configs.items():
                groups_map[name] = data.get("names", [])
                configs_map[name] = {"ref_count": data.get("ref_count", 2)}

            tournament_data = {
                "groups": groups_map,
                "group_configs": configs_map,
                "active_group": self.active_group_name
            }

        self.setup_finished.emit(self.input_proj_name.text(), final_referees, tournament_data)

    def show_error(self, msg):
        self.lbl_error.setText(msg)
        # 3秒后清除
        asyncio.get_event_loop().call_later(3, lambda: self.lbl_error.setText(""))

    def on_nav_back(self):
        if self.stack.currentIndex() == 1:
            self.stack.setCurrentIndex(0)
            self.retranslate_ui()
            self.stop_scan_safe()
        else:
            self.back_to_home_requested.emit()

    def start_scan(self):
        if self.is_scanning: return
        self.is_scanning = True
        self.retranslate_ui()
        self.btn_rescan.setEnabled(False)
        self.scan_task = asyncio.create_task(self.run_ble_scan())

    def stop_scan_safe(self):
        if self.scan_task and not self.scan_task.done():
            self.scan_task.cancel()
        self.is_scanning = False
        self.retranslate_ui()  # 更新状态文字

    async def run_ble_scan(self):
        try:
            devs = await BleakScanner.discover(timeout=4.0)
            self.scanned_devices = [d for d in devs if d.name and DEVICE_NAME_PREFIX in d.name]
            for card in self.ref_cards: card.update_devices(self.scanned_devices)
        except Exception as e:
            self.lbl_scan_status.setText(f"Error: {e}")
        finally:
            self.is_scanning = False
            self.btn_rescan.setEnabled(True)
            self.retranslate_ui()


# 此处保留您原有的 RefereeConfigCard 类，无需大改，
# 仅需确保其内部也使用了 i18n.tr() 并在 retranslate_ui 中更新文本
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

        self.lbl_mode = QLabel()
        layout.addRow(self.lbl_mode, self.combo_mode)

        self.combo_pri = QComboBox()
        self.combo_pri.currentIndexChanged.connect(self.update_secondary_list)
        self.lbl_pri = QLabel()
        layout.addRow(self.lbl_pri, self.combo_pri)

        self.combo_sec = QComboBox()
        self.lbl_sec = QLabel()
        layout.addRow(self.lbl_sec, self.combo_sec)

        self.on_mode_change()

    def retranslate_ui(self):
        self.setTitle(f"{i18n.tr('header_referee')} {self.index}")
        self.combo_mode.setItemText(0, i18n.tr("mode_single_dev"))
        self.combo_mode.setItemText(1, i18n.tr("mode_dual_dev"))

        self.lbl_mode.setText(i18n.tr("header_mode"))
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