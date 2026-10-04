"""脚本策略引擎。"""
import sys
import importlib
import traceback
from types import ModuleType
from typing import Any, cast
from collections.abc import Callable
from collections.abc import Sequence
from pathlib import Path
from datetime import datetime
from threading import Thread

from pandas import DataFrame

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine, LogEngine
from vnpy.trader.constant import Direction, Offset, OrderType, Interval
from vnpy.trader.object import (
    BaseData,
    OrderRequest,
    HistoryRequest,
    SubscribeRequest,
    TickData,
    OrderData,
    TradeData,
    PositionData,
    AccountData,
    ContractData,
    LogData,
    BarData,
    CancelRequest
)
from vnpy.trader.datafeed import BaseDatafeed, get_datafeed


APP_NAME = "ScriptTrader"

EVENT_SCRIPT_LOG = "eScriptLog"


class ScriptEngine(BaseEngine):
    """脚本策略引擎。"""
    setting_filename: str = "script_trader_setting.json"

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """初始化脚本线程和数据服务，并把日志注册到脚本日志事件。"""
        super().__init__(main_engine, event_engine, APP_NAME)

        self.strategy_active: bool = False
        self.strategy_thread: Thread | None = None

        self.datafeed: BaseDatafeed = get_datafeed()

        log_engine: LogEngine = cast(LogEngine, self.main_engine.get_engine("log"))
        log_engine.register_log(EVENT_SCRIPT_LOG)

    def init(self) -> None:
        """启动策略引擎"""
        result: bool = self.datafeed.init()
        if result:
            self.write_log("数据服务初始化成功")

    def start_strategy(self, script_path: str) -> None:
        """运行策略线程中的策略方法"""
        if self.strategy_active:
            return
        self.strategy_active = True

        self.strategy_thread = Thread(
            target=self.run_strategy, args=(script_path,))
        self.strategy_thread.start()

        self.write_log("策略交易脚本启动")

    def run_strategy(self, script_path: str) -> None:
        """加载策略脚本并调用run函数"""
        path: Path = Path(script_path)
        sys.path.append(str(path.parent))

        script_name: str = path.parts[-1]
        module_name: str = script_name.replace(".py", "")

        try:
            module: ModuleType = importlib.import_module(module_name)
            importlib.reload(module)
            module.run(self)
        except Exception:
            msg: str = f"触发异常已停止\n{traceback.format_exc()}"
            self.write_log(msg)

    def stop_strategy(self) -> None:
        """停止运行中的策略"""
        if not self.strategy_active:
            return
        self.strategy_active = False

        if self.strategy_thread:
            self.strategy_thread.join()
        self.strategy_thread = None

        self.write_log("策略交易脚本停止")

    def connect_gateway(self, setting: dict, gateway_name: str) -> None:
        """按配置连接指定交易接口。"""
        self.main_engine.connect(setting, gateway_name)

    def send_order(
        self,
        vt_symbol: str,
        price: float,
        volume: float,
        direction: Direction,
        offset: Offset,
        order_type: OrderType
    ) -> str:
        """找不到合约时返回空字符串，否则按合约所属接口发出委托并返回委托号。"""
        contract: ContractData | None = self.get_contract(vt_symbol)
        if not contract:
            return ""

        req: OrderRequest = OrderRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            direction=direction,
            type=order_type,
            volume=volume,
            price=price,
            offset=offset,
            reference=APP_NAME
        )

        vt_orderid: str = self.main_engine.send_order(req, contract.gateway_name)
        return vt_orderid

    def subscribe(self, vt_symbols: Sequence[str]) -> None:
        """对能找到合约的本地代码逐个订阅行情。"""
        for vt_symbol in vt_symbols:
            contract: ContractData | None = self.main_engine.get_contract(vt_symbol)
            if contract:
                req: SubscribeRequest = SubscribeRequest(
                    symbol=contract.symbol,
                    exchange=contract.exchange
                )
                self.main_engine.subscribe(req, contract.gateway_name)

    def buy(
        self,
        vt_symbol: str,
        price: float,
        volume: float,
        order_type: OrderType = OrderType.LIMIT
    ) -> str:
        """以多头开仓发出委托。"""
        return self.send_order(vt_symbol, price, volume, Direction.LONG, Offset.OPEN, order_type)

    def sell(
        self,
        vt_symbol: str,
        price: float,
        volume: float,
        order_type: OrderType = OrderType.LIMIT
    ) -> str:
        """以空头平仓发出委托。"""
        return self.send_order(vt_symbol, price, volume, Direction.SHORT, Offset.CLOSE, order_type)

    def short(
        self,
        vt_symbol: str,
        price: float,
        volume: float,
        order_type: OrderType = OrderType.LIMIT
    ) -> str:
        """以空头开仓发出委托。"""
        return self.send_order(vt_symbol, price, volume, Direction.SHORT, Offset.OPEN, order_type)

    def cover(
        self,
        vt_symbol: str,
        price: float,
        volume: float,
        order_type: OrderType = OrderType.LIMIT
    ) -> str:
        """以多头平仓发出委托。"""
        return self.send_order(vt_symbol, price, volume, Direction.LONG, Offset.CLOSE, order_type)

    def cancel_order(self, vt_orderid: str) -> None:
        """找不到委托时直接返回，否则撤销该委托。"""
        order: OrderData | None = self.get_order(vt_orderid)
        if not order:
            return

        req: CancelRequest = order.create_cancel_request()
        self.main_engine.cancel_order(req, order.gateway_name)

    def get_tick(self, vt_symbol: str, use_df: bool = False) -> TickData | None:
        """查询单条行情，use_df 为真时转成 DataFrame。"""
        return cast(TickData | None, get_data(self.main_engine.get_tick, arg=vt_symbol, use_df=use_df))

    def get_ticks(self, vt_symbols: Sequence[str], use_df: bool = False) -> Sequence[TickData] | DataFrame | None:
        """逐个查询行情，use_df 为真时转成 DataFrame。"""
        ticks: list = []
        for vt_symbol in vt_symbols:
            tick: TickData | None = self.main_engine.get_tick(vt_symbol)
            ticks.append(tick)

        if not use_df:
            return ticks
        else:
            return to_df(ticks)

    def get_order(self, vt_orderid: str, use_df: bool = False) -> OrderData | None:
        """查询单笔委托，use_df 为真时转成 DataFrame。"""
        return cast(OrderData | None, get_data(self.main_engine.get_order, arg=vt_orderid, use_df=use_df))

    def get_orders(self, vt_orderids: Sequence[str], use_df: bool = False) -> Sequence[OrderData] | DataFrame | None:
        """逐个查询委托，use_df 为真时转成 DataFrame。"""
        orders: list = []
        for vt_orderid in vt_orderids:
            order: OrderData | None = self.main_engine.get_order(vt_orderid)
            orders.append(order)

        if not use_df:
            return orders
        else:
            return to_df(orders)

    def get_trades(self, vt_orderid: str, use_df: bool = False) -> Sequence[TradeData] | DataFrame | None:
        """收集指定委托号的成交，use_df 为真时转成 DataFrame。"""
        trades: list = []
        all_trades: list[TradeData] = self.main_engine.get_all_trades()

        for trade in all_trades:
            if trade.vt_orderid == vt_orderid:
                trades.append(trade)

        if not use_df:
            return trades
        else:
            return to_df(trades)

    def get_all_active_orders(self, use_df: bool = False) -> Sequence[OrderData] | DataFrame | None:
        """查询全部活动委托，use_df 为真时转成 DataFrame。"""
        return cast(
            Sequence[OrderData] | DataFrame | None,
            get_data(self.main_engine.get_all_active_orders, use_df=use_df)
        )

    def get_contract(self, vt_symbol: str, use_df: bool = False) -> ContractData | None:
        """查询合约，use_df 为真时转成 DataFrame。"""
        return cast(ContractData | None, get_data(self.main_engine.get_contract, arg=vt_symbol, use_df=use_df))

    def get_all_contracts(self, use_df: bool = False) -> Sequence[ContractData] | DataFrame | None:
        """查询全部合约，use_df 为真时转成 DataFrame。"""
        return cast(
            Sequence[ContractData] | DataFrame | None,
            get_data(self.main_engine.get_all_contracts, use_df=use_df)
        )

    def get_account(self, vt_accountid: str, use_df: bool = False) -> AccountData | None:
        """查询资金账户，use_df 为真时转成 DataFrame。"""
        return cast(AccountData | None, get_data(self.main_engine.get_account, arg=vt_accountid, use_df=use_df))

    def get_all_accounts(self, use_df: bool = False) -> Sequence[AccountData] | DataFrame | None:
        """查询全部资金账户，use_df 为真时转成 DataFrame。"""
        return cast(
            Sequence[AccountData] | DataFrame | None,
            get_data(self.main_engine.get_all_accounts, use_df=use_df)
        )

    def get_position(self, vt_positionid: str, use_df: bool = False) -> PositionData | None:
        """按持仓编号查询持仓，use_df 为真时转成 DataFrame。"""
        return cast(PositionData | None, get_data(self.main_engine.get_position, arg=vt_positionid, use_df=use_df))

    def get_position_by_symbol(self, vt_symbol: str, direction: Direction, use_df: bool = False) -> PositionData | None:
        """找不到合约时返回 None，否则按接口、合约和方向拼持仓编号再查询。"""
        contract: ContractData | None = self.main_engine.get_contract(vt_symbol)
        if not contract:
            return None

        vt_positionid: str = f"{contract.gateway_name}.{contract.vt_symbol}.{direction.value}"
        return cast(PositionData | None, get_data(self.main_engine.get_position, arg=vt_positionid, use_df=use_df))

    def get_all_positions(self, use_df: bool = False) -> Sequence[PositionData] | DataFrame | None:
        """查询全部持仓，use_df 为真时转成 DataFrame。"""
        return cast(
            Sequence[PositionData] | DataFrame | None,
            get_data(self.main_engine.get_all_positions, use_df=use_df)
        )

    def get_bars(
        self,
        vt_symbol: str,
        start_date: str,
        interval: Interval,
        use_df: bool = False
    ) -> Sequence[BarData] | DataFrame:
        """找不到合约时返回空列表，否则向数据服务查询从起始日期到当前的 K 线。"""
        contract: ContractData | None = self.main_engine.get_contract(vt_symbol)
        if not contract:
            return []

        start: datetime = datetime.strptime(start_date, "%Y%m%d")
        end: datetime = datetime.now()

        req: HistoryRequest = HistoryRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            start=start,
            end=end,
            interval=interval
        )

        bars: Sequence[BarData] | DataFrame = get_data(self.datafeed.query_bar_history, arg=req, use_df=use_df)
        return bars

    def write_log(self, msg: str) -> None:
        """打印日志并推送脚本日志事件。"""
        log: LogData = LogData(msg=msg, gateway_name=APP_NAME)
        print(f"{log.time}\t{log.msg}")

        event: Event = Event(EVENT_SCRIPT_LOG, log)
        self.event_engine.put(event)

    def send_notification(self, msg: str) -> None:
        """以脚本策略引擎通知为标题发送通知。"""
        subject: str = "脚本策略引擎通知"
        self.main_engine.send_notification(msg, subject)

    send_email = send_notification


def to_df(data_list: Sequence[BaseData]) -> DataFrame | None:
    """把数据列表转成 DataFrame，空列表返回 None。"""
    if not data_list:
        return None

    dict_list: list = [data.__dict__ for data in data_list if data]
    return DataFrame(dict_list)


def get_data(func: Callable, arg: Any = None, use_df: bool = False) -> Any:
    """arg 为空时直接调用函数，否则传入 arg；use_df 为真时把结果转成 DataFrame。"""
    if not arg:
        data = func()
    else:
        data = func(arg)

    if not use_df:
        return data
    elif data is None:
        return data
    else:
        if not isinstance(data, list):
            data = [data]
        return to_df(data)
