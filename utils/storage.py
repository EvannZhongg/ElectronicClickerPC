# utils/storage.py
import os
import json
import csv
from datetime import datetime


class ProjectStorage:
    # ... (前部分保持不变) ...
    def __init__(self, base_dir="projects"):
        self.base_dir = os.path.join(os.getcwd(), base_dir)
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        self.current_project_path = None

    def create_project(self, project_name, referees_data, tournament_data=None):
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join([c for c in project_name if c.isalnum() or c in (' ', '_', '-')]).strip()
        folder_name = f"{timestamp_str}_{safe_name}"

        self.current_project_path = os.path.join(self.base_dir, folder_name)
        os.makedirs(self.current_project_path, exist_ok=True)

        config = {
            "project_name": project_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "referees": referees_data,
            "tournament_data": tournament_data or {}
        }

        self._write_config(config)
        self._init_all_csvs(referees_data)

        print(f"Project initialized: {self.current_project_path}")
        return self.current_project_path

    def update_project_config(self, project_name, referees_data, tournament_data=None):
        if not self.current_project_path or not os.path.exists(self.current_project_path):
            print("Warning: Project path lost, creating new instead.")
            return self.create_project(project_name, referees_data, tournament_data)

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        json_path = os.path.join(self.current_project_path, "config.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                    created_at = old_data.get("created_at", created_at)
            except:
                pass

        config = {
            "project_name": project_name,
            "created_at": created_at,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "referees": referees_data,
            "tournament_data": tournament_data or {}
        }

        self._write_config(config)
        self._init_all_csvs(referees_data)
        print(f"Project updated: {self.current_project_path}")
        return self.current_project_path

    def _write_config(self, config):
        if not self.current_project_path: return
        json_path = os.path.join(self.current_project_path, "config.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    def _init_all_csvs(self, referees_data):
        for ref in referees_data:
            csv_path = os.path.join(self.current_project_path, f"referee_{ref['index']}.csv")
            if not os.path.exists(csv_path):
                self._init_raw_log_csv(ref['index'])

        results_path = os.path.join(self.current_project_path, "results.csv")
        if not os.path.exists(results_path):
            self._init_results_csv()

    def _init_raw_log_csv(self, ref_index):
        if not self.current_project_path: return
        file_path = os.path.join(self.current_project_path, f"referee_{ref_index}.csv")
        headers = ["SystemTime", "BLE_Timestamp", "DeviceRole", "Contestant", "CurrentTotal", "EventType", "TotalPlus",
                   "TotalMinus"]
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

    def _init_results_csv(self):
        if not self.current_project_path: return
        file_path = os.path.join(self.current_project_path, "results.csv")
        headers = ["Group", "Contestant", "FinalScore", "Details", "Timestamp"]
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

    def log_data(self, ref_index, role, event_data, contestant_name=""):
        if not self.current_project_path: return
        file_path = os.path.join(self.current_project_path, f"referee_{ref_index}.csv")
        current, evt_type, plus, minus, ble_ts = event_data
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            ble_ts, role, contestant_name, current, evt_type, plus, minus
        ]
        try:
            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            print(f"CSV Log Error: {e}")

    def save_result(self, group, contestant, total_score, details):
        if not self.current_project_path: return
        file_path = os.path.join(self.current_project_path, "results.csv")
        row = [group, contestant, total_score, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        try:
            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            print(f"Save Result Error: {e}")

    # --- 新增方法 ---
    def get_existing_contestants(self):
        """
        扫描当前项目下所有 referee_*.csv，返回有过记录的选手名称集合。
        只要选手出现在 CSV 中（说明接收过 BLE 数据），即视为已打分。
        """
        scored_set = set()
        if not self.current_project_path:
            return scored_set

        # 遍历目录下所有 referee_ 开头的 csv
        try:
            files = os.listdir(self.current_project_path)
            for file in files:
                if file.startswith("referee_") and file.endswith(".csv"):
                    path = os.path.join(self.current_project_path, file)
                    with open(path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            name = row.get("Contestant", "").strip()
                            if name:
                                scored_set.add(name)
        except Exception as e:
            print(f"Error scanning logs: {e}")

        return scored_set

    # ... (list_projects 等保持不变) ...
    def list_projects(self):
        projects = []
        if not os.path.exists(self.base_dir): return projects
        for folder in os.listdir(self.base_dir):
            folder_path = os.path.join(self.base_dir, folder)
            config_path = os.path.join(folder_path, "config.json")
            if os.path.isdir(folder_path) and os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        projects.append({
                            "name": data.get("project_name", folder),
                            "time": data.get("created_at", ""),
                            "path": folder_path,
                            "folder": folder
                        })
                except:
                    pass
        projects.sort(key=lambda x: x['time'], reverse=True)
        return projects

    def load_project_config(self, folder_name):
        path = os.path.join(self.base_dir, folder_name, "config.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def set_current_project(self, folder_name):
        path = os.path.join(self.base_dir, folder_name)
        if os.path.exists(path):
            self.current_project_path = path


storage = ProjectStorage()