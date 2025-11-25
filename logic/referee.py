# logic/referee.py
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from core.device_node import DeviceNode
from utils.storage import storage  # 【新增】导入


class Referee(QObject):
    score_updated = pyqtSignal(int, int, int)

    # 【修改】增加 index 参数
    def __init__(self, index, name, mode="SINGLE"):
        super().__init__()
        self.index = index  # 裁判编号，用于区分 CSV 文件
        self.name = name
        self.mode = mode

        self.primary_device: DeviceNode = None
        self.secondary_device: DeviceNode = None

        self.last_total = 0
        self.last_plus = 0
        self.last_minus = 0

        self.pos_dev_val = 0
        self.neg_dev_val = 0

    def set_devices(self, primary, secondary=None):
        self.primary_device = primary
        self.primary_device.data_received.connect(self._on_primary_data, Qt.ConnectionType.QueuedConnection)

        if self.mode == "DUAL" and secondary:
            self.secondary_device = secondary
            self.secondary_device.data_received.connect(self._on_secondary_data, Qt.ConnectionType.QueuedConnection)

    def _on_primary_data(self, current, evt_type, plus, minus, ts):
        # 【新增】记录原始数据到 CSV
        storage.log_data(self.index, "PRIMARY", (current, evt_type, plus, minus, ts))

        if self.mode == "SINGLE":
            self.last_total = current
            self.last_plus = plus
            self.last_minus = minus
            self.score_updated.emit(current, plus, minus)
        else:
            self.pos_dev_val = current
            self._calculate_dual_score()

    def _on_secondary_data(self, current, evt_type, plus, minus, ts):
        # 【新增】记录原始数据到 CSV
        storage.log_data(self.index, "SECONDARY", (current, evt_type, plus, minus, ts))

        if self.mode == "DUAL":
            self.neg_dev_val = current
            self._calculate_dual_score()

    def _calculate_dual_score(self):
        final_score = self.pos_dev_val - self.neg_dev_val

        self.last_total = final_score
        self.last_plus = self.pos_dev_val
        self.last_minus = self.neg_dev_val

        self.score_updated.emit(final_score, self.pos_dev_val, self.neg_dev_val)