# logic/referee.py
from PyQt6.QtCore import QObject, pyqtSignal, Qt  # 【关键】导入 Qt
from core.device_node import DeviceNode


class Referee(QObject):
    score_updated = pyqtSignal(int, int, int)

    def __init__(self, name, mode="SINGLE"):
        super().__init__()
        self.name = name
        self.mode = mode
        self.primary_device: DeviceNode = None
        self.secondary_device: DeviceNode = None

        # --- 新增：内部状态缓存 ---
        self.last_total = 0
        self.last_plus = 0
        self.last_minus = 0

        self.pos_dev_val = 0
        self.neg_dev_val = 0

    def set_devices(self, primary, secondary=None):
        self.primary_device = primary
        # 【修改点1】强制队列连接，将执行权切回主线程
        self.primary_device.data_received.connect(self._on_primary_data, Qt.ConnectionType.QueuedConnection)

        if self.mode == "DUAL" and secondary:
            self.secondary_device = secondary
            # 【修改点2】同上
            self.secondary_device.data_received.connect(self._on_secondary_data, Qt.ConnectionType.QueuedConnection)

    # 【修改点3】参数改为解包后的5个int
    def _on_primary_data(self, current, evt_type, plus, minus, ts):
        if self.mode == "SINGLE":
            self.last_total = current
            self.last_plus = plus
            self.last_minus = minus
            self.score_updated.emit(current, plus, minus)
        else:
            self.pos_dev_val = current
            self._calculate_dual_score()

    def _on_secondary_data(self, current, evt_type, plus, minus, ts):
        if self.mode == "DUAL":
            self.neg_dev_val = current
            self._calculate_dual_score()

    def _calculate_dual_score(self):
        final_score = self.pos_dev_val - self.neg_dev_val

        # 更新缓存
        self.last_total = final_score
        self.last_plus = self.pos_dev_val
        self.last_minus = self.neg_dev_val

        self.score_updated.emit(final_score, self.pos_dev_val, self.neg_dev_val)