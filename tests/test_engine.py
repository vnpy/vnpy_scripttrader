from typing import cast

from vnpy.event import EventEngine
from vnpy.trader.constant import Direction, Exchange, Product
from vnpy.trader.engine import MainEngine
from vnpy.trader.object import ContractData, OrderRequest

from vnpy_scripttrader.engine import ScriptEngine


class FakeLogEngine:
    def register_log(self, event_type: str) -> None:
        self.event_type: str = event_type


class FakeMainEngine:
    def __init__(self, contract: ContractData | None) -> None:
        self.contract: ContractData | None = contract
        self.log_engine: FakeLogEngine = FakeLogEngine()
        self.order_requests: list[OrderRequest] = []
        self.gateway_names: list[str] = []

    def get_engine(self, engine_name: str) -> FakeLogEngine | None:
        if engine_name == "log":
            return self.log_engine
        return None

    def get_contract(self, vt_symbol: str) -> ContractData | None:
        if self.contract is not None and vt_symbol == self.contract.vt_symbol:
            return self.contract
        return None

    def send_order(self, req: OrderRequest, gateway_name: str) -> str:
        self.order_requests.append(req)
        self.gateway_names.append(gateway_name)
        return f"{gateway_name}.1"


class FakeEventEngine:
    def put(self, event: object) -> None:
        return None


def make_contract() -> ContractData:
    return ContractData(
        symbol="rb2510",
        exchange=Exchange.SHFE,
        name="rb2510",
        product=Product.FUTURES,
        size=10,
        pricetick=1,
        gateway_name="CTP",
    )


class TestBuyOrder:
    def test_buy_sends_order_request(self) -> None:
        contract: ContractData = make_contract()
        main_engine: FakeMainEngine = FakeMainEngine(contract)
        engine: ScriptEngine = ScriptEngine(
            cast(MainEngine, main_engine),
            cast(EventEngine, FakeEventEngine()),
        )
        price: float = 3500.0
        volume: float = 2.0

        orderid: str = engine.buy(contract.vt_symbol, price, volume)

        assert orderid == "CTP.1"
        assert main_engine.gateway_names == [contract.gateway_name]
        assert len(main_engine.order_requests) == 1
        req: OrderRequest = main_engine.order_requests[0]
        assert req.symbol == contract.symbol
        assert req.direction == Direction.LONG
        assert req.price == price
        assert req.volume == volume

    def test_buy_without_contract_does_not_send(self) -> None:
        main_engine: FakeMainEngine = FakeMainEngine(None)
        engine: ScriptEngine = ScriptEngine(
            cast(MainEngine, main_engine),
            cast(EventEngine, FakeEventEngine()),
        )

        orderid: str = engine.buy("rb2510.SHFE", 3500.0, 2.0)

        assert orderid == ""
        assert main_engine.order_requests == []
