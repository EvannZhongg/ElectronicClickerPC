# ui/score_panel.py
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.i18n import i18n


class ScorePanel(QFrame):
    def __init__(self, referee):
        super().__init__()
        self.referee = referee
        self.curr_total = 0
        self.curr_plus = 0
        self.curr_minus = 0

        self.init_ui()

        # 信号连接
        self.referee.score_updated.connect(self.update_score, Qt.ConnectionType.QueuedConnection)

        # 主设备状态
        if self.referee.primary_device:
            self.referee.primary_device.status_changed.connect(self.update_status_primary,
                                                               Qt.ConnectionType.QueuedConnection)

        # 副设备状态 (仅双机模式)
        if self.referee.secondary_device:
            self.referee.secondary_device.status_changed.connect(self.update_status_secondary,
                                                                 Qt.ConnectionType.QueuedConnection)

        i18n.language_changed.connect(self.retranslate_ui)

    def init_ui(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        # 背景色微调，区分卡片
        self.setStyleSheet("ScorePanel { background-color: #fdfdfd; border-radius: 8px; border: 1px solid #ddd; }")

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        # 裁判名称
        self.lbl_name = QLabel()
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: #333;")

        # 分数
        self.lbl_score = QLabel("0")
        self.lbl_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_score.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        self.lbl_score.setStyleSheet("color: #2c3e50;")

        # 详情
        self.lbl_detail = QLabel()
        self.lbl_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_detail.setStyleSheet("color: #7f8c8d; font-size: 14px;")

        # --- 【新增】重置按钮区 ---
        # 使用一个容器让按钮居中，并稍微与其他元素隔开
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 8, 0, 8)  # 上下增加一点间距

        self.btn_reset = QPushButton("RESET")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setFixedSize(80, 24)  # 固定大小，避免太占空间
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1; 
                color: #7f8c8d; 
                border: 1px solid #bdc3c7; 
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e74c3c;
                color: white;
                border: 1px solid #c0392b;
            }
            QPushButton:pressed {
                background-color: #c0392b;
            }
        """)
        # 连接到 Referee 的逻辑层 (确保 referee.py 中已实现 request_reset)
        self.btn_reset.clicked.connect(self.referee.request_reset)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()

        # --- 状态区 (改为容器) ---
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 5, 0, 0)
        status_layout.setSpacing(2)

        # 主设备状态
        self.lbl_status_pri = QLabel()
        self.lbl_status_pri.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_pri.setStyleSheet("font-size: 11px;")

        # 副设备状态 (默认隐藏，双机模式显示)
        self.lbl_status_sec = QLabel()
        self.lbl_status_sec.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_sec.setStyleSheet("font-size: 11px;")

        status_layout.addWidget(self.lbl_status_pri)
        status_layout.addWidget(self.lbl_status_sec)

        # 组装布局
        layout.addWidget(self.lbl_name)
        layout.addWidget(self.lbl_score)
        layout.addWidget(self.lbl_detail)
        layout.addWidget(btn_container)  # 插入按钮
        layout.addWidget(status_container)

        self.setLayout(layout)

        self.retranslate_ui()

    def retranslate_ui(self):
        mode_str = i18n.tr("mode_single") if self.referee.mode == "SINGLE" else i18n.tr("mode_dual")
        ref_title = i18n.tr("referee_name")
        self.lbl_name.setText(f"{ref_title} {self.referee.name} ({mode_str})")

        p_str = i18n.tr("score_plus")
        m_str = i18n.tr("score_minus")
        self.lbl_detail.setText(f"{p_str}: {self.curr_plus} | {m_str}: {self.curr_minus}")

        # 更新按钮文本
        self.btn_reset.setText("RESET 0")

        # 刷新默认状态文本
        if not self.referee.primary_device or not self.referee.primary_device.is_connected:
            self.update_status_text(self.lbl_status_pri, "device_primary", i18n.tr("status_waiting"), "orange")

        if self.referee.mode == "DUAL":
            self.lbl_status_sec.setVisible(True)
            if not self.referee.secondary_device or not self.referee.secondary_device.is_connected:
                self.update_status_text(self.lbl_status_sec, "device_secondary", i18n.tr("status_waiting"), "orange")
        else:
            self.lbl_status_sec.setVisible(False)

    def update_score(self, total, plus, minus):
        self.curr_total = total
        self.curr_plus = plus
        self.curr_minus = minus
        self.lbl_score.setText(str(total))
        self.retranslate_ui()  # 更新详情

    def update_status_primary(self, status):
        self.handle_status_update(self.lbl_status_pri, "device_primary", status)

    def update_status_secondary(self, status):
        self.handle_status_update(self.lbl_status_sec, "device_secondary", status)

    def handle_status_update(self, label, prefix_key, status):
        color = "orange"
        text = status

        if "Connected" in status and "Dis" not in status:
            text = i18n.tr("status_connected")
            color = "green"
        elif "Disconnected" in status:
            text = i18n.tr("status_disconnected")
            color = "red"
        elif "Connecting" in status:
            text = i18n.tr("status_waiting")
            color = "orange"

        self.update_status_text(label, prefix_key, text, color)

    def update_status_text(self, label, prefix_key, status_text, color):
        prefix = i18n.tr(prefix_key)
        label.setText(f"{prefix}: {status_text}")
        label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")