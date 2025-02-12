
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

    def __init__(
        self,
        price: Decimal,
        volume: Decimal
    ):
        self.price = price
        self.volume = volume


class GridStrategy:
    pair: str

    open_orders: List[Order]
    closed_orders: List[Order]

    rungs: List[Rung]
    rung_count: int
    base_price: Decimal
    percentage: Decimal
    total_volume: Decimal

    current_ask: Decimal
    current_bid: Decimal

    account_client: AccountData
    market_client: MarketData
    trading_client: Trading

    def __init__(
        self,
        pair: str,
        base_price: Decimal,
        percentage: Decimal,
        total_volume: Decimal,
        rung_count: int
    ):
        self.logger = get_logger(f'{pair.replace("/", "")}')
        self.logger.info(
            f"Initialising GridStrategy for pair: {pair} "
            f"with base price of {base_price} and "
            f"rungs spread {percentage * 100}% apart."
        )

        # init clients
        self.account_client = AccountData()
        self.market_client = MarketData()
        self.trading_client = Trading()

        # ensure valid arguments
        if base_price <= 0:
            message = (
                "Error: base_price must be positive, "
                f"was {base_price}.")
            self.logger.error(message)
            raise ValueError(message)
        if percentage <= 0:
            message = (
                "Error: percentage must be greater than 0, "
                f"was {percentage}."
            )
            self.logger.error(message)
            raise ValueError(message)
        if total_volume <= 0:
            message = (
                "Error: total_volume must be greater than 0, "
                f"was {total_volume}."
            )
            self.logger.error(message)
            raise ValueError(message)
        if rung_count < 2:
            message = (
                "Error: rung_count must be greater than 2, "
                f"was {rung_count}."
            )
            self.logger.error(message)
            raise ValueError(message)
        
        # save arguments
        self.base_price = base_price
        self.percentage = percentage
        self.total_volume = total_volume
        self.rung_count = rung_count

        # create lists
        self.rungs = []
        self.open_orders = []
        self.closed_orders = []

        # ensure pair is valid
        pair_list = self.market_client.get_tradable_asset_pairs(pair)
        if not any(p.name == pair for p in pair_list):
            raise ValueError(
                f"Error: {pair} does not represent a viable asset pair."
            )
        self.pair = pair

        # get price data
        self.update_price()

        # set up rungs
        for i in range(rung_count):
            price = base_price * ((1 + self.percentage) ** i)
            volume = self.total_volume / self.rung_count
            self.rungs.append(Rung(
                price=price,
                volume=volume
            ))

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
