# utils/i18n.py
from PyQt6.QtCore import QObject, pyqtSignal
from utils.app_settings import app_settings


class I18nManager(QObject):
    language_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_lang = app_settings.get("language")

        self.translations = {
            "zh": {
                "app_title": "电子计分系统 PC端",
                # ... 菜单 ...
                "menu_settings": "设置",
                "menu_language": "语言选择",
                "menu_preferences": "偏好设置...",  # 【新增】
                "menu_help": "帮助",
                "menu_project": "项目",

                # ... 偏好设置对话框 ...
                "prefs_title": "偏好设置",
                "tab_shortcuts": "快捷键设置",
                "lbl_reset_all_shortcut": "全局重置(清零)快捷键:",

                # ... 通用按钮 ...
                "btn_save": "保存",
                "btn_cancel": "取消",

                # ... 原有其他翻译保持不变 ...
                "home_new_project": "新建计分项目",
                "btn_back": "返回",
                "btn_next": "下一步",
                "btn_finish": "完成配置",
                "btn_rescan": "重新扫描",
                "wiz_p1_title": "步骤 1/2: 项目设置",
                "lbl_proj_name": "项目名称:",
                "lbl_game_mode": "比赛模式:",
                "mode_single_player": "单人模式 (1位裁判)",
                "mode_multi_player": "多人模式 (多位裁判)",
                "lbl_ref_count": "裁判人数:",
                "wiz_p2_title": "步骤 2/2: 绑定裁判设备",
                "status_scanning": "正在扫描蓝牙设备...",
                "status_found": "扫描完成，找到 {} 个设备",
                "status_no_dev": "未找到可用设备",
                "header_referee": "裁判",
                "header_mode": "计分模式",
                "header_dev_pri": "主设备 (正分/总分)",
                "header_dev_sec": "副设备 (负分)",
                "mode_single_dev": "单机模式",
                "mode_dual_dev": "双机联动",
                "placeholder_select": "请选择设备...",
                "referee_name": "裁判",
                "mode_single": "单机",
                "mode_dual": "双机",
                "score_total": "总分",
                "score_plus": "正分",
                "score_minus": "负分",
                "status_waiting": "等待连接...",
                "status_connected": "已连接",
                "status_disconnected": "已断开",
                "device_primary": "主设备",
                "device_secondary": "副设备",
                "btn_stop_match": "结束比赛 / 返回首页",
                "msg_duplicate_dev": "错误：设备 {} 被重复选择！",
                "msg_select_all": "请为所有启用的位置选择设备！",
                "dash_title": "实时计分看板",
                "btn_overlay": "开启悬浮窗模式",
                "title_select_window": "选择要附着的窗口",
                "lbl_window_list": "当前活动窗口列表:",
                "btn_confirm_overlay": "进入悬浮模式",
                "btn_exit_overlay": "退出悬浮 (还原)",
                "overlay_ref_format": "裁判{}: 总{} (+{} / -{})"
            },
            "en": {
                "app_title": "Electronic Clicker System",
                # ... Menus ...
                "menu_settings": "Settings",
                "menu_language": "Language",
                "menu_preferences": "Preferences...",  # 【New】
                "menu_help": "Help",
                "menu_project": "Project",

                # ... Preferences Dialog ...
                "prefs_title": "Preferences",  # 【New】
                "tab_shortcuts": "Shortcuts",  # 【New】
                "lbl_reset_all_shortcut": "Global Reset Shortcut:",  # 【New】

                "btn_save": "Save",
                "btn_cancel": "Cancel",

                # ... (Keep existing translations) ...
                "home_new_project": "New Scoring Project",
                "btn_back": "Back",
                "btn_next": "Next",
                "btn_finish": "Finish",
                "btn_rescan": "Rescan",
                "wiz_p1_title": "Step 1/2: Project Settings",
                "lbl_proj_name": "Project Name:",
                "lbl_game_mode": "Game Mode:",
                "mode_single_player": "Single Player (1 Referee)",
                "mode_multi_player": "Multiplayer (Multiple Referees)",
                "lbl_ref_count": "Referee Count:",
                "wiz_p2_title": "Step 2/2: Bind Devices",
                "status_scanning": "Scanning Bluetooth devices...",
                "status_found": "Scan complete. Found {} devices.",
                "status_no_dev": "No devices found",
                "header_referee": "Referee",
                "header_mode": "Mode",
                "header_dev_pri": "Primary (Plus/Total)",
                "header_dev_sec": "Secondary (Minus)",
                "mode_single_dev": "Single Device",
                "mode_dual_dev": "Dual Device",
                "placeholder_select": "Select Device...",
                "referee_name": "Referee",
                "mode_single": "Single",
                "mode_dual": "Dual",
                "score_total": "Total",
                "score_plus": "Plus",
                "score_minus": "Minus",
                "status_waiting": "Waiting...",
                "status_connected": "Connected",
                "status_disconnected": "Disconnected",
                "device_primary": "Primary",
                "device_secondary": "Secondary",
                "btn_stop_match": "End Match / Back to Home",
                "msg_duplicate_dev": "Error: Device {} is selected multiple times!",
                "msg_select_all": "Please select devices for all slots!",
                "dash_title": "Live Scoreboard",
                "btn_overlay": "Floating Overlay Mode",
                "title_select_window": "Select Target Window",
                "lbl_window_list": "Active Windows:",
                "btn_confirm_overlay": "Start Overlay",
                "btn_exit_overlay": "Exit Overlay (Restore)",
                "overlay_ref_format": "Ref{}: T{} (+{} / -{})"
            }
        }

    def set_language(self, lang_code):
        if lang_code in self.translations:
            self.current_lang = lang_code
            app_settings.set("language", lang_code)
            self.language_changed.emit()

    def tr(self, key, *args):
        text = self.translations.get(self.current_lang, {}).get(key, key)
        if args:
            return text.format(*args)
        return text


i18n = I18nManager()