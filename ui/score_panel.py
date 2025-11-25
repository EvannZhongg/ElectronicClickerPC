# ui/score_panel.py
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout, QWidget, QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
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
        if self.referee.primary_device:
            self.referee.primary_device.status_changed.connect(self.update_status_primary,
                                                               Qt.ConnectionType.QueuedConnection)
        if self.referee.secondary_device:
            self.referee.secondary_device.status_changed.connect(self.update_status_secondary,
                                                                 Qt.ConnectionType.QueuedConnection)
        i18n.language_changed.connect(self.retranslate_ui)

    def init_ui(self):
        # 优化样式：浅灰背景，柔和阴影，圆角
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            ScorePanel {
                background-color: #F7F9FC; 
                border-radius: 12px; 
                border: 1px solid #E4E7ED;
            }
        """)

        # 添加阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # 裁判名称
        self.lbl_name = QLabel()
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")

        # 分数 (加大字号，深色)
        self.lbl_score = QLabel("0")
        self.lbl_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_score.setFont(QFont("Arial", 64, QFont.Weight.Bold))
        self.lbl_score.setStyleSheet("color: #2c3e50;")

        # 详情
        self.lbl_detail = QLabel()
        self.lbl_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_detail.setStyleSheet("color: #7f8c8d; font-size: 14px; font-weight: 500;")

        # 按钮容器
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 15, 0, 10)

        self.btn_reset = QPushButton("RESET")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setFixedSize(100, 32)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #fff; 
                color: #e74c3c; 
                border: 1px solid #e74c3c; 
                border-radius: 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton:pressed {
                background-color: #c0392b;
                border-color: #c0392b;
            }
        """)
        self.btn_reset.clicked.connect(self.referee.request_reset)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()

        # 状态区
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 5, 0, 0)
        status_layout.setSpacing(2)

        self.lbl_status_pri = QLabel()
        self.lbl_status_pri.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_status_sec = QLabel()
        self.lbl_status_sec.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status_layout.addWidget(self.lbl_status_pri)
        status_layout.addWidget(self.lbl_status_sec)

        layout.addWidget(self.lbl_name)
        layout.addWidget(self.lbl_score)
        layout.addWidget(self.lbl_detail)
        layout.addWidget(btn_container)
        layout.addWidget(status_container)

        self.setLayout(layout)
        self.retranslate_ui()

    def retranslate_ui(self):
        # ... (保持原逻辑不变) ...
        mode_str = i18n.tr("mode_single") if self.referee.mode == "SINGLE" else i18n.tr("mode_dual")
        ref_title = i18n.tr("referee_name")
        self.lbl_name.setText(f"{ref_title} {self.referee.name} ({mode_str})")

        p_str = i18n.tr("score_plus")
        m_str = i18n.tr("score_minus")
        self.lbl_detail.setText(f"{p_str}: {self.curr_plus} | {m_str}: {self.curr_minus}")

        self.btn_reset.setText("RESET 0")

        if not self.referee.primary_device or not self.referee.primary_device.is_connected:
            self.update_status_text(self.lbl_status_pri, "device_primary", i18n.tr("status_waiting"), "#f39c12")

        if self.referee.mode == "DUAL":
            self.lbl_status_sec.setVisible(True)
            if not self.referee.secondary_device or not self.referee.secondary_device.is_connected:
                self.update_status_text(self.lbl_status_sec, "device_secondary", i18n.tr("status_waiting"), "#f39c12")
        else:
            self.lbl_status_sec.setVisible(False)

    def update_score(self, total, plus, minus):
        self.curr_total = total
        self.curr_plus = plus
        self.curr_minus = minus
        self.lbl_score.setText(str(total))
        self.retranslate_ui()

    def update_status_primary(self, status):
        self.handle_status_update(self.lbl_status_pri, "device_primary", status)

    def update_status_secondary(self, status):
        self.handle_status_update(self.lbl_status_sec, "device_secondary", status)

    def handle_status_update(self, label, prefix_key, status):
        color = "#f39c12"  # orange
        text = status

        if "Connected" in status and "Dis" not in status:
            text = i18n.tr("status_connected")
            color = "#27ae60"  # green
        elif "Disconnected" in status:
            text = i18n.tr("status_disconnected")
            color = "#c0392b"  # red
        elif "Connecting" in status:
            text = i18n.tr("status_waiting")
            color = "#f39c12"

        self.update_status_text(label, prefix_key, text, color)

    def update_status_text(self, label, prefix_key, status_text, color):
        prefix = i18n.tr(prefix_key)
        label.setText(f"{prefix}: {status_text}")
        label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")