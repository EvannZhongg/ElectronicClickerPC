# ui/overlay_window.py
import time
import csv
import os
import datetime
from PyQt6.QtWidgets import (QWidget, QLabel, QGraphicsDropShadowEffect,
                             QPushButton, QVBoxLayout)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRect, QSize
from PyQt6.QtGui import (QFont, QColor, QPainter, QPen, QPainterPath,
                         QBrush, QCursor)
from utils.i18n import i18n
from utils.storage import storage


# ============================================================================
# 通用悬浮组件基类
# ============================================================================
class OverlayWidget(QWidget):
    """
    具备以下功能的通用悬浮控件：
    1. 鼠标左键拖拽移动 (支持网格吸附)
    2. 右下角边缘拖拽改变大小 (Resize)
    3. 鼠标悬停显示背景/边框 (移出后透明)
    4. 鼠标悬停显示关闭按钮
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.grid_size = 20

        self.is_dragging = False
        self.is_resizing = False
        self.drag_start_pos = QPoint()
        self.widget_start_pos = QPoint()
        self.widget_start_size = QSize()
        self.hovered = False

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 25, 15, 15)

        self.btn_close = QPushButton("×", self)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.close)
        self.btn_close.hide()

        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 14px;
                line-height: 20px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)

        self.resize(200, 100)
        self.setMinimumSize(100, 60)

    def update_close_btn_pos(self):
        self.btn_close.move(self.width() - 30, 6)

    def resizeEvent(self, event):
        self.update_close_btn_pos()
        super().resizeEvent(event)

    def enterEvent(self, event):
        self.hovered = True
        self.btn_close.show()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.btn_close.hide()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_in_resize_area(event.pos()):
                self.is_resizing = True
                self.drag_start_pos = event.globalPosition().toPoint()
                self.widget_start_size = self.size()
                event.accept()
            else:
                self.is_dragging = True
                self.drag_start_pos = event.globalPosition().toPoint()
                self.widget_start_pos = self.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.raise_()
                event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_resizing:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            new_width = max(self.minimumWidth(), self.widget_start_size.width() + delta.x())
            new_height = max(self.minimumHeight(), self.widget_start_size.height() + delta.y())
            self.resize(new_width, new_height)
            event.accept()
            return

        if self.is_dragging:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            target_pos = self.widget_start_pos + delta

            if self.grid_size > 1:
                snapped_x = round(target_pos.x() / self.grid_size) * self.grid_size
                snapped_y = round(target_pos.y() / self.grid_size) * self.grid_size
                self.move(snapped_x, snapped_y)
            else:
                self.move(target_pos)

            event.accept()
            return

        if self.is_in_resize_area(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.is_resizing = False
            if self.is_in_resize_area(event.pos()):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def is_in_resize_area(self, pos):
        rect = self.rect()
        return (pos.x() > rect.width() - 20 and pos.y() > rect.height() - 20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.hovered:
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

            # Resize handle icon
            painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
            w, h = self.width(), self.height()
            painter.drawLine(w - 6, h - 6, w - 6, h - 6)
            painter.drawLine(w - 10, h - 6, w - 6, h - 10)
            painter.drawLine(w - 14, h - 6, w - 6, h - 14)


# ============================================================================
# 具体组件：裁判分显示标签
# ============================================================================
class DraggableLabel(OverlayWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(250, 100)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.label.setWordWrap(True)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(5)
        shadow.setColor(QColor(0, 0, 0))
        shadow.setOffset(2, 2)
        self.label.setGraphicsEffect(shadow)

        self.main_layout.addWidget(self.label)
        self.label.setStyleSheet("color: white; border: none; background: transparent;")

    def set_text(self, text, font):
        self.label.setFont(font)
        self.label.setText(text)

    def paintEvent(self, event):
        super().paintEvent(event)


# ============================================================================
# 具体组件：实时曲线控件 (从第一个非零分记录开始)
# ============================================================================
class ScoreCurveWidget(OverlayWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(600, 250)

        self.history = {}
        self.ref_colors = {}
        self.start_time = None

        self.color_palette = [
            QColor("#e74c3c"), QColor("#3498db"), QColor("#2ecc71"),
            QColor("#f1c40f"), QColor("#9b59b6"), QColor("#e67e22"),
        ]

    def reset_data(self):
        self.history.clear()
        self.start_time = None
        self.update()

    def load_history(self, contestant_name, referees):
        self.history.clear()
        self.start_time = None

        project_path = storage.current_project_path
        if not project_path or not os.path.exists(project_path):
            return

        # 1. 读取所有原始数据
        raw_data_map = {}  # { ref: [(ts, score), ...] }
        for ref in referees:
            csv_path = os.path.join(project_path, f"referee_{ref.index}.csv")
            if not os.path.exists(csv_path):
                continue
            pts = []
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("Contestant") == contestant_name:
                            ts_str = row.get("SystemTime")
                            score_str = row.get("CurrentTotal")
                            if ts_str and score_str:
                                try:
                                    if '.' in ts_str and len(ts_str.split('.')[1]) == 3:
                                        ts_str += "000"
                                    dt = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
                                    ts = dt.timestamp()
                                    pts.append((ts, int(score_str)))
                                except:
                                    pass
            except:
                pass
            if pts:
                raw_data_map[ref] = pts

        # 2. 寻找全局最早的“非零”时间点作为 0 秒
        min_non_zero_ts = None
        for pts in raw_data_map.values():
            for (ts, score) in pts:
                if score != 0:
                    if min_non_zero_ts is None or ts < min_non_zero_ts:
                        min_non_zero_ts = ts

        # 如果所有记录都是0，或者没有记录，则保持等待状态
        if min_non_zero_ts is None:
            self.update()
            return

        self.start_time = min_non_zero_ts

        # 3. 填充 history (过滤掉起点之前的 0 分记录)
        for ref, pts in raw_data_map.items():
            if ref not in self.ref_colors:
                idx = len(self.ref_colors)
                self.ref_colors[ref] = self.color_palette[idx % len(self.color_palette)]

            clean_pts = []
            for (ts, score) in pts:
                # 只保留 start_time 之后（或同时）的点
                if ts < self.start_time:
                    continue

                elapsed = ts - self.start_time
                clean_pts.append((elapsed, score))

            if clean_pts:
                self.history[ref] = clean_pts

        self.update()

    def add_point(self, ref, score):
        current_ts = time.time()

        # 实时数据：只有当分数不为0时，才初始化起点
        if self.start_time is None:
            if score != 0:
                self.start_time = current_ts
            else:
                # 依然是 0 分，且未开始，则忽略（继续等待）
                return

        if ref not in self.history:
            self.history[ref] = []
            idx = len(self.history) - 1
            self.ref_colors[ref] = self.color_palette[idx % len(self.color_palette)]

        elapsed = current_ts - self.start_time
        if elapsed < 0: elapsed = 0

        self.history[ref].append((elapsed, score))
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 没有数据或未开始时，显示占位框
        if not self.history or self.start_time is None:
            painter.setBrush(QColor(0, 0, 0, 80))
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1, Qt.PenStyle.DashLine))
            rect = self.rect().adjusted(2, 2, -2, -2)
            painter.drawRoundedRect(rect, 10, 10)

            painter.setPen(QColor(220, 220, 220))
            painter.setFont(QFont("Microsoft YaHei", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Waiting for start signal...")
            return

        # 正常绘制
        margin = 20
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        w, h = rect.width(), rect.height()
        x0, y0 = rect.x(), rect.y()

        all_times = [pt[0] for pts in self.history.values() for pt in pts]
        all_scores = [pt[1] for pts in self.history.values() for pt in pts]

        if not all_times: return

        max_time = max(max(all_times), 5.0)

        if not all_scores:
            min_score, max_score = 0, 10
        else:
            min_score, max_score = min(all_scores), max(all_scores)

        if min_score == max_score:
            min_score -= 5
            max_score += 5
        else:
            span = max_score - min_score
            min_score -= span * 0.1
            max_score += span * 0.1

        def map_x(t):
            return x0 + (t / max_time) * w

        def map_y(s):
            ratio = (s - min_score) / (max_score - min_score)
            return (y0 + h) - (ratio * h)

        if min_score <= 0 <= max_score:
            zero_y = map_y(0)
            painter.setPen(QPen(QColor(255, 255, 255, 150), 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(x0), int(zero_y), int(x0 + w), int(zero_y))

        for ref, points in self.history.items():
            if not points: continue

            color = self.ref_colors.get(ref, Qt.GlobalColor.white)
            pen = QPen(color, 2)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            path = QPainterPath()
            start_x = map_x(points[0][0])
            start_y = map_y(points[0][1])
            path.moveTo(start_x, start_y)

            for t, s in points[1:]:
                path.lineTo(map_x(t), map_y(s))

            painter.drawPath(path)

            last_pt = points[-1]
            cx, cy = map_x(last_pt[0]), map_y(last_pt[1])

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(int(cx), int(cy)), 4, 4)

            painter.setPen(QColor("white"))
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.drawText(int(cx) + 8, int(cy) + 5, str(last_pt[1]))


# ============================================================================
# 主悬浮窗容器
# ============================================================================
class OverlayWindow(QWidget):
    closed_signal = pyqtSignal()

    def __init__(self, target_window, referees):
        super().__init__()
        self.target_window = target_window
        self.referees = referees
        self.labels = {}

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.curve_widget = ScoreCurveWidget(self)
        self.curve_widget.move(50, 400)
        self.curve_widget.show()

        self.lbl_title = DraggableLabel(self)
        self.lbl_title.resize(400, 80)
        self.lbl_title.set_text("Waiting...", QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        self.lbl_title.move(300, 20)
        self.lbl_title.hide()

        self.init_referee_labels()
        self.setup_tracking()

    def init_referee_labels(self):
        start_x = 50
        start_y = 60
        gap_y = 120

        for index, ref in enumerate(self.referees):
            lbl = DraggableLabel(self)
            lbl.resize(250, 100)
            lbl.move(start_x, start_y + index * gap_y)
            lbl.show()
            self.labels[ref] = lbl

            ref.score_updated.connect(lambda t, p, m, r=ref: self.update_referee_label(r))

    def update_title(self, name):
        self.lbl_title.set_text(name, QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        self.lbl_title.show()

        self.curve_widget.load_history(name, self.referees)

        # 仅更新文字
        for ref in self.referees:
            if ref in self.labels:
                total = getattr(ref, 'last_total', 0)
                plus = getattr(ref, 'last_plus', 0)
                minus = getattr(ref, 'last_minus', 0)
                text = f"{ref.name}\n{i18n.tr('score_total')}: {total}   (+{plus} / -{minus})"
                self.labels[ref].set_text(text, QFont("Microsoft YaHei", 16, QFont.Weight.Bold))

    def update_referee_label(self, ref):
        if ref not in self.labels: return

        total = getattr(ref, 'last_total', 0)
        plus = getattr(ref, 'last_plus', 0)
        minus = getattr(ref, 'last_minus', 0)

        text = f"{ref.name}\n{i18n.tr('score_total')}: {total}   (+{plus} / -{minus})"

        lbl = self.labels[ref]
        lbl.set_text(text, QFont("Microsoft YaHei", 16, QFont.Weight.Bold))

        self.curve_widget.add_point(ref, total)

    def setup_tracking(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync_position)
        self.timer.start(50)

    def sync_position(self):
        if not self.target_window: return
        try:
            self.setGeometry(
                self.target_window.left,
                self.target_window.top,
                self.target_window.width,
                self.target_window.height
            )
            if self.isHidden(): self.show()
        except Exception:
            self.close()

    def closeEvent(self, event):
        self.timer.stop()
        self.closed_signal.emit()
        super().closeEvent(event)