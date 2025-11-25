# logic/referee.py
import asyncio
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from core.device_node import DeviceNode
from utils.storage import storage


class Referee(QObject):
    score_updated = pyqtSignal(int, int, int)

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

    # 【核心修复】修改了这里的异步调度逻辑
    def request_reset(self):
        """触发关联设备的重置逻辑"""

        async def _do_reset():
            # 收集需要执行的协程
            coros = []
            if self.primary_device:
                coros.append(self.primary_device.send_reset_command())

            if self.secondary_device:
                coros.append(self.secondary_device.send_reset_command())

            if coros:
                # 使用 asyncio.gather 来并发执行协程，它可以正确处理 coroutines 列表
                # return_exceptions=True 防止一个失败影响另一个
                await asyncio.gather(*coros, return_exceptions=True)

        # 在事件循环中调度执行这个包装任务
        asyncio.create_task(_do_reset())

    def _on_primary_data(self, current, evt_type, plus, minus, ts):
        # 记录原始数据到 CSV
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
        # 记录原始数据到 CSV
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