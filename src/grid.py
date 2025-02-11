
from typing import (
    Optional,
    List
)
from decimal import Decimal
from src.kraken_api import (
    AccountData,
    MarketData,
    Trading,
    # TradableAssetPair,
    Order
)
# from src.portfolio import Portfolio
from src.get_logger import get_logger


class Rung:
    price: Decimal
    volume: Decimal
    order: Optional[Order] = None


class GridStrategy:
    pair: str

    open_orders: List[Order] = []
    closed_orders: List[Order] = []

    rungs: List[Rung]
    rung_count: int
    base_price: Decimal
    percentage: Decimal

    current_ask: Decimal
    current_bid: Decimal

    account_client = AccountData()
    market_client = MarketData()
    trading_client = Trading()

    def __init__(
        self,
        pair: str,
        base_price: Decimal,
        percentage: Decimal,
        rung_count: int
    ):
        self.logger = get_logger(f'{pair.replace("/", "")}')
        self.logger.info(
            f"Initialising GridStrategy for pair: {pair} "
            f"with base price of {base_price} and "
            f"rungs spread {percentage * 100}% apart."
        )

        # ensure valid arguments
        if base_price <= 0:
            self.logger.error("Error: base_price must be positive.")
            raise ValueError("Error: base_price must be positive.")
        if percentage <= 0:
            self.logger.error("Error: percentage must be greater than 0.")
            raise ValueError("Error: percentage must be greater than 0.")

        # ensure pair is valid
        pair_list = self.market_client.get_tradable_asset_pairs(pair)
        if not any(p.name == pair for p in pair_list):
            raise ValueError(
                f"Error: {pair} does not represent a viable asset pair."
            )
        self.pair = pair

        self.update_price()

    def update_price(self):
        # gets latest ask/bid
        ticker_info = self.market_client.get_ticker_information(self.pair)
        self.current_ask = ticker_info.a[0]
        self.current_bid = ticker_info.b[0]
        self.logger.info(
            f"{self.pair} price spread updated. "
            f"Ask: {self.current_ask}, "
            f"Bid: {self.current_bid}."
        )
