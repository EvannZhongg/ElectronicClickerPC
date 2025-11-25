# core/device_node.py
import asyncio
from bleak import BleakClient
from PyQt6.QtCore import QObject, pyqtSignal
from core.protocol import parse_notification_data
from config import CHARACTERISTIC_UUID


class DeviceNode(QObject):
    # 信号定义：传递基础数据类型 (current, type, plus, minus, timestamp)
    data_received = pyqtSignal(int, int, int, int, int)
    status_changed = pyqtSignal(str)

    def __init__(self, ble_device):
        super().__init__()
        self.ble_device = ble_device
        self.client = None
        self.is_connected = False

    async def connect(self):
        self.status_changed.emit("Connecting...")
        try:
            # 【关键修改】在构造时直接传入断开回调，避免 Attribute 错误
            self.client = BleakClient(
                self.ble_device,
                disconnected_callback=self._on_disconnected
            )

            await self.client.connect()
            self.is_connected = True
            self.status_changed.emit("Connected")

            await self.client.start_notify(CHARACTERISTIC_UUID, self._notification_handler)

        except Exception as e:
            self.is_connected = False
            self.status_changed.emit(f"Conn Error: {str(e)}")

    def _on_disconnected(self, client):
        # 回调：连接断开
        self.is_connected = False
        self.status_changed.emit("Disconnected")

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()

    def _notification_handler(self, sender, data):
        """运行在蓝牙后台线程，只负责转发信号"""
        try:
            event = parse_notification_data(data)
            # 发射解包后的基础数据
            self.data_received.emit(
                event.current_total,
                event.event_type,
                event.total_plus,
                event.total_minus,
                event.timestamp_ms
            )
        except Exception as e:
            print(f"Callback Error: {e}")