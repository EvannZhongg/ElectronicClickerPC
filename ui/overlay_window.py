# ui/overlay_window.py
from PyQt6.QtWidgets import QWidget, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QColor
from utils.i18n import i18n


class DraggableLabel(QLabel):
    """
    可拖拽并支持网格吸附的标签控件
    """

    def __init__(self, parent=None, grid_size=50):
        super().__init__(parent)
        self.grid_size = grid_size  # 网格大小 (像素)
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.widget_start_pos = QPoint()

        # 设置鼠标手势提示
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        # 初始样式：半透明背景，圆角，白色文字
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 150); 
                color: white; 
                border-radius: 8px; 
                padding: 10px;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            # 记录按下时的全局鼠标位置和控件当前位置
            self.drag_start_pos = event.globalPosition().toPoint()
            self.widget_start_pos = self.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            # 计算鼠标移动的偏移量
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            target_pos = self.widget_start_pos + delta

            # --- 网格吸附核心逻辑 ---
            # 将坐标四舍五入到最近的 grid_size 倍数
            snapped_x = round(target_pos.x() / self.grid_size) * self.grid_size
            snapped_y = round(target_pos.y() / self.grid_size) * self.grid_size

            # 移动控件
            self.move(snapped_x, snapped_y)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class OverlayWindow(QWidget):
    # 信号：当窗口关闭时通知主程序
    closed_signal = pyqtSignal()

    def __init__(self, target_window, referees):
        super().__init__()
        self.target_window = target_window
        self.referees = referees
        self.labels = {}

        self.init_ui()
        self.setup_tracking()

    def init_ui(self):
        # 窗口属性：无边框、置顶、工具窗口、透明背景
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 【注意】移除了之前的 Layout，改用绝对定位

        # 网格设定
        grid_size = 50
        start_x = 50
        start_y = 50

        for index, ref in enumerate(self.referees):
            # 使用自定义的可拖拽标签
            lbl = DraggableLabel(self, grid_size=grid_size)
            lbl.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))

            # 添加阴影效果让文字更清晰
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(5)
            shadow.setColor(QColor(0, 0, 0))
            shadow.setOffset(2, 2)
            lbl.setGraphicsEffect(shadow)

            # 初始位置：按索引垂直排列，对齐网格
            initial_y = start_y + (index * grid_size * 2)  # 间隔两个格子
            lbl.move(start_x, initial_y)
            lbl.show()

            self.labels[ref] = lbl

            # 连接信号
            self.update_referee_label(ref)
            ref.score_updated.connect(lambda t, p, m, r=ref: self.update_referee_label(r))

    def update_referee_label(self, ref):
        if ref not in self.labels: return

        total = getattr(ref, 'last_total', 0)
        plus = getattr(ref, 'last_plus', 0)
        minus = getattr(ref, 'last_minus', 0)

        # 格式化显示文本
        text = f"{ref.name}\n{i18n.tr('score_total')}: {total}   (+{plus} / -{minus})"

        lbl = self.labels[ref]
        lbl.setText(text)
        lbl.adjustSize()  # 每次文字改变后自适应大小，保证背景框正确包裹

    def setup_tracking(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync_position)
        self.timer.start(100)

    def sync_position(self):
        if not self.target_window: return
        try:
            # 只有当目标窗口可见时才显示悬浮窗
            if not self.target_window.visible:  # 注意：pygetwindow 属性可能是 isActive 或 visible
                # pygetwindow 的 visible 属性可能不准确，通常只要未最小化即可
                # 这里简单处理：如果找不到窗口或者报错则关闭
                pass

                # 同步位置和大小覆盖目标窗口
            self.setGeometry(
                self.target_window.left,
                self.target_window.top,
                self.target_window.width,
                self.target_window.height
            )
            self.show()
        except Exception:
            self.close()

    def closeEvent(self, event):
        self.timer.stop()
        self.closed_signal.emit()
        super().closeEvent(event)