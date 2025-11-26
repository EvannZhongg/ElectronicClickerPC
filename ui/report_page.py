# ui/report_page.py
import csv
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox,
                             QTabWidget, QFileDialog, QMessageBox, QComboBox, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QBrush
from utils.storage import storage
from utils.i18n import i18n


class ReportPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.raw_results_data = []  # 原始读取的数据
        self.processed_rankings = []  # 计算后的排名数据
        self.init_ui()
        i18n.language_changed.connect(self.update_texts)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- 顶部导航 ---
        header = QHBoxLayout()
        self.btn_back = QPushButton(i18n.tr("btn_back"))
        self.btn_back.clicked.connect(self.back_requested.emit)

        self.lbl_title = QLabel(i18n.tr("report_title"))
        self.lbl_title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        # 确保标题在深色主题下可见
        self.lbl_title.setStyleSheet("color: #2c3e50;")
        if self.parent() and "2b2b2b" in self.parent().styleSheet():
            self.lbl_title.setStyleSheet("color: white;")

        header.addWidget(self.btn_back)
        header.addSpacing(20)
        header.addWidget(self.lbl_title)
        header.addStretch()
        layout.addLayout(header)

        # --- 控制栏 (含组别筛选) ---
        ctrl_layout = QHBoxLayout()

        # 1. 组别筛选
        self.lbl_filter = QLabel(i18n.tr("lbl_filter_group"))
        self.combo_group = QComboBox()
        self.combo_group.setMinimumWidth(150)
        self.combo_group.currentIndexChanged.connect(self.calculate_ranking)

        # 2. 技术分比例
        self.lbl_ratio = QLabel(i18n.tr("lbl_tech_ratio"))
        self.spin_ratio = QSpinBox()
        self.spin_ratio.setRange(1, 100)
        self.spin_ratio.setValue(60)
        self.spin_ratio.setSuffix("%")

        self.btn_recalc = QPushButton(i18n.tr("btn_recalc"))
        self.btn_recalc.clicked.connect(self.calculate_ranking)

        self.btn_export = QPushButton(i18n.tr("btn_export_csv"))
        self.btn_export.clicked.connect(self.export_csv)

        ctrl_layout.addWidget(self.lbl_filter)
        ctrl_layout.addWidget(self.combo_group)
        ctrl_layout.addSpacing(20)
        ctrl_layout.addWidget(self.lbl_ratio)
        ctrl_layout.addWidget(self.spin_ratio)
        ctrl_layout.addWidget(self.btn_recalc)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_export)
        layout.addLayout(ctrl_layout)

        # --- 表格区域 ---
        self.tabs = QTabWidget()

        # 排名表
        self.table_rank = QTableWidget()
        self.table_rank.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_rank.setAlternatingRowColors(True)
        self.table_rank.setStyleSheet(
            "QHeaderView::section { background-color: #ecf0f1; color: #2c3e50; font-weight: bold; }")

        # 原始数据表
        self.table_raw = QTableWidget()
        self.table_raw.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_raw.verticalHeader().setVisible(False)
        self.table_raw.setStyleSheet(
            "QHeaderView::section { background-color: #ecf0f1; color: #2c3e50; font-weight: bold; }")

        self.tabs.addTab(self.table_rank, i18n.tr("tab_ranking"))
        self.tabs.addTab(self.table_raw, i18n.tr("tab_raw_data"))

        layout.addWidget(self.tabs)

    def update_texts(self):
        self.btn_back.setText(i18n.tr("btn_back"))
        self.lbl_title.setText(i18n.tr("report_title"))
        self.lbl_filter.setText(i18n.tr("lbl_filter_group"))
        self.lbl_ratio.setText(i18n.tr("lbl_tech_ratio"))
        self.btn_recalc.setText(i18n.tr("btn_recalc"))
        self.btn_export.setText(i18n.tr("btn_export_csv"))
        self.tabs.setTabText(0, i18n.tr("tab_ranking"))
        self.tabs.setTabText(1, i18n.tr("tab_raw_data"))
        self.calculate_ranking()

    def load_project_data(self, folder_name):
        storage.set_current_project(folder_name)
        self.raw_results_data = storage.get_project_results()

        groups = set()
        for r in self.raw_results_data:
            grp = r.get('group')
            if grp: groups.add(grp)

        self.combo_group.blockSignals(True)
        self.combo_group.clear()

        sorted_groups = sorted(list(groups))
        for g in sorted_groups:
            self.combo_group.addItem(g, g)

        self.combo_group.blockSignals(False)

        if self.combo_group.count() > 0:
            self.combo_group.setCurrentIndex(0)

        self.calculate_ranking()

    def calculate_ranking(self):
        ratio = self.spin_ratio.value()
        selected_group = self.combo_group.currentData()

        # 1. 过滤
        filtered_data = []
        for r in self.raw_results_data:
            if selected_group is not None and r.get('group') != selected_group:
                continue
            filtered_data.append(r)

        # 整理
        contestants = {}
        for r in filtered_data:
            contestants[r['contestant']] = r

        if not contestants:
            self.table_rank.setRowCount(0)
            self.table_raw.setRowCount(0)
            return

        # 2. 计算最大值
        max_scores_by_ref = {}
        all_ref_names = set()

        for c_data in contestants.values():
            for ref_name, score_data in c_data['ref_scores'].items():
                all_ref_names.add(ref_name)
                total = score_data.get('total', 0)
                if total > max_scores_by_ref.get(ref_name, 0):
                    max_scores_by_ref[ref_name] = total

        # 3. 计算数据
        ranking_list = []
        sorted_refs = sorted(list(all_ref_names))

        for name, data in contestants.items():
            ref_scores = data['ref_scores']
            scaled_sum = 0
            count = 0

            ref_details_formatted = {}

            for ref_name in sorted_refs:
                s_data = ref_scores.get(ref_name, {'total': 0, 'plus': 0, 'minus': 0})
                raw = s_data['total']
                plus = s_data['plus']
                minus = s_data['minus']

                max_val = max_scores_by_ref.get(ref_name, 1)
                if max_val == 0: max_val = 1

                scaled = (raw / max_val) * ratio
                scaled_sum += scaled
                count += 1

                ref_details_formatted[ref_name] = {
                    "raw": raw,
                    "plus": plus,
                    "minus": minus,
                    "scaled": scaled
                }

            final_scaled = scaled_sum / count if count > 0 else 0

            ranking_list.append({
                "contestant": name,
                "final_scaled": final_scaled,
                "ref_data": ref_details_formatted
            })

        ranking_list.sort(key=lambda x: x['final_scaled'], reverse=True)
        self.processed_rankings = ranking_list

        # 4. 渲染排名表
        cols_rank = [i18n.tr("col_rank"), i18n.tr("col_contestant"), i18n.tr("col_final_score")]
        self.table_rank.setColumnCount(len(cols_rank))
        self.table_rank.setHorizontalHeaderLabels(cols_rank)
        self.table_rank.setRowCount(len(ranking_list))
        self.table_rank.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for i, row_data in enumerate(ranking_list):
            self.table_rank.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table_rank.setItem(i, 1, QTableWidgetItem(row_data['contestant']))

            score_item = QTableWidgetItem(f"{row_data['final_scaled']:.2f}")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            score_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            self.table_rank.setItem(i, 2, score_item)

        # 5. 渲染原始数据表
        cols_raw = [i18n.tr("col_contestant")]
        for ref in sorted_refs:
            cols_raw.append(f"{ref}\n{i18n.tr('header_col_raw')}")
            cols_raw.append(f"{ref}\n{i18n.tr('header_col_scaled')}")

        self.table_raw.setColumnCount(len(cols_raw))
        self.table_raw.setHorizontalHeaderLabels(cols_raw)
        self.table_raw.setRowCount(len(ranking_list))

        # 配色定义
        color_raw_bg = QColor("#ffcccc")
        color_scaled_bg = QColor("#99ccff")
        brush_text = QBrush(QColor("black"))

        for i, row_data in enumerate(ranking_list):
            name_item = QTableWidgetItem(row_data['contestant'])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_raw.setItem(i, 0, name_item)

            current_col = 1
            for ref_name in sorted_refs:
                details = row_data['ref_data'].get(ref_name, {})

                # --- 原始分 (红色背景) ---
                if details:
                    text_raw = f"{details['raw']} ({details['plus']} / {details['minus']})"
                else:
                    text_raw = "-"

                item_raw = QTableWidgetItem(text_raw)
                item_raw.setBackground(color_raw_bg)
                item_raw.setForeground(brush_text)
                item_raw.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_raw.setItem(i, current_col, item_raw)

                # --- 比例分 (蓝色背景) ---
                if details:
                    text_scaled = f"{details['scaled']:.2f}"
                else:
                    text_scaled = "-"

                item_scaled = QTableWidgetItem(text_scaled)
                item_scaled.setBackground(color_scaled_bg)
                item_scaled.setForeground(brush_text)
                item_scaled.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_scaled.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                self.table_raw.setItem(i, current_col + 1, item_scaled)

                current_col += 2

        # --- 动态优化列宽 (修改部分) ---
        header = self.table_raw.horizontalHeader()

        # 1. 数据列：Stretch (平分剩余空间)
        for col in range(1, self.table_raw.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        # 2. 选手列：先 ResizeToContents 计算紧凑宽度，再增加缓冲
        self.table_raw.resizeColumnToContents(0)
        compact_width = self.table_raw.columnWidth(0)
        # 增加 40px 的宽度缓冲，并确保不小于 100px
        target_width = max(compact_width + 40, 100)

        # 使用 Interactive 模式，允许用户进一步拖拽调整，同时应用我们的初始宽度
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table_raw.setColumnWidth(0, target_width)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "report.csv", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)

                    writer.writerow(["Ranking Report"])
                    writer.writerow(["Rank", "Contestant", "Final Scaled Score"])
                    for i, r in enumerate(self.processed_rankings):
                        writer.writerow([i + 1, r['contestant'], f"{r['final_scaled']:.2f}"])

                    writer.writerow([])
                    writer.writerow(["Detailed Data"])

                    ref_keys = []
                    if self.processed_rankings:
                        ref_keys = sorted(list(self.processed_rankings[0]['ref_data'].keys()))

                    header = ["Contestant"]
                    for rk in ref_keys:
                        header.append(f"{rk} Raw(Total/Plus/Minus)")
                        header.append(f"{rk} Scaled")
                    writer.writerow(header)

                    for r in self.processed_rankings:
                        row = [r['contestant']]
                        for rk in ref_keys:
                            d = r['ref_data'].get(rk)
                            if d:
                                row.append(f"{d['raw']} ({d['plus']}/{d['minus']})")
                                row.append(f"{d['scaled']:.2f}")
                            else:
                                row.extend(["-", "-"])
                        writer.writerow(row)

                QMessageBox.information(self, "Success", "Export successful!")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))