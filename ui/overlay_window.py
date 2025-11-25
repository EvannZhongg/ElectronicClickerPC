# ui/overlay_window.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from utils.i18n import i18n


class OverlayWindow(QWidget):
    # 信号：当窗口关闭时（无论是代码关闭还是Alt+F4关闭），通知主程序
    closed_signal = pyqtSignal()

    def __init__(self, target_window, referees):
        super().__init__()
        self.target_window = target_window
        self.referees = referees

        self.init_ui()
        self.setup_tracking()

    # ... (init_ui, update_referee_label 保持不变，直接复用上一步的代码) ...
    # ... 请确保 init_ui 代码存在 ...

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        left_container = QWidget()
        left_container.setFixedWidth(300)
        self.score_layout = QVBoxLayout(left_container)
        self.score_layout.setSpacing(15)
        self.labels = {}
        for ref in self.referees:
            lbl = QLabel()
            lbl.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Black))
            lbl.setStyleSheet("color: white;")
            lbl.setWordWrap(True)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(5)
            shadow.setColor(QColor(0, 0, 0))
            shadow.setOffset(2, 2)
            lbl.setGraphicsEffect(shadow)
            self.score_layout.addWidget(lbl)
            self.labels[ref] = lbl
            self.update_referee_label(ref)
            ref.score_updated.connect(lambda t, p, m, r=ref: self.update_referee_label(r))
        self.score_layout.addStretch()
        main_layout.addWidget(left_container)
        main_layout.addStretch()

    def update_referee_label(self, ref):
        if ref not in self.labels: return
        total = getattr(ref, 'last_total', 0)
        plus = getattr(ref, 'last_plus', 0)
        minus = getattr(ref, 'last_minus', 0)
        text = f"{ref.name}\n{i18n.tr('score_total')}: {total}   (+{plus} / -{minus})"
        self.labels[ref].setText(text)

    def setup_tracking(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync_position)
        self.timer.start(100)

    def sync_position(self):
        if not self.target_window: return
        try:
            if not self.target_window.visible:
                self.hide()
            else:
                self.show()
                self.setGeometry(
                    self.target_window.left,
                    self.target_window.top,
                    self.target_window.width,
                    self.target_window.height
                )
        except Exception:
            self.close()

    # --- 关键修改：重写 closeEvent ---
    def closeEvent(self, event):
        self.timer.stop()
        self.closed_signal.emit()  # 确保通知主窗口清理引用
        super().closeEvent(event)