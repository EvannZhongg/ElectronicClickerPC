# main.py
import sys
import asyncio
import faulthandler  # 1. 导入模块

from PyQt6.QtWidgets import QApplication
from qasync import QEventLoop
from ui.main_window import MainWindow

def main():
    # 2. 启用错误处理，如果再崩溃，控制台会打印具体是哪行代码导致的
    faulthandler.enable()

    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()