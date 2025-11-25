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
            # 构造时传入断开回调
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
            # 连接失败时，确保清理 client 对象，防止后续 disconnect 误判
            self.client = None

    def _on_disconnected(self, client):
        # 回调：连接断开
        self.is_connected = False
        self.status_changed.emit("Disconnected")

    # 【修复点】增强的 disconnect 方法
    async def disconnect(self):
        if self.client:
            try:
                # 只有当 Bleak 认为已连接时才尝试断开，且捕获所有异常
                if self.client.is_connected:
                    await self.client.disconnect()
            except Exception as e:
                # 忽略断开过程中的错误（例如 AssertionError），只打印日志
                print(f"Disconnect ignored error: {e}")
            finally:
                # 无论是否报错，都强制清理引用
                self.client = None
                self.is_connected = False

    async def send_reset_command(self):
        """向 ESP32 发送重置信号 (0x01)"""
        if not self.client or not self.is_connected:
            print("Device not connected, cannot reset.")
            return

        try:
            await self.client.write_gatt_char(CHARACTERISTIC_UUID, b'\x01', response=True)
            print(f"Reset command sent to {self.ble_device.name}")
        except Exception as e:
            print(f"Failed to send reset command: {e}")

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