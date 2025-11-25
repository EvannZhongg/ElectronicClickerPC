# ui/home_page.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QDialog, QTableWidget, \
    QTableWidgetItem, QHeaderView, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from utils.i18n import i18n
from utils.storage import storage


class HomePage(QWidget):
    start_project_requested = pyqtSignal()
    open_project_requested = pyqtSignal(str)  # 传递文件夹名

    def __init__(self):
        super().__init__()
        self.init_ui()
        i18n.language_changed.connect(self.update_texts)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(50, 100, 50, 100)
        main_layout.setSpacing(30)

        self.lbl_welcome = QLabel()
        self.lbl_welcome.setFont(QFont("Microsoft YaHei", 28, QFont.Weight.Bold))
        self.lbl_welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_welcome.setStyleSheet("color: #333;")

        # 按钮容器
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(40)

        # 新建项目按钮
        self.btn_new_project = QPushButton()
        self.btn_new_project.setMinimumSize(220, 180)
        self.btn_new_project.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_project.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-size: 22px;
                border-radius: 15px;
                font-weight: bold;
                padding: 20px;
            }
            QPushButton:hover { background-color: #2980b9; margin-top: 5px; }
        """)
        self.btn_new_project.clicked.connect(self.start_project_requested.emit)

        # 打开已有项目按钮
        self.btn_open_project = QPushButton()
        self.btn_open_project.setMinimumSize(220, 180)
        self.btn_open_project.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_project.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-size: 22px;
                border-radius: 15px;
                font-weight: bold;
                padding: 20px;
            }
            QPushButton:hover { background-color: #27ae60; margin-top: 5px; }
        """)
        self.btn_open_project.clicked.connect(self.show_project_selector)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_new_project)
        btn_layout.addWidget(self.btn_open_project)
        btn_layout.addStretch()

        main_layout.addStretch(1)
        main_layout.addWidget(self.lbl_welcome)
        main_layout.addSpacing(50)
        main_layout.addLayout(btn_layout)
        main_layout.addStretch(2)

        self.setLayout(main_layout)
        self.update_texts()

    def update_texts(self):
        self.lbl_welcome.setText(i18n.tr("app_title"))
        self.btn_new_project.setText(f"+ {i18n.tr('home_new_project')}")
        self.btn_open_project.setText(f"📂 {i18n.tr('home_open_project')}")

    def show_project_selector(self):
        dialog = ProjectSelectorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_folder:
            self.open_project_requested.emit(dialog.selected_folder)


class ProjectSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("title_open_project"))
        self.resize(600, 400)
        self.selected_folder = None

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([i18n.tr("col_proj_name"), i18n.tr("col_create_time")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.on_double_click)
        layout.addWidget(self.table)

        self.projects = storage.list_projects()
        if not self.projects:
            layout.addWidget(QLabel(i18n.tr("lbl_no_projects")))
            self.table.setVisible(False)
        else:
            self.table.setRowCount(len(self.projects))
            for i, p in enumerate(self.projects):
                self.table.setItem(i, 0, QTableWidgetItem(p['name']))
                self.table.setItem(i, 1, QTableWidgetItem(p['time']))
                self.table.item(i, 0).setData(Qt.ItemDataRole.UserRole, p['folder'])

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton(i18n.tr("btn_cancel"))
        btn_cancel.clicked.connect(self.reject)

        btn_open = QPushButton(i18n.tr("btn_open"))
        btn_open.clicked.connect(self.confirm_selection)
        btn_open.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_open)
        layout.addLayout(btn_layout)

    def on_double_click(self, item):
        self.confirm_selection()

    def confirm_selection(self):
        row = self.table.currentRow()
        if row >= 0:
            self.selected_folder = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.accept()