from pathlib import Path

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore
from vnpy.trader.object import LogData
from ..engine import APP_NAME, EVENT_SCRIPT_LOG, BaseEngine


class ScriptManager(QtWidgets.QWidget):
    """"""
    signal_log: QtCore.pyqtSignal = QtCore.pyqtSignal(Event)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__()

        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine

        self.script_engine: BaseEngine = main_engine.get_engine(APP_NAME)

        self.script_path: str = ""

        self.init_ui()
        self.register_event()

        self.script_engine.init()

    def init_ui(self) -> None:
        """"""
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
        """"""
        self.signal_log.connect(self.process_log_event)

        self.event_engine.register(EVENT_SCRIPT_LOG, self.signal_log.emit)

    def show(self) -> None:
        """"""
        self.showMaximized()

    def process_log_event(self, event: Event) -> None:
        """"""
        log: LogData = event.data
        msg: str = f"{log.time}\t{log.msg}"
        self.log_monitor.append(msg)

    def start_script(self) -> None:
        """"""
        if self.script_path:
            self.script_engine.start_strategy(self.script_path)

    def stop_script(self) -> None:
        """"""
        self.script_engine.stop_strategy()

    def select_script(self) -> None:
        """"""
        cwd: str = str(Path.cwd())

        path, type_ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            u"载入策略脚本",
            cwd,
            "Python File(*.py)"
        )

        if path:
            self.script_path = path
            self.strategy_line.setText(path)
