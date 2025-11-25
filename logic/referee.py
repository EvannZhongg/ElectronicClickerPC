# logic/referee.py
import asyncio
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from core.device_node import DeviceNode
from utils.storage import storage


class Referee(QObject):
    score_updated = pyqtSignal(int, int, int)

    def __init__(self, index, name, mode="SINGLE"):
        super().__init__()
        self.index = index
        self.name = name
        self.mode = mode

        self.primary_device: DeviceNode = None
        self.secondary_device: DeviceNode = None

        self.last_total = 0
        self.last_plus = 0
        self.last_minus = 0

        self.pos_dev_val = 0
        self.neg_dev_val = 0

        # 上下文：当前选手
        self.current_contestant = ""

    def set_devices(self, primary, secondary=None):
        self.primary_device = primary
        self.primary_device.data_received.connect(self._on_primary_data, Qt.ConnectionType.QueuedConnection)

        if self.mode == "DUAL" and secondary:
            self.secondary_device = secondary
            self.secondary_device.data_received.connect(self._on_secondary_data, Qt.ConnectionType.QueuedConnection)

    def set_contestant(self, name):
        """更新当前执裁的选手名称，用于日志记录"""
        self.current_contestant = name

    def request_reset(self):
        async def _do_reset():
            coros = []
            if self.primary_device:
                coros.append(self.primary_device.send_reset_command())
            if self.secondary_device:
                coros.append(self.secondary_device.send_reset_command())
            if coros:
                await asyncio.gather(*coros, return_exceptions=True)

        asyncio.create_task(_do_reset())

    def _on_primary_data(self, current, evt_type, plus, minus, ts):
        # 传入 current_contestant
        storage.log_data(self.index, "PRIMARY", (current, evt_type, plus, minus, ts), self.current_contestant)

        if self.mode == "SINGLE":
            self.last_total = current
            self.last_plus = plus
            self.last_minus = minus
            self.score_updated.emit(current, plus, minus)
        else:
            self.pos_dev_val = current
            self._calculate_dual_score()

    def _on_secondary_data(self, current, evt_type, plus, minus, ts):
        storage.log_data(self.index, "SECONDARY", (current, evt_type, plus, minus, ts), self.current_contestant)

        if self.mode == "DUAL":
            self.neg_dev_val = current
            self._calculate_dual_score()

    def _calculate_dual_score(self):
        final_score = self.pos_dev_val - self.neg_dev_val
        self.last_total = final_score
        self.last_plus = self.pos_dev_val
        self.last_minus = self.neg_dev_val
        self.score_updated.emit(final_score, self.pos_dev_val, self.neg_dev_val)