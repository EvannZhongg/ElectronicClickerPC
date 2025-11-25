# utils/storage.py
import os
import json
import csv
from datetime import datetime


class ProjectStorage:
    def __init__(self, base_dir="projects"):
        # 默认保存到运行目录下的 projects 文件夹
        self.base_dir = os.path.join(os.getcwd(), base_dir)
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        self.current_project_path = None

    def create_project(self, project_name, referees_data):
        """
        创建项目文件夹和配置文件
        project_name: 项目名称
        referees_data: 裁判配置列表 (用于 config.json)
        """
        # 1. 生成唯一文件夹名: YYYYMMDD_HHMMSS_ProjectName
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 清理文件名非法字符
        safe_name = "".join([c for c in project_name if c.isalnum() or c in (' ', '_', '-')]).strip()
        folder_name = f"{timestamp_str}_{safe_name}"

        self.current_project_path = os.path.join(self.base_dir, folder_name)
        os.makedirs(self.current_project_path, exist_ok=True)

        # 2. 保存 config.json
        config = {
            "project_name": project_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "referees": referees_data
        }

        json_path = os.path.join(self.current_project_path, "config.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        # 3. 为每个裁判初始化 CSV 文件
        for ref in referees_data:
            self._init_csv(ref['index'])

        print(f"Project initialized: {self.current_project_path}")
        return self.current_project_path

    def _init_csv(self, ref_index):
        if not self.current_project_path: return
        file_path = os.path.join(self.current_project_path, f"referee_{ref_index}.csv")

        # CSV 表头
        # SystemTime: PC系统时间
        # BLE_Timestamp: ESP32传来的时间戳
        # DeviceRole: PRIMARY(主)/SECONDARY(副)
        # EventType: 1(加)/-1(减)/0(重置)
        headers = ["SystemTime", "BLE_Timestamp", "DeviceRole", "CurrentTotal", "EventType", "TotalPlus", "TotalMinus"]

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

    def log_data(self, ref_index, role, event_data):
        """
        实时追加数据到 CSV
        """
        if not self.current_project_path: return

        file_path = os.path.join(self.current_project_path, f"referee_{ref_index}.csv")

        # 解包数据
        current, evt_type, plus, minus, ble_ts = event_data

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],  # 精确到毫秒
            ble_ts,
            role,
            current,
            evt_type,
            plus,
            minus
        ]

        try:
            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            print(f"CSV Log Error: {e}")


# 全局单例
storage = ProjectStorage()