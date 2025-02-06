
import requests
from requests.exceptions import RequestException
import time
import hmac
import hashlib
import base64
import urllib
import os
from abc import ABC
from typing import Optional, List, Tuple
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from src.logger import get_logger


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    ICEBERG = "iceberg"
    STOP_LOSS = "stop-loss"
    TAKE_PROFIT = "take-profit"
    STOP_LOSS_LIMIT = "stop-loss-limit"
    TAKE_PROFIT_LIMIT = "take-profit-limit"
    TRAILING_STOP = "trailing-stop"
    TRAILING_STOP_LIMIT = "trailing-stop-limit"
    SETTLE_POSITION = "settle-position"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderTrigger(str, Enum):
    INDEX = "index"
    LAST = "last"


class STPType(str, Enum):
    CANCEL_NEWEST = "cancel-newest"
    CANCEL_OLDEST = "cancel-oldest"
    CANCEL_BOTH = "cancel-both"


class TimeInForce(str, Enum):
    GTC = "GTC"
    IOC = "IOC"
    GTD = "GTD"


class OrderStatusType(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "canceled"
    EXPIRED = "expired"


class TimeData(BaseModel):
    unixtime: int
    rfc1123: str


class SystemStatusEnum(str, Enum):
    ONLINE = "online"
    MAINTENENCE = "maintenance"
    CANCEL_ONLY = "cancel_only"
    POST_ONYL = "post_only"


class SystemStatus(BaseModel):
    status: SystemStatusEnum
    timestamp: str


class AssetStatus(str, Enum):
    ENABLED = "enabled"
    DEPOSIT_ONLY = "deposit_only"
    WITHDRAWAL_ONLY = "withdrawal_only"
    FUNDING_TEMPORARILY_DISABLED = "funding_temporarily_disabled"


class AssetInfo(BaseModel):
    name: str
    aclass: str
    altname: str
    decimals: int
    display_decimals: int
    collateral_value: float
    status: AssetStatus


class TradableAssetInfo(str, Enum):
    INFO = "info"
    LEVERAGE = "leverage"
    FEES = "fees"
    MARGIN = "margin"


class TradableAssetPair(BaseModel):
    name: str
    altname: str
    wsname: str
    aclass_base: str
    base: str
    aclass_quote: str
    quote: str
    lot: str
    cost_decimals: int
    pair_decimals: int
    lot_decimals: int
    lot_multiplier: int
    leverage_buy: List[int]
    leverage_sell: List[int]
    fees: List[Tuple[int, Decimal]]
    fees_maker: List[Tuple[int, Decimal]]
    fee_volume_currency: str
    margin_call: int
    margin_stop: int
    ordermin: Decimal
    costmin: Decimal
    tick_size: Decimal
    status: SystemStatusEnum
    long_position_limit: int
    short_position_limit: int


class TickerInfo(BaseModel):
    name: str
    a: List[str]  # ask
    b: List[str]  # bid
    c: List[str]  # last trade closed
    v: List[str]  # volume
    p: List[str]  # volume weighted average price
    t: List[int]  # number of trades in prev 24h
    l: List[str]  # low
    h: List[str]  # high
    o: str        # todays open price


class OHLCTickData(BaseModel):
    time: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    vwap: Decimal
    volume: Decimal
    count: int


class OHLCData(BaseModel):
    name: str
    ticks: List[OHLCTickData]
    last: int


class OrderBookAsk(BaseModel):
    price: Decimal
    volume: Decimal
    timestamp: int


class OrderBookBid(BaseModel):
    price: Decimal
    volume: Decimal
    timestamp: int


class OrderBook(BaseModel):
    name: str
    asks: List[OrderBookAsk]
    bids: List[OrderBookBid]


class RecentTradeTickData(BaseModel):
    price: Decimal
    volume: Decimal
    time: float
    order_side: str
    order_type: str
    miscellaneous: str
    trade_id: int


class RecentTrades(BaseModel):
    name: str
    tick_data: List[RecentTradeTickData]
    last: str


class SpreadData(BaseModel):
    time: int
    bid: str
    ask: str


class RecentSpreads(BaseModel):
    pair: str
    spread_data: List[SpreadData]
    last: int


class AssetBalance(BaseModel):
    name: str
    amount: Decimal


class ExtendedAssetBalance(BaseModel):
    name: str
    balance: Decimal
    credit: Optional[Decimal] = None
    credit_used: Optional[Decimal] = None
    hold_trade: Decimal


class TradeBalance(BaseModel):
    eb: Decimal = Decimal("0.0")
    # Equivalent balance (combined balance of all currencies)
    tb: Decimal = Decimal("0.0")
    # Trade balance (combined balance of all equity currencies)
    m: Decimal = Decimal("0.0")
    # Margin amount of open positions
    n: Decimal = Decimal("0.0")
    # Unrealized net profit/loss of open positions
    c: Decimal = Decimal("0.0")
    # Cost basis of open positions
    v: Decimal = Decimal("0.0")
    # Current floating valuation of open positions
    e: Decimal = Decimal("0.0")
    # Equity: trade balance + unrealized net profit/loss
    mf: Decimal = Decimal("0.0")
    # Free margin: Equity - initial margin
    # (maximum margin available to open new positions)
    ml: Decimal = Decimal("0.0")
    # Margin level: (equity / initial margin) * 100
    uv: Decimal = Decimal("0.0")
    # Unexecuted value: Value of unfilled and partially filled orders


class OrderDescription(BaseModel):
    pair: str
    type: OrderSide
    ordertype: OrderType
    price: Decimal
    price2: Optional[Decimal] = None
    leverage: Optional[str] = None
    order: Optional[str] = None
    close: Optional[str] = None

    @field_validator("*")
    def none_to_null(cls, value):
        return None if value == "none" else value


class Order(BaseModel):
    txid: str
    refid: Optional[str] = None
    userref: Optional[int] = None
    cl_ord_id: Optional[str] = None
    status: OrderStatusType
    opentm: Optional[float] = None
    starttm: Optional[float] = None
    closetm: Optional[float] = None
    expiretm: Optional[float] = None
    descr: OrderDescription
    vol: Optional[Decimal] = None
    vol_exec: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    fee: Optional[Decimal] = None
    price: Decimal
    stopprice: Optional[Decimal] = None
    limitprice: Optional[Decimal] = None
    trigger: Optional[OrderTrigger] = None
    margin: Optional[bool] = None
    misc: Optional[str] = None
    oflags: Optional[str] = None
    trades: List[str] = []
    sender_sub_id: Optional[str] = None
    reason: Optional[str] = None

    @field_validator("*")
    def none_to_null(cls, value):
        return None if value == "None" else value


class TradeType(str, Enum):
    ALL = "all"
    ANY_POSITION = "any position"
    CLOSED_POSITION = "closed position"
    CLOSING_POSITION = "closing position"
    NO_POSITION = "no position"


class Trade(BaseModel):
    txid: str
    ordertxid: str
    postxid: str
    pair: str
    time: float
    type: OrderSide
    ordertype: OrderType
    price: Decimal
    cost: Decimal
    fee: Decimal
    vol: Decimal
    margin: Optional[Decimal] = None
    leverage: Optional[str] = None
    misc: str
    ledgers: Optional[str] = None
    trade_id: int
    maker: bool
    posstatus: Optional[str] = None
    cprice: Optional[Decimal] = None
    ccost: Optional[Decimal] = None
    cfee: Optional[Decimal] = None
    cvol: Optional[Decimal] = None
    cmargin: Optional[Decimal] = None
    net: Optional[Decimal] = None
    trades: Optional[List[str]] = None


class FeeTierInfo(BaseModel):
    fee: Decimal
    min_fee: Decimal
    max_fee: Decimal
    next_fee: Decimal
    tier_volume: Decimal
    next_volume: Decimal


class TradeVolume(BaseModel):
    currency: str
    volume: Decimal
    fees: FeeTierInfo
    fees_maker: FeeTierInfo


class BaseAPI(ABC):
    _URI_path: str
    _URL_path: str
    _session: requests.Session

    def __init__(self) -> None:
        super().__init__()
        load_dotenv('.env')
        self._logger = get_logger('kraken')
        if not os.environ.get("API_SECRET"):
            self._logger.error("Error! API_SECRET is missing!")
            raise ValueError("Error! API_SECRET is missing!")
        if not os.environ.get("API_KEY"):
            self._logger.error("Error! API_KEY is missing!")
            raise ValueError("Error! API_KEY is missing!")
        self._session = requests.Session()

    def _generate_headers(self, URI: str, post_data: dict) -> dict:
        url_encoded_post_data = urllib.parse.urlencode(post_data)
        encoded = (str(post_data['nonce']) + url_encoded_post_data).encode()
        message = URI.encode() + hashlib.sha256(encoded).digest()
        signature = hmac.new(
            base64.b64decode(os.environ.get("API_SECRET")),
            message,
            hashlib.sha512
        )
        signature_digest = base64.b64encode(signature.digest())
        return {
            'API-Key': os.environ.get("API_KEY"),
            'API-Sign': signature_digest.decode()
        }

    def _create_signed_request(
            self,
            URI: str,
            URL: str,
            post_data: dict
            ) -> dict:
        headers = self._generate_headers(URI, post_data)
        self._logger.debug(f"Sending request to {URL} with data: {post_data}")
        try:
            response = self._session.post(URL, data=post_data, headers=headers)
            self._logger.info(f"Request sent to {URL}: {post_data}")
            response_data = response.json()
            self._logger.debug(f"Response received: {response_data}")
            return response_data
        except requests.exceptions.RequestException:
            raise ValueError(f"Failed to parse JSON response from {URL}")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to {URL} timed out")

    def _nonce(self) -> int:
        return int(time.time()*1000)

    def _get_response(self, endpoint: str, post_data: dict) -> dict:
        self._logger.info(f"Making API request to {endpoint}")
        response = None
        try:
            response = self._create_signed_request(
                self._URI_path + endpoint,
                self._URL_path + endpoint,
                post_data
            )
            return self._process_response(response)
        except Exception as e:
            self._logger.error(f"Error getting response: {e}")

    def _process_response(self, response: dict) -> dict:
        if not response:
            raise ValueError("No response received from API")
        if response.get("error"):
            error_message = ", ".join(response["error"])
            self._logger.error(f"API error: {error_message}")
            raise RequestException(f"API error: {error_message}")
        elif not response.get("result"):
            self._logger.error(f"Invalid response format: {response}")
            raise ValueError(f"Invalid response format: {response}")
        return response.get('result')

    def _enforce_precision(
            self,
            price: Decimal,
            precision: str = "0.0000"
            ) -> Decimal:
        quantizer = Decimal(precision)
        return price.quantize(quantizer, rounding=ROUND_DOWN)


class MarketData(BaseAPI):
    _URI_path: str = '/0/public/'
    _URL_path: str = 'https://api.kraken.com' + _URI_path

    def get_server_time(self) -> TimeData:
        endpoint = 'Time'
        post_data = {
            'nonce': self._nonce()
        }

        self._logger.info("Fetching server time from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            return TimeData(**response['result'])

        except Exception as e:
            self._logger.error(f"Error fetching server time: {e}")

    def get_system_status(self) -> SystemStatus:
        endpoint = 'SystemStatus'
        post_data = {
            'nonce': self._nonce()
        }

        self._logger.info("Fetching Kraken API system status...")

        try:
            response = self._get_response(endpoint, post_data)

            return SystemStatus(**response['result'])

        except Exception as e:
            self._logger.error(f"Error fetching system status: {e}")

    def get_asset_info(
            self,
            asset: Optional[str | List[str]] = None,
            aclass: Optional[str] = None
            ) -> List[AssetInfo]:
        endpoint = 'Assets'
        post_data = {
            'nonce': self._nonce(),
            'asset': ','.join(asset) if isinstance(asset, list) else asset,
            'aclass': aclass
        }

        self._logger.info("Fetching asset(s) info from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            assets = []
            for asset_symbol, asset_data in response['result'].items():
                if asset_symbol in (asset
                                    if isinstance(asset, list) else [asset]):
                    assets.append(AssetInfo(**asset_data, name=asset_symbol))

            return assets

        except Exception as e:
            self._logger.error(f"Error fetching asset info: {e}")

    def get_tradable_asset_pairs(
            self,
            pair: str,
            info: Optional[TradableAssetInfo] = None,
            country_code: Optional[str] = None
            ) -> List[TradableAssetPair]:
        endpoint = 'AssetPairs'
        post_data = {
            'nonce': self._nonce(),
            'pair': pair,
            'info': info,
            'country_code': country_code
        }

        self._logger.info("Fetching tradable asset pairs from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            asset_pairs = []
            for asset_symbol, asset_data in response['result'].items():
                asset_pairs.append(
                    TradableAssetPair(**asset_data, name=asset_symbol)
                )

            return asset_pairs

        except Exception as e:
            self._logger.error(f"Error fetching tradable asset pairs: {e}")

    def get_ticker_information(self, pair: Optional[str] = None) -> TickerInfo:
        endpoint = 'Ticker'
        post_data = {
            'nonce': self._nonce(),
            'pair': pair
        }

        self._logger.info("Fetching ticker information from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            tickers = []
            for asset_symbol, asset_data in response['result'].items():
                tickers.append(TickerInfo(**asset_data, name=asset_symbol))
            return tickers

        except Exception as e:
            self._logger.error(f"Error fetching ticker information: {e}")

    def get_ohlc_data(
            self,
            pair: str,
            interval: int = 1,
            since: int = 0
            ) -> OHLCData:
        allowed = [1, 5, 15, 30, 60, 240, 1440, 10080, 21600]

        if interval not in allowed:
            raise ValueError(
                f"Invalid interval: {interval}. Allowed values are {allowed}"
            )

        endpoint = 'OHLC'
        post_data = {
            'nonce': self._nonce(),
            'pair': pair,
            'interval': interval,
            'since': since
        }

        self._logger.info("Fetching OHLC data from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            ticks = [
                OHLCTickData(
                    time=int(tick[0]),
                    open=Decimal(tick[1]),
                    high=Decimal(tick[2]),
                    low=Decimal(tick[3]),
                    close=Decimal(tick[4]),
                    vwap=Decimal(tick[5]),
                    volume=Decimal(tick[6]),
                    count=int(tick[7])
                )
                for tick in response['result'][pair]]

            return OHLCData(
                name=pair,
                ticks=ticks,
                last=int(response['result']['last']),
            )

        except Exception as e:
            self._logger.exception(f"Error fetching OHLC data: {e}")

    def get_order_book(self, pair: str, count: int = 100) -> OrderBook:
        if 1 >= count <= 500:
            raise ValueError(
                f"Invalid count: {count}. Must be >= 1 and <= 500."
            )

        endpoint = 'Depth'
        post_data = {
            'nonce': self._nonce(),
            'pair': pair,
            'count': count
        }

        self._logger.info("Fetching order book from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            asks = [OrderBookAsk(price=ask[0], volume=ask[1], timestamp=ask[2])
                    for ask in response['result'][pair]['asks']]
            bids = [OrderBookBid(price=bid[0], volume=bid[1], timestamp=bid[2])
                    for bid in response['result'][pair]['bids']]

            return OrderBook(name=pair, asks=asks, bids=bids)

        except Exception as e:
            self._logger.exception(f"Error fetching orderbook: {e}")

    def get_recent_trades(
            self,
            pair: str,
            since: int = 0,
            count: int = 50) -> RecentTrades:
        if 1 >= count <= 1000:
            raise ValueError(
                f"Invalid count: {count}. Must be >= 1 and <= 500."
            )

        endpoint = 'Depth'
        post_data = {
            'nonce': self._nonce(),
            'pair': pair,
            'since': since,
            'count': count
        }

        self._logger.info("Fetching recent trades from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            ticks = [
                RecentTradeTickData(
                    price=tick[0],
                    volume=tick[1],
                    time=tick[2],
                    order_side=tick[3],
                    order_type=tick[4],
                    miscellaneous=tick[5],
                    trade_id=tick[6]
                )
                for tick in response['result'][pair]]

            return RecentTrades(
                name=pair, tick_data=ticks, last=response['result']['last']
            )

        except Exception as e:
            self._logger.exception(f"Error fetching recent trades: {e}")

    def get_recent_spreads(self, pair: str, since: int = 0) -> RecentSpreads:
        endpoint = 'Spread'
        post_data = {
            'nonce': self._nonce(),
            'pair': pair,
            'since': since
        }

        self._logger.info("Fetching recent spreads from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            spread_data = [SpreadData(time=val[0], bid=val[1], ask=val[2])
                           for val in response['result'][pair]]

            return RecentSpreads(
                pair=pair,
                spread_data=spread_data,
                last=response['result']['last']
            )

        except Exception as e:
            self._logger.exception(f"Error fetching recent spreads: {e}")


class AccountData(BaseAPI):
    _URI_path: str = '/0/private/'
    _URL_path: str = 'https://api.kraken.com' + _URI_path

    def get_account_balance(self) -> List[AssetBalance]:
        endpoint = 'Balance'
        post_data = {
            'nonce': self._nonce()
        }

        self._logger.info("Fetching account balance from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            assets = []
            self._logger.debug("Retrieved asset balances:")
            for name, amount in response['result'].items():
                if Decimal(amount) > Decimal("0"):
                    self._logger.debug(f"{name}: {amount}")
                    assets.append(
                        AssetBalance(name=name, amount=Decimal(amount))
                    )

            return assets

        except Exception as e:
            self._logger.exception(f"Error fetching account balance: {e}")

    def get_extended_account_balance(self) -> List[ExtendedAssetBalance]:
        endpoint = 'BalanceEx'
        post_data = {
            'nonce': self._nonce()
        }

        self._logger.info(
            "Fetching extended account balance from Kraken API..."
        )

        try:
            response = self._get_response(endpoint, post_data)

            balances = []
            self._logger.debug("Retrieved extended asset balances:")
            for name, data in response['result'].items():
                self._logger.debug(f"{name}: {data}")
                balances.append(ExtendedAssetBalance(**data, name=name))

            return balances

        except Exception as e:
            self._logger.exception(
                f"Error fetching extended account balance: {e}"
            )

    def get_trade_balance(self, asset: Optional[str] = None) -> TradeBalance:
        endpoint = 'TradeBalance'
        post_data = {
            'nonce': self._nonce(),
            'asset': asset
        }

        self._logger.info("Fetching trade balance from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            return TradeBalance(**response['result'])

        except Exception as e:
            self._logger.exception(f"Error fetching trade balance: {e}")

    def get_open_orders(
            self,
            trades: Optional[bool] = None,
            userref: Optional[int] = None,
            cl_ord_id: Optional[str] = None
            ) -> List[Order]:
        endpoint = 'OpenOrders'
        post_data = {
            k: v for k, v in {
                'nonce': self._nonce(),
                'trades': trades,
                'userref': userref,
                'cl_ord_id': cl_ord_id
            }.items() if v is not None
        }

        self._logger.info("Fetching open orders from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            orders = []
            for order in response['result'].get('open'):
                order_data = response['result']['open'][order]
                orders.append(Order(
                    **{k: v for k, v in order_data.items() if k != 'descr'},
                    txid=order,
                    descr=order_data['descr']
                ))

            return orders

        except Exception as e:
            self._logger.exception(f"Error fetching open orders: {e}")

    def get_closed_orders(
            self,
            trades: Optional[bool] = None,
            userref: Optional[int] = None,
            cl_ord_id: Optional[str] = None,
            start: Optional[int] = None,
            end: Optional[int] = None,
            ofs: Optional[int] = None,
            closetime: Optional[str] = None,
            consolidate_taker: Optional[bool] = None
            ) -> Optional[Order]:
        endpoint = 'ClosedOrders'
        post_data = {
            k: v for k, v in {
                'nonce': self._nonce(),
                'trades': trades,
                'userref': userref,
                'cl_ord_id': cl_ord_id,
                'start': start,
                'end': end,
                'ofs': ofs,
                'closetime': closetime,
                'consolidate_taker': consolidate_taker
            }.items() if v is not None
        }

        self._logger.info("Fetching closed orders from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            orders = []
            for order in response['result'].get('closed'):
                order_data = response['result']['closed'][order]
                orders.append(Order(
                    **{k: v for k, v in order_data.items() if k != 'descr'},
                    txid=order,
                    descr=order_data['descr']
                ))

            return orders

        except Exception as e:
            self._logger.exception(f"Error fetching closed orders: {e}")

    def query_orders_info(
            self,
            txid: str,
            trades: Optional[bool] = None,
            userref: Optional[int] = None,
            consolidate_taker: Optional[bool] = None
            ) -> List[Order]:
        endpoint = 'QueryOrders'
        post_data = {
            k: v for k, v in {
                'nonce': self._nonce(),
                'txid': txid,
                'trades': trades,
                'userref': userref,
                'consolidate_taker': consolidate_taker
            }.items() if v is not None
        }

        self._logger.info("Fetching order info from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)
            return [
                Order(
                    **{k: v for k, v in order_data.items() if k != 'descr'},
                    txid=order,
                    descr=order_data['descr']
                )
                for order, order_data in response['result'].items()
            ]
        except Exception as e:
            self._logger.exception(f"Error fetching closed orders: {e}")

    def get_trades_history(
            self,
            type: Optional[TradeType] = None,
            trades: Optional[bool] = None,
            start: Optional[int] = None,
            end: Optional[int] = None,
            ofs: Optional[int] = None,
            consolidate_taker: Optional[bool] = None,
            ledgers: Optional[bool] = None
            ) -> Optional[List[Trade]]:
        endpoint = 'TradesHistory'
        post_data = {
            k: v for k, v in {
                'nonce': self._nonce(),
                'type': type,
                'trades': trades,
                'start': start,
                'end': end,
                'ofs': ofs,
                'consolidate_taker': consolidate_taker,
                'ledgers': ledgers
            }.items() if v is not None
        }

        self._logger.info("Fetching trade history from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)
            return [
                Trade(**trade_data, txid=trade)
                for trade, trade_data in response['result']['trades'].items()
            ]
        except Exception as e:
            self._logger.exception(f"Error fetching trade history: {e}")

    def querey_trades_info(
            self,
            txid: str,
            trades: Optional[bool] = None
            ) -> List[Trade]:
        endpoint = 'QueryTrades'
        post_data = {
            k: v for k, v in {
                'nonce': self._nonce(),
                'txid': txid,
                'trades': trades
            }.items() if v is not None
        }

        self._logger.info("Fetching trade info from Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            trade_list = []
            for trade in response['result']:
                order_data = response['result'][trade]
                trade_list.append(Trade(**order_data, txid=trade))

            return trade_list

        except Exception as e:
            self._logger.exception(f"Error fetching trade info: {e}")

    # def get_open_positions(
    #         self,
    #         txid: Optional[str],
    #         docalcs: Optional[bool],
    #         consolidation: Optional[str]
    #     ) -> OpenMarginPosition:
    #     pass

    # def get_ledgers_info(
    #         self,
    #         asset: Optional[str] = None,
    #         aclass: Optional[str] = None,
    #         type: Optional[OrderType] = None,
    #         start: Optional[int] = None,
    #         end: Optional[int] = None,
    #         ofs: Optional[int] = None,
    #         without_content: Optional[bool] = None
    #     ) -> Optional[Dict]:
    #     endpoint = 'Ledgers'
    #     post_data = {
    #         'nonce': self._nonce()
    #     }
    #     if asset is not None:
    #         post_data.update(({'asset': asset}))
    #     if aclass is not None:
    #         post_data.update(({'aclass': aclass}))
    #     if type is not None:
    #         post_data.update(({'type': type}))
    #     if start is not None:
    #         post_data.update(({'start': start}))
    #     if end is not None:
    #         post_data.update(({'end': end}))
    #     if ofs is not None:
    #         post_data.update(({'ofs': ofs}))
    #     if without_content is not None:
    #         post_data.update(({'without_content': without_content}))
    #     self._logger.info("Fetching ledger info from Kraken API...")
    #     response = self._get_response(endpoint, post_data)
    #     return response

    # def querey_ledgers(
    #         self,
    #         id: str,
    #         trades: Optional[bool] = None
    #     ) -> Optional[Dict]:
    #     endpoint = 'QueryLedgers'
    #     post_data = {
    #         'nonce': self._nonce(),
    #         'id': id
    #     }
    #     if trades is not None:
    #         post_data.update(({'trades': trades}))
    #     self._logger.info("Fetching ledger from Kraken API...")
    #     response = self._get_response(endpoint, post_data)
    #     return response

    # def get_trade_volume(
    #         self,
    #         pair: Optional[str] = None
    #     ) -> List[TradeVolume]:
    #     endpoint = 'TradeVolume'
    #     post_data = {
    #         'nonce': self._nonce()
    #     }
    #     if pair is not None:
    #         post_data.update(({'pair': pair}))

    #     self._logger.info("Fetching trade volume from Kraken API...")

    #     try:
    #         response = self._get_response(endpoint, post_data)

    #         volume_list = []
    #         pair = "" if pair is None else pair
    #         for p in pair.split(","):

    #         tv_data = response['result']
    #         fees = tv_data.get("fees")
    #         tv_data.pop("fees")
    #         fees_maker = tv_data.get("fees_maker")
    #         tv_data.pop("fees_maker")

    #         return TradeVolume(**tv_data, fees=fees, fees_maker=fees_maker)

    #     except Exception as e:
    #         self._logger.exception(f"Error fetching trade volume: {e}")


class Trading(BaseAPI):
    _URI_path: str = '/0/private/'
    _URL_path: str = 'https://api.kraken.com' + _URI_path

    def add_order(
            self,
            ordertype: OrderType,
            type: OrderSide,
            volume: Decimal,
            pair: str,
            userref: Optional[int] = None,
            cl_ord_id: Optional[str] = None,
            displayvol: Optional[Decimal] = None,
            price: Optional[Decimal] = None,
            price2: Optional[Decimal] = None,
            trigger: Optional[OrderTrigger] = None,
            leverage: Optional[Decimal] = None,
            reduce_only: Optional[bool] = None,
            stptype: Optional[STPType] = None,
            oflags: Optional[str] = None,
            timeinforce: Optional[TimeInForce] = None,
            starttm: Optional[str] = None,
            expiretm: Optional[str] = None,
            close_ordertype: Optional[OrderType] = None,
            close_price: Optional[Decimal] = None,
            close_price2: Optional[Decimal] = None,
            deadline: Optional[str] = None,
            validate: Optional[bool] = None
            ) -> Order:
        endpoint = 'AddOrder'

        if userref is not None and cl_ord_id is not None:
            raise ValueError(
                "userref and cl_ord_id are mutually exclusive. "
                "Provide only one."
            )

        if volume <= 0:
            raise ValueError("Volume must be a positive decimal.")

        if ordertype == OrderType.ICEBERG and displayvol is not None:
            if displayvol < (volume / Decimal(15)):
                raise ValueError(
                    "For iceberg orders. Minimum value is 1 / 15 of volume."
                )

        if ordertype == OrderType.LIMIT and price is None:
            raise ValueError("Limit orders require a price.")

        if ordertype == OrderType.MARKET and price is not None:
            raise ValueError("Market orders should not be provided a price.")

        post_data = {
            'nonce': self._nonce(),
            'ordertype': ordertype,
            'type': type,
            'volume': str(volume),
            'pair': pair,
            'userref': userref,
            'cl_ord_id': cl_ord_id,
            'displayvol': displayvol,
            'price': self._enforce_precision(price) if price else None,
            'price2': price2,
            'trigger': trigger if trigger else None,
            'leverage': leverage,
            'reduce_only': reduce_only,
            'stptype': stptype,
            'oflags': oflags,
            'timeinforce': timeinforce,
            'starttm': starttm,
            'expiretm': expiretm,
            'close[ordertype]': close_ordertype,
            'close[price]': close_price,
            'close[price2]': close_price2,
            'deadline': deadline,
            'validate': validate
        }

        post_data = {k: v for k, v in post_data.items() if v is not None}

        self._logger.info("Adding order with Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)

            self._logger.info(
                f"Placed order: {response['result'].get('descr').get('order')}"
            )

            return Order(
                txid=response['result']['txid'][0],
                userref=userref,
                cl_ord_id=cl_ord_id,
                type=type,
                vol=volume,
                status=OrderStatusType.OPEN,
                descr=OrderDescription(
                    pair=pair,
                    type=type,
                    ordertype=ordertype,
                    price=price,
                    price2=price2,
                    leverage=leverage
                ),
                vol_exec=Decimal("0"),
                cost=Decimal("0"),
                fee=Decimal("0"),
                displayvol=displayvol,
                price=price,
                trigger=trigger,
                leverage=leverage,
                reduce_only=reduce_only,
                stptype=stptype,
                oflags=oflags,
                timeinforce=timeinforce,
                starttm=starttm,
                expiretm=expiretm,
                close_ordertype=close_ordertype,
                close_price=close_price,
                close_price2=close_price2,
                deadline=deadline
            )

        except Exception as e:
            self._logger.exception(f"Error adding order: {e}")

    def cancel_order(
            self,
            txid: Optional[str | int] = None,
            cl_ord_id: Optional[str] = None
            ) -> int:
        endpoint = 'CancelOrder'

        if txid is None and cl_ord_id is None:
            raise ValueError("Either txid, userref or cl_ord_id is required.")

        post_data = {
            'nonce': self._nonce(),
            'txid': txid,
            'cl_ord_id': cl_ord_id
        }

        self._logger.info("Cancelling order with Kraken API...")

        try:
            response = self._get_response(endpoint, post_data)
            return response['result']['count']

        except Exception as e:
            self._logger.exception(f"Error cancelling order(s): {e}")

#     def cancel_all(self):
#         endpoint = 'CancelAll'
#         post_data = {
#             'nonce': self._nonce()
#         }
#         self._logger.info("Cancelling all orders with Kraken API...")
#         response = self._get_response(endpoint, post_data)
#         return response
