"""脚本策略管理界面。"""
from pathlib import Path

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore
from vnpy.trader.object import LogData
from ..engine import APP_NAME, EVENT_SCRIPT_LOG, BaseEngine


class ScriptManager(QtWidgets.QWidget):
    """脚本策略管理界面。"""
    signal_log: QtCore.Signal = QtCore.Signal(Event)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """取得脚本引擎，初始化界面并调用引擎的 init。"""
        super().__init__()

        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine

        self.script_engine: BaseEngine = main_engine.get_engine(APP_NAME)

        self.script_path: str = ""

        self.init_ui()
        self.register_event()

        self.script_engine.init()

    def init_ui(self) -> None:
        """搭建脚本路径、打开、启动、停止、清空和日志框。"""
        self.setWindowTitle("脚本策略")

        start_button: QtWidgets.QPushButton = QtWidgets.QPushButton("启动")
        start_button.clicked.connect(self.start_script)

        stop_button: QtWidgets.QPushButton = QtWidgets.QPushButton("停止")
        stop_button.clicked.connect(self.stop_script)

        select_button: QtWidgets.QPushButton = QtWidgets.QPushButton("打开")
        select_button.clicked.connect(self.select_script)

        self.strategy_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()

        self.log_monitor: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.log_monitor.setReadOnly(True)

        clear_button: QtWidgets.QPushButton = QtWidgets.QPushButton("清空")
        clear_button.clicked.connect(self.log_monitor.clear)

        hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.strategy_line)
        hbox.addWidget(select_button)
        hbox.addWidget(start_button)
        hbox.addWidget(stop_button)
        hbox.addStretch()
        hbox.addWidget(clear_button)

        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(self.log_monitor)

        self.setLayout(vbox)

    def register_event(self) -> None:
        """把脚本日志事件接到日志框。"""
        self.signal_log.connect(self.process_log_event)

        self.event_engine.register(EVENT_SCRIPT_LOG, self.signal_log.emit)

    def show(self) -> None:
        """最大化显示窗口。"""
        self.showMaximized()

    def process_log_event(self, event: Event) -> None:
        """把日志时间和内容追加到日志框。"""
        log: LogData = event.data
        msg: str = f"{log.time}\t{log.msg}"
        self.log_monitor.append(msg)

    def start_script(self) -> None:
        """已选择脚本路径时启动该脚本。"""
        if self.script_path:
            self.script_engine.start_strategy(self.script_path)

    def stop_script(self) -> None:
        """停止正在运行的脚本。"""
        self.script_engine.stop_strategy()

    def select_script(self) -> None:
        """选择 Python 脚本并显示其路径。"""
        cwd: str = str(Path.cwd())

        path, type_ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "载入策略脚本",
            cwd,
            "Python File(*.py)"
        )

        if path:
            self.script_path = path
            self.strategy_line.setText(path)
