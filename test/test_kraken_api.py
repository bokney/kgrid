
import os
import pytest
import requests
from decimal import Decimal
from unittest.mock import patch, MagicMock
from requests.exceptions import RequestException
from time import sleep
from src.kraken_api import (
    BaseAPI,
    MarketData,
    AccountData,
    Trading,
    TimeData,
    SystemStatus,
    AssetInfo,
    TradableAssetPair,
    TickerInfo,
    OHLCData,
    OrderBook,
    RecentTrades,
    RecentSpreads,
    AssetBalance,
    ExtendedAssetBalance,
    TradeBalance,
    Order,
    OrderType,
    OrderSide,
    OrderStatusType,
    Trade,
)


class TestBaseAPI:
    @pytest.fixture
    def base_api(self):
        return BaseAPI()

    @patch("src.kraken_api.load_dotenv", lambda *args, **kwargs: None)
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_vars(self):
        os.environ.clear()
        with pytest.raises(ValueError, match="Error! API_SECRET is missing!"):
            BaseAPI()

        with patch.dict(os.environ, {"API_SECRET": "test_secret"}):
            with pytest.raises(ValueError, match="Error! API_KEY is missing!"):
                BaseAPI()

    @patch.dict(
        os.environ,
        {"API_SECRET": "dGVzdF9zZWNyZXQ=", "API_KEY": "test_key"}
    )
    def test_generate_headers(self, base_api: BaseAPI):
        URI = "/test/endpoint"
        post_data = {"nonce": 123456789, "param1": "value1"}
        headers = base_api._generate_headers(URI, post_data)
        assert "API-Key" in headers
        assert "API-Sign" in headers
        assert headers["API-Key"] == "test_key"
        assert isinstance(headers["API-Sign"], str)

    @patch.object(requests.Session, 'post')
    @patch.dict(
        os.environ,
        {"API_SECRET": "dGVzdF9zZWNyZXQ=", "API_KEY": "test_key"}
    )
    def test_create_signed_request(self, mock_post, base_api: BaseAPI):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        post_data = {"nonce": 123456789, "param1": "value1"}

        response = base_api._create_signed_request(
            "/test/uri", "https://api.example.com/test",
            post_data
        )

        assert response == {"result": "success"}

        mock_post.assert_called_once_with(
            "https://api.example.com/test",
            data=post_data,
            headers=mock_post.call_args[1]["headers"]
        )

        headers = mock_post.call_args[1]["headers"]
        assert "API-Key" in headers
        assert "API-Sign" in headers
        assert headers["API-Key"] == "test_key"

    @patch.object(requests.Session, 'post')
    @patch.dict(
        os.environ,
        {"API_SECRET": "dGVzdF9zZWNyZXQ=", "API_KEY": "test_key"}
    )
    def test_create_signed_request_error(self, mock_post, base_api: BaseAPI):
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Non-JSON response")
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        post_data = {"nonce": 123456789, "param1": "value1"}

        with pytest.raises(ValueError):
            base_api._create_signed_request(
                "/test/uri", "https://api.example.com/test",
                post_data
            )

        mock_post.assert_called_once_with(
            "https://api.example.com/test",
            data=post_data,
            headers=mock_post.call_args[1]["headers"]
        )

    def test_process_response(self, base_api: BaseAPI):
        response = {"result": {"data": "value"}, "error": []}
        result = base_api._process_response(response)
        assert result == {"data": "value"}

    def test_process_response_error(self, base_api: BaseAPI):
        response = {"error": ["Some error"]}
        with pytest.raises(RequestException, match="API error: Some error"):
            base_api._process_response(response)

        with pytest.raises(ValueError, match="No response received from API"):
            base_api._process_response(None)  # type: ignore

    def test_nonce_unique(self, base_api: BaseAPI):
        nonce1 = base_api._nonce()
        sleep(0.001)
        nonce2 = base_api._nonce()
        assert nonce1 != nonce2
        assert nonce1 < nonce2


class TestMarketData:
    @pytest.fixture
    def market_data(self):
        with patch(
            "src.kraken_api.load_dotenv",
            lambda *args, **kwargs: None
        ):
            with patch.dict(
                os.environ,
                {"API_KEY": "test_key", "API_SECRET": "test_secret"},
                clear=True
            ):
                yield MarketData()

    @patch.object(MarketData, '_get_response')
    def test_get_server_time(self, mock_get_response, market_data: MarketData):
        mock_get_response.return_value = {
            "unixtime": 1688669448,
            "rfc1123": "Thu, 06 Jul 23 18:50:48 +0000"
        }

        result = market_data.get_server_time()

        assert isinstance(result, TimeData)
        assert result.unixtime == 1688669448
        assert result.rfc1123 == "Thu, 06 Jul 23 18:50:48 +0000"

    @patch.object(MarketData, '_get_response')
    def test_get_system_status(
        self,
        mock_get_response,
        market_data: MarketData
    ):
        mock_get_response.return_value = {
            "status": "online",
            "timestamp": "2023-07-06T18:52:00Z"
        }

        result = market_data.get_system_status()

        assert isinstance(result, SystemStatus)
        assert result.status == "online"
        assert result.timestamp == "2023-07-06T18:52:00Z"

    @patch.object(MarketData, '_get_response')
    def test_get_asset_info(self, mock_get_response, market_data: MarketData):
        mock_get_response.return_value = {
            "XXBT": {
                "aclass": "currency",
                "altname": "XBT",
                "decimals": 10,
                "display_decimals": 5,
                "collateral_value": 1,
                "status": "enabled"
            },
            "ZEUR": {
                "aclass": "currency",
                "altname": "EUR",
                "decimals": 4,
                "display_decimals": 2,
                "collateral_value": 1,
                "status": "enabled"
            },
            "ZUSD": {
                "aclass": "currency",
                "altname": "USD",
                "decimals": 4,
                "display_decimals": 2,
                "collateral_value": 1,
                "status": "enabled"
            }
        }

        result = market_data.get_asset_info("XXBT")
        assert isinstance(result, list)
        assert all(isinstance(item, AssetInfo) for item in result)
        assert len(result) == 1
        assert result[0].name == "XXBT"
        assert result[0].altname == "XBT"
        assert result[0].decimals == 10

        result = market_data.get_asset_info(["XXBT", "ZEUR"])
        assert len(result) == 2
        assert result[0].name == "XXBT"
        assert result[0].altname == "XBT"
        assert result[1].name == "ZEUR"
        assert result[1].altname == "EUR"

        result = market_data.get_asset_info("INVALID")
        assert len(result) == 0

    @patch.object(MarketData, '_get_response')
    def test_get_tradable_asset_pairs(
        self,
        mock_get_response,
        market_data: MarketData
    ):
        mock_get_response.return_value = {
            "XETHXXBT": {
                "altname": "ETHXBT",
                "wsname": "ETH/XBT",
                "aclass_base": "currency",
                "base": "XETH",
                "aclass_quote": "currency",
                "quote": "XXBT",
                "lot": "unit",
                "cost_decimals": 6,
                "pair_decimals": 5,
                "lot_decimals": 8,
                "lot_multiplier": 1,
                "leverage_buy": [2, 3, 4, 5],
                "leverage_sell": [2, 3, 4, 5],
                "fees": [
                    [0, 0.26],
                    [50000, 0.24],
                    [100000, 0.22],
                    [250000, 0.2],
                    [500000, 0.18],
                    [1000000, 0.16],
                    [2500000, 0.14],
                    [5000000, 0.12],
                    [10000000, 0.1],
                ],
                "fees_maker": [
                    [0, 0.16],
                    [50000, 0.14],
                    [100000, 0.12],
                    [250000, 0.1],
                    [500000, 0.08],
                    [1000000, 0.06],
                    [2500000, 0.04],
                    [5000000, 0.02],
                    [10000000, 0],
                ],
                "fee_volume_currency": "ZUSD",
                "margin_call": 80,
                "margin_stop": 40,
                "ordermin": "0.01",
                "costmin": "0.00002",
                "tick_size": "0.00001",
                "status": "online",
                "long_position_limit": 1100,
                "short_position_limit": 400,
            },
            "XXBTZUSD": {
                "altname": "XBTUSD",
                "wsname": "XBT/USD",
                "aclass_base": "currency",
                "base": "XXBT",
                "aclass_quote": "currency",
                "quote": "ZUSD",
                "lot": "unit",
                "cost_decimals": 5,
                "pair_decimals": 1,
                "lot_decimals": 8,
                "lot_multiplier": 1,
                "leverage_buy": [2, 3, 4, 5],
                "leverage_sell": [2, 3, 4, 5],
                "fees": [
                    [0, 0.26],
                    [50000, 0.24],
                    [100000, 0.22],
                    [250000, 0.2],
                    [500000, 0.18],
                    [1000000, 0.16],
                    [2500000, 0.14],
                    [5000000, 0.12],
                    [10000000, 0.1],
                ],
                "fees_maker": [
                    [0, 0.16],
                    [50000, 0.14],
                    [100000, 0.12],
                    [250000, 0.1],
                    [500000, 0.08],
                    [1000000, 0.06],
                    [2500000, 0.04],
                    [5000000, 0.02],
                    [10000000, 0],
                ],
                "fee_volume_currency": "ZUSD",
                "margin_call": 80,
                "margin_stop": 40,
                "ordermin": "0.0001",
                "costmin": "0.5",
                "tick_size": "0.1",
                "status": "online",
                "long_position_limit": 250,
                "short_position_limit": 200,
            }
        }

        result = market_data.get_tradable_asset_pairs("XETHXXBT")

        assert isinstance(result, list)
        assert all(isinstance(item, TradableAssetPair) for item in result)
        assert len(result) == 2

        assert result[0].name == "XETHXXBT"
        assert result[0].altname == "ETHXBT"
        assert result[0].base == "XETH"
        assert result[0].quote == "XXBT"
        assert result[0].status == "online"

        assert result[1].name == "XXBTZUSD"
        assert result[1].altname == "XBTUSD"
        assert result[1].base == "XXBT"
        assert result[1].quote == "ZUSD"
        assert result[1].status == "online"

    @patch.object(MarketData, '_get_response')
    def test_get_ticker_information(
        self,
        mock_get_response,
        market_data: MarketData
    ):
        mock_get_response.return_value = {
            "XXBTZUSD": {
                "a": ["30300.10000", "1", "1.000"],
                "b": ["30300.00000", "1", "1.000"],
                "c": ["30303.20000", "0.00067643"],
                "v": ["4083.67001100", "4412.73601799"],
                "p": ["30706.77771", "30689.13205"],
                "t": [34619, 38907],
                "l": ["29868.30000", "29868.30000"],
                "h": ["31631.00000", "31631.00000"],
                "o": "30502.80000",
            }
        }

        result = market_data.get_ticker_information("XXBTZUSD")

        assert isinstance(result, TickerInfo)

        assert result.name == "XXBTZUSD"
        assert result.a == [
            Decimal("30300.10000"),
            Decimal("1"),
            Decimal("1.000")
        ]
        assert result.b == [
            Decimal("30300.00000"),
            Decimal("1"),
            Decimal("1.000")
        ]
        assert result.c == [
            Decimal("30303.20000"),
            Decimal("0.00067643")
        ]
        assert result.v == [
            Decimal("4083.67001100"),
            Decimal("4412.73601799")
        ]
        assert result.p == [
            Decimal("30706.77771"),
            Decimal("30689.13205")
        ]
        assert result.t == [34619, 38907]
        assert result.l == [
            Decimal("29868.30000"),
            Decimal("29868.30000")
        ]
        assert result.h == [
            Decimal("31631.00000"),
            Decimal("31631.00000")
        ]
        assert result.o == Decimal("30502.80000")

    @patch.object(MarketData, '_get_response')
    def test_get_ohlc_data(self, mock_get_response, market_data: MarketData):
        mock_get_response.return_value = {
            "XXBTZUSD": [
                [
                    1688671200,
                    "30306.1",
                    "30306.2",
                    "30305.7",
                    "30305.7",
                    "30306.1",
                    "3.39243896",
                    23,
                ],
                [
                    1688671260,
                    "30304.5",
                    "30304.5",
                    "30300.0",
                    "30300.0",
                    "30300.0",
                    "4.42996871",
                    18,
                ],
                [
                    1688671320,
                    "30300.3",
                    "30300.4",
                    "30291.4",
                    "30291.4",
                    "30294.7",
                    "2.13024789",
                    25,
                ],
                [
                    1688671380,
                    "30291.8",
                    "30295.1",
                    "30291.8",
                    "30295.0",
                    "30293.8",
                    "1.01836275",
                    9,
                ],
            ],
            "last": 1688672160
        }

        result = market_data.get_ohlc_data("XXBTZUSD")

        assert isinstance(result, OHLCData)
        assert result.name == "XXBTZUSD"
        assert len(result.ticks) == 4

        assert result.ticks[0].time == 1688671200
        assert result.ticks[0].open == Decimal("30306.1")
        assert result.ticks[0].high == Decimal("30306.2")
        assert result.ticks[0].low == Decimal("30305.7")
        assert result.ticks[0].close == Decimal("30305.7")
        assert result.ticks[0].vwap == Decimal("30306.1")
        assert result.ticks[0].volume == Decimal("3.39243896")
        assert result.ticks[0].count == 23

        assert result.ticks[1].time == 1688671260
        assert result.ticks[1].open == Decimal("30304.5")
        assert result.ticks[1].high == Decimal("30304.5")
        assert result.ticks[1].low == Decimal("30300.0")
        assert result.ticks[1].close == Decimal("30300.0")
        assert result.ticks[1].vwap == Decimal("30300.0")
        assert result.ticks[1].volume == Decimal("4.42996871")
        assert result.ticks[1].count == 18

        assert result.last == 1688672160

    @patch.object(MarketData, '_get_response')
    def test_get_order_book(self, mock_get_response, market_data: MarketData):
        mock_get_response.return_value = {
            "XXBTZUSD": {
                "asks": [
                    ["30384.10000", "2.059", 1688671659],
                    ["30387.90000", "1.500", 1688671380],
                    ["30393.70000", "9.871", 1688671261],
                ],
                "bids": [
                    ["30297.00000", "1.115", 1688671636],
                    ["30296.70000", "2.002", 1688671674],
                    ["30289.80000", "5.001", 1688671673],
                ],
            }
        }

        result = market_data.get_order_book("XXBTZUSD")

        assert result.name == "XXBTZUSD"
        assert isinstance(result, OrderBook)
        assert len(result.asks) == 3
        assert result.asks[0].price == Decimal("30384.10000")
        assert result.asks[0].volume == Decimal("2.059")
        assert result.asks[0].timestamp == 1688671659
        assert result.asks[1].price == Decimal("30387.90000")
        assert result.asks[1].volume == Decimal("1.500")
        assert result.asks[1].timestamp == 1688671380
        assert len(result.bids) == 3
        assert result.bids[0].price == Decimal("30297.00000")
        assert result.bids[0].volume == Decimal("1.115")
        assert result.bids[0].timestamp == 1688671636
        assert result.bids[1].price == Decimal("30296.70000")
        assert result.bids[1].volume == Decimal("2.002")
        assert result.bids[1].timestamp == 1688671674

    @patch.object(MarketData, '_get_response')
    def test_get_recent_trades(
        self,
        mock_get_response,
        market_data: MarketData
    ):
        mock_get_response.return_value = {
            "XXBTZUSD": [
                [
                    "30243.40000",
                    "0.34507674",
                    1688669597.8277369,
                    "b",
                    "m",
                    "",
                    61044952
                ],
                [
                    "30243.30000",
                    "0.00376960",
                    1688669598.2804112,
                    "s",
                    "l",
                    "",
                    61044953
                ],
                [
                    "30243.30000",
                    "0.01235716",
                    1688669602.698379,
                    "s",
                    "m",
                    "",
                    61044956
                ]
            ],
            "last": "1688671969993150842"
        }

        result = market_data.get_recent_trades("XXBTZUSD")

        assert isinstance(result, RecentTrades)
        assert result.name == "XXBTZUSD"
        assert result.tick_data[0].price == Decimal("30243.40000")
        assert result.tick_data[0].volume == Decimal("0.34507674")
        assert result.tick_data[0].time == 1688669597.8277369
        assert result.tick_data[0].order_side == "b"
        assert result.tick_data[0].order_type == "m"
        assert result.tick_data[0].miscellaneous == ""
        assert result.tick_data[0].trade_id == 61044952
        assert result.tick_data[1].price == Decimal("30243.30000")
        assert result.tick_data[1].volume == Decimal("0.00376960")
        assert result.tick_data[1].time == 1688669598.2804112
        assert result.tick_data[1].order_side == "s"
        assert result.tick_data[1].order_type == "l"
        assert result.tick_data[1].miscellaneous == ""
        assert result.tick_data[1].trade_id == 61044953
        assert result.last == "1688671969993150842"

    @patch.object(MarketData, '_get_response')
    def test_get_recent_spreads(
        self,
        mock_get_response,
        market_data: MarketData
    ):
        mock_get_response.return_value = {
            "XXBTZUSD": [
                [
                    1688671834,
                    "30292.10000",
                    "30297.50000"
                ],
                [
                    1688671834,
                    "30292.10000",
                    "30296.70000"
                ],
                [
                    1688671834,
                    "30292.70000",
                    "30296.70000"
                ]
            ],
            "last": 1688672106
        }

        result = market_data.get_recent_spreads("XXBTZUSD")

        assert isinstance(result, RecentSpreads)
        assert result.pair == "XXBTZUSD"
        assert result.spread_data[0].time == 1688671834
        assert result.spread_data[0].bid == "30292.10000"
        assert result.spread_data[0].ask == "30297.50000"
        assert result.spread_data[1].time == 1688671834
        assert result.spread_data[1].bid == "30292.10000"
        assert result.spread_data[1].ask == "30296.70000"


class TestAccountData:
    @pytest.fixture
    def account_data(self):
        with patch(
            "src.kraken_api.load_dotenv",
            lambda *args, **kwargs: None
        ):
            with patch.dict(
                os.environ,
                {"API_KEY": "test_key", "API_SECRET": "test_secret"},
                clear=True
            ):
                yield AccountData()

    @patch.object(AccountData, '_get_response')
    def test_get_account_balance(
        self,
        mock_get_response,
        account_data: AccountData
    ):
        mock_get_response.return_value = {
            "ZUSD": "171288.6158",
            "ZEUR": "504861.8946",
            "XXBT": "1011.1908877900",
            "XETH": "818.5500000000",
            "USDT": "500000.00000000",
            "DAI": "9999.9999999999",
            "DOT": "2.5000000000",
            "ETH2.S": "198.3970800000",
            "ETH2": "2.5885574330",
            "USD.M": "1213029.2780"
        }

        result = account_data.get_account_balance()

        assert isinstance(result, list)
        assert all(isinstance(item, AssetBalance) for item in result)
        assert len(result) == 10
        assert result[0].name == "ZUSD"
        assert result[0].amount == Decimal("171288.6158")
        assert result[1].name == "ZEUR"
        assert result[1].amount == Decimal("504861.8946")
        assert result[2].name == "XXBT"
        assert result[2].amount == Decimal("1011.1908877900")

    @patch.object(AccountData, '_get_response')
    def test_get_extended_account_balance(
        self,
        mock_get_response,
        account_data: AccountData
    ):
        mock_get_response.return_value = {
            "ZUSD": {
                "balance": 25435.21,
                "hold_trade": 8249.76
            },
            "XXBT": {
                "balance": 1.2435,
                "hold_trade": 0.8423
            }
        }

        result = account_data.get_extended_account_balance()

        assert isinstance(result, list)
        assert all(isinstance(item, ExtendedAssetBalance) for item in result)

        assert result[0].name == "ZUSD"
        assert result[0].balance == Decimal("25435.21")
        assert result[0].hold_trade == Decimal("8249.76")
        assert result[1].name == "XXBT"
        assert result[1].balance == Decimal("1.2435")
        assert result[1].hold_trade == Decimal("0.8423")

    @patch.object(AccountData, '_get_response')
    def test_get_trade_balance(
        self,
        mock_get_response,
        account_data: AccountData
    ):
        mock_get_response.return_value = {
            "eb": "1101.3425",
            "tb": "392.2264",
            "m": "7.0354",
            "n": "-10.0232",
            "c": "21.1063",
            "v": "31.1297",
            "e": "382.2032",
            "mf": "375.1678",
            "ml": "5432.57"
        }

        result = account_data.get_trade_balance()

        assert isinstance(result, TradeBalance)

        assert result.eb == Decimal("1101.3425")
        assert result.tb == Decimal("392.2264")
        assert result.m == Decimal("7.0354")
        assert result.n == Decimal("-10.0232")
        assert result.c == Decimal("21.1063")
        assert result.v == Decimal("31.1297")
        assert result.e == Decimal("382.2032")
        assert result.mf == Decimal("375.1678")
        assert result.ml == Decimal("5432.57")

    @patch.object(AccountData, '_get_response')
    def test_get_open_orders(
        self,
        mock_get_response,
        account_data: AccountData
    ):
        mock_get_response.return_value = {
            "open": {
                "OQCLML-BW3P3-BUCMWZ": {
                    "refid": "None",
                    "userref": 0,
                    "status": "open",
                    "opentm": 1688666559.8974,
                    "starttm": 0,
                    "expiretm": 0,
                    "descr": {
                        "pair": "XBTUSD",
                        "type": "buy",
                        "ordertype": "limit",
                        "price": "30010.0",
                        "price2": "0",
                        "leverage": "none",
                        "order": "buy 1.25000000 XBTUSD @ limit 30010.0",
                        "close": ""
                    },
                    "vol": "1.25000000",
                    "vol_exec": "0.37500000",
                    "cost": "11253.7",
                    "fee": "0.00000",
                    "price": "30010.0",
                    "stopprice": "0.00000",
                    "limitprice": "0.00000",
                    "misc": "",
                    "oflags": "fciq",
                    "trades": [
                        "TCCCTY-WE2O6-P3NB37"
                    ]
                },
                "OB5VMB-B4U2U-DK2WRW": {
                    "refid": "None",
                    "userref": 45326,
                    "status": "open",
                    "opentm": 1688665899.5699,
                    "starttm": 0,
                    "expiretm": 0,
                    "descr": {
                        "pair": "XBTUSD",
                        "type": "buy",
                        "ordertype": "limit",
                        "price": "14500.0",
                        "price2": "0",
                        "leverage": "5:1",
                        "order":
                        "buy 0.27500000 XBTUSD "
                        "@ limit 14500.0 with 5:1 leverage",
                        "close": ""
                    },
                    "vol": "0.27500000",
                    "vol_exec": "0.00000000",
                    "cost": "0.00000",
                    "fee": "0.00000",
                    "price": "0.00000",
                    "stopprice": "0.00000",
                    "limitprice": "0.00000",
                    "misc": "",
                    "oflags": "fciq"
                }
            }
        }

        result = account_data.get_open_orders()

        assert isinstance(result, list)
        assert all(isinstance(item, Order) for item in result)
        assert len(result) == 2

        assert result[0].txid == "OQCLML-BW3P3-BUCMWZ"
        assert result[0].userref == 0
        assert result[0].status == "open"
        assert result[0].opentm == 1688666559.8974
        assert result[0].starttm == 0
        assert result[0].expiretm == 0
        assert result[0].descr.pair == "XBTUSD"
        assert result[0].descr.type == "buy"
        assert result[0].descr.ordertype == "limit"
        assert result[0].descr.price == Decimal("30010.0")
        assert result[0].descr.price2 == Decimal("0")
        assert result[0].descr.leverage is None
        assert result[0].descr.order == "buy 1.25000000 XBTUSD @ limit 30010.0"
        assert result[0].descr.close == ""
        assert result[0].vol == Decimal("1.25000000")
        assert result[0].vol_exec == Decimal("0.37500000")
        assert result[0].cost == Decimal("11253.7")
        assert result[0].fee == Decimal("0.00000")
        assert result[0].price == Decimal("30010.0")
        assert result[0].stopprice == Decimal("0.00000")
        assert result[0].limitprice == Decimal("0.00000")
        assert result[0].misc == ""
        assert result[0].oflags == "fciq"
        assert len(result[0].trades) == 1
        assert result[0].trades[0] == "TCCCTY-WE2O6-P3NB37"

        assert result[1].txid == "OB5VMB-B4U2U-DK2WRW"

    @patch.object(AccountData, '_get_response')
    def test_get_closed_orders(
        self,
        mock_get_response,
        account_data: AccountData
    ):
        mock_get_response.return_value = {
            "closed": {
                "O37652-RJWRT-IMO74O": {
                    "refid": "None",
                    "userref": 1,
                    "status": "canceled",
                    "reason": "User requested",
                    "opentm": 1688148493.7708,
                    "closetm": 1688148610.0482,
                    "starttm": 0,
                    "expiretm": 0,
                    "descr": {
                        "pair": "XBTGBP",
                        "type": "buy",
                        "ordertype": "stop-loss-limit",
                        "price": "23667.0",
                        "price2": "0",
                        "leverage": "none",
                        "order": "buy 0.00100000 XBTGBP @ limit 23667.0",
                        "close": ""
                    },
                    "vol": "0.00100000",
                    "vol_exec": "0.00000000",
                    "cost": "0.00000",
                    "fee": "0.00000",
                    "price": "0.00000",
                    "stopprice": "0.00000",
                    "limitprice": "0.00000",
                    "misc": "",
                    "oflags": "fciq",
                    "trigger": "index"
                },
                "O6YDQ5-LOMWU-37YKEE": {
                    "refid": "None",
                    "userref": 36493663,
                    "status": "canceled",
                    "reason": "User requested",
                    "opentm": 1688148493.7708,
                    "closetm": 1688148610.0477,
                    "starttm": 0,
                    "expiretm": 0,
                    "descr": {
                        "pair": "XBTEUR",
                        "type": "buy",
                        "ordertype": "take-profit-limit",
                        "price": "27743.0",
                        "price2": "0",
                        "leverage": "none",
                        "order": "buy 0.00100000 XBTEUR @ limit 27743.0",
                        "close": ""
                    },
                    "vol": "0.00100000",
                    "vol_exec": "0.00000000",
                    "cost": "0.00000",
                    "fee": "0.00000",
                    "price": "0.00000",
                    "stopprice": "0.00000",
                    "limitprice": "0.00000",
                    "misc": "",
                    "oflags": "fciq",
                    "trigger": "index"
                }
            },
            "count": 2
        }

        result = account_data.get_closed_orders()

        assert isinstance(result, list)
        assert all(isinstance(item, Order) for item in result)
        assert len(result) == 2

        assert result[0].txid == "O37652-RJWRT-IMO74O"
        assert result[0].refid is None
        assert result[0].userref == 1
        assert result[0].cl_ord_id is None
        assert result[0].status == OrderStatusType.CANCELLED
        assert result[0].opentm == 1688148493.7708
        assert result[0].starttm == 0
        assert result[0].expiretm == 0
        assert result[0].descr.pair == "XBTGBP"
        assert result[0].descr.type == "buy"
        assert result[0].descr.ordertype == "stop-loss-limit"
        assert result[0].descr.price == Decimal("23667.0")
        assert result[0].descr.price2 == Decimal("0")
        assert result[0].descr.leverage is None
        assert result[0].descr.order == "buy 0.00100000 XBTGBP @ limit 23667.0"
        assert result[0].descr.close == ""
        assert result[0].vol == Decimal("0.00100000")
        assert result[0].vol_exec == Decimal("0.00000000")
        assert result[0].cost == Decimal("0.00000")
        assert result[0].fee == Decimal("0.00000")
        assert result[0].price == Decimal("0.00000")
        assert result[0].stopprice == Decimal("0.00000")
        assert result[0].limitprice == Decimal("0.00000")
        assert result[0].margin is None
        assert result[0].misc == ""
        assert result[0].oflags == "fciq"
        assert len(result[0].trades) == 0
        assert result[0].sender_sub_id is None
        assert result[0].closetm == 1688148610.0482
        assert result[0].reason == "User requested"

        assert result[1].txid == "O6YDQ5-LOMWU-37YKEE"
        assert result[1].refid is None
        assert result[1].userref == 36493663

    @patch.object(AccountData, '_get_response')
    def test_query_orders_info(
        self,
        mock_get_response,
        account_data: AccountData
    ):
        mock_get_response.return_value = {
            "OBCMZD-JIEE7-77TH3F": {
                "refid": "None",
                "userref": 0,
                "status": "closed",
                "reason": None,
                "opentm": 1688665496.7808,
                "closetm": 1688665499.1922,
                "starttm": 0,
                "expiretm": 0,
                "descr": {
                    "pair": "XBTUSD",
                    "type": "buy",
                    "ordertype": "stop-loss-limit",
                    "price": "27500.0",
                    "price2": "0",
                    "leverage": "none",
                    "order": "buy 1.25000000 XBTUSD @ limit 27500.0",
                    "close": ""
                },
                "vol": "1.25000000",
                "vol_exec": "1.25000000",
                "cost": "27526.2",
                "fee": "26.2",
                "price": "27500.0",
                "stopprice": "0.00000",
                "limitprice": "0.00000",
                "misc": "",
                "oflags": "fciq",
                "trigger": "index",
                "trades": [
                    "TZX2WP-XSEOP-FP7WYR"
                ]
            },
            "OMMDB2-FSB6Z-7W3HPO": {
                "refid": "None",
                "userref": 0,
                "status": "closed",
                "reason": None,
                "opentm": 1688592012.2317,
                "closetm": 1688592012.2335,
                "starttm": 0,
                "expiretm": 0,
                "descr": {
                    "pair": "XBTUSD",
                    "type": "sell",
                    "ordertype": "market",
                    "price": "0",
                    "price2": "0",
                    "leverage": "none",
                    "order": "sell 0.25000000 XBTUSD @ market",
                    "close": ""
                },
                "vol": "0.25000000",
                "vol_exec": "0.25000000",
                "cost": "7500.0",
                "fee": "7.5",
                "price": "30000.0",
                "stopprice": "0.00000",
                "limitprice": "0.00000",
                "misc": "",
                "oflags": "fcib",
                "trades": [
                    "TJUW2K-FLX2N-AR2FLU"
                ]
            }
        }

        result = account_data.query_orders_info(
            "OBCMZD-JIEE7-77TH3F,OMMDB2-FSB6Z-7W3HPO"
        )

        assert isinstance(result, list)
        assert all(isinstance(item, Order) for item in result)
        assert len(result) == 2

        assert result[0].txid == "OBCMZD-JIEE7-77TH3F"
        assert result[0].refid is None
        assert result[0].userref == 0
        assert result[0].cl_ord_id is None
        assert result[0].status == OrderStatusType.CLOSED

        assert result[0].reason is None
        assert result[0].opentm == 1688665496.7808
        assert result[0].closetm == 1688665499.1922
        assert result[0].starttm == 0
        assert result[0].expiretm == 0
        assert result[0].descr.pair == "XBTUSD"
        assert result[0].descr.type == "buy"
        assert result[0].descr.ordertype == "stop-loss-limit"
        assert result[0].descr.price == Decimal("27500.0")
        assert result[0].descr.price2 == Decimal("0")
        assert result[0].descr.leverage is None
        assert result[0].descr.order == "buy 1.25000000 XBTUSD @ limit 27500.0"
        assert result[0].descr.close == ""
        assert result[0].vol == Decimal("1.25000000")
        assert result[0].vol_exec == Decimal("1.25000000")
        assert result[0].cost == Decimal("27526.2")
        assert result[0].fee == Decimal("26.2")
        assert result[0].price == Decimal("27500.0")
        assert result[0].stopprice == Decimal("0.00000")
        assert result[0].limitprice == Decimal("0.00000")
        assert result[0].misc == ""
        assert result[0].oflags == "fciq"
        assert result[0].trigger == "index"
        assert len(result[0].trades) == 1
        assert result[0].trades[0] == "TZX2WP-XSEOP-FP7WYR"

    @patch.object(AccountData, '_get_response')
    def test_get_trades_history(
        self,
        mock_get_response,
        account_data: AccountData
    ):
        mock_get_response.return_value = {
            "trades": {
                "THVRQM-33VKH-UCI7BS": {
                    "ordertxid": "OQCLML-BW3P3-BUCMWZ",
                    "postxid": "TKH2SE-M7IF5-CFI7LT",
                    "pair": "XXBTZUSD",
                    "time": 1688667796.8802,
                    "type": "buy",
                    "ordertype": "limit",
                    "price": "30010.00000",
                    "cost": "600.20000",
                    "fee": "0.00000",
                    "vol": "0.02000000",
                    "margin": "0.00000",
                    "misc": "",
                    "trade_id": 40274859,
                    "maker": True
                },
                "TCWJEG-FL4SZ-3FKGH6": {
                    "ordertxid": "OQCLML-BW3P3-BUCMWZ",
                    "postxid": "TKH2SE-M7IF5-CFI7LT",
                    "pair": "XXBTZUSD",
                    "time": 1688667769.6396,
                    "type": "buy",
                    "ordertype": "limit",
                    "price": "30010.00000",
                    "cost": "300.10000",
                    "fee": "0.00000",
                    "vol": "0.01000000",
                    "margin": "0.00000",
                    "misc": "",
                    "trade_id": 39482674,
                    "maker": True
                }
            }
        }

        result = account_data.get_trades_history()

        assert isinstance(result, list)
        assert all(isinstance(item, Trade) for item in result)
        assert len(result) == 2

        assert result[0].txid == "THVRQM-33VKH-UCI7BS"
        assert result[0].ordertxid == "OQCLML-BW3P3-BUCMWZ"
        assert result[0].postxid == "TKH2SE-M7IF5-CFI7LT"
        assert result[0].pair == "XXBTZUSD"
        assert result[0].time == 1688667796.8802
        assert result[0].ordertype == OrderType.LIMIT
        assert result[0].price == Decimal("30010.00000")
        assert result[0].cost == Decimal("600.20000")
        assert result[0].fee == Decimal("0.00000")
        assert result[0].vol == Decimal("0.02000000")
        assert result[0].margin == Decimal("0.00000")
        assert result[0].misc == ""
        assert result[0].trade_id == 40274859
        assert result[0].maker is True

        assert result[1].txid == "TCWJEG-FL4SZ-3FKGH6"
        assert result[1].ordertxid == "OQCLML-BW3P3-BUCMWZ"
        assert result[1].postxid == "TKH2SE-M7IF5-CFI7LT"
        assert result[1].pair == "XXBTZUSD"
        assert result[1].time == 1688667769.6396
        assert result[1].type == OrderSide.BUY
        assert result[1].ordertype == OrderType.LIMIT

    @patch.object(AccountData, '_get_response')
    def test_querey_trades_info(
        self,
        mock_get_response,
        account_data: AccountData
    ):
        mock_get_response.return_value = {
            "THVRQM-33VKH-UCI7BS": {
                "ordertxid": "OQCLML-BW3P3-BUCMWZ",
                "postxid": "TKH2SE-M7IF5-CFI7LT",
                "pair": "XXBTZUSD",
                "time": 1688667796.8802,
                "type": "buy",
                "ordertype": "limit",
                "price": "30010.00000",
                "cost": "600.20000",
                "fee": "0.00000",
                "vol": "0.02000000",
                "margin": "0.00000",
                "misc": "",
                "trade_id": 93748276,
                "maker": True
            },
            "TTEUX3-HDAAA-RC2RUO": {
                "ordertxid": "OH76VO-UKWAD-PSBDX6",
                "postxid": "TKH2SE-M7IF5-CFI7LT",
                "pair": "XXBTZEUR",
                "time": 1688082549.3138,
                "type": "buy",
                "ordertype": "limit",
                "price": "27732.00000",
                "cost": "0.20020",
                "fee": "0.00000",
                "vol": "0.00020000",
                "margin": "0.00000",
                "misc": "",
                "trade_id": 74625834,
                "maker": True
            }
        }

        result = account_data.querey_trades_info(
            "THVRQM-33VKH-UCI7BS,TTEUX3-HDAAA-RC2RUO"
        )

        assert isinstance(result, list)
        assert all(isinstance(item, Trade) for item in result)
        assert len(result) == 2

        assert result[0].txid == "THVRQM-33VKH-UCI7BS"
        assert result[0].ordertxid == "OQCLML-BW3P3-BUCMWZ"
        assert result[0].postxid == "TKH2SE-M7IF5-CFI7LT"
        assert result[0].pair == "XXBTZUSD"
        assert result[0].time == 1688667796.8802
        assert result[0].ordertype == OrderType.LIMIT
        assert result[0].price == Decimal("30010.00000")
        assert result[0].cost == Decimal("600.20000")
        assert result[0].fee == Decimal("0.00000")
        assert result[0].vol == Decimal("0.02000000")
        assert result[0].margin == Decimal("0.00000")
        assert result[0].misc == ""
        assert result[0].trade_id == 93748276
        assert result[0].maker is True

        assert result[1].txid == "TTEUX3-HDAAA-RC2RUO"
        assert result[1].ordertxid == "OH76VO-UKWAD-PSBDX6"
        assert result[1].postxid == "TKH2SE-M7IF5-CFI7LT"
        assert result[1].pair == "XXBTZEUR"
        assert result[1].time == 1688082549.3138
        assert result[1].type == OrderSide.BUY
        assert result[1].ordertype == OrderType.LIMIT

    # @pytest.mark.skip
    # @patch.object(AccountData, '_get_response')
    # def test_get_trade_volume(self, mock_get_response, account_data):
    #     mock_get_response.return_value = {
    #         "error": [],
    #         "result": {
    #             "currency": "ZUSD",
    #             "volume": "200709587.4223",
    #             "fees": {
    #                 "XXBTZUSD": {
    #                     "fee": "0.1000",
    #                     "minfee": "0.1000",
    #                     "maxfee": "0.2600",
    #                     "nextfee": None,
    #                     "nextvolume": None,
    #                     "tiervolume": "10000000.0000"
    #                 }
    #             },
    #             "fees_maker": {
    #                 "XXBTZUSD": {
    #                     "fee": "0.0000",
    #                     "minfee": "0.0000",
    #                     "maxfee": "0.1600",
    #                     "nextfee": None,
    #                     "nextvolume": None,
    #                     "tiervolume": "10000000.0000"
    #                 }
    #             }
    #         }
    #         }
    #     result = account_data.get_trade_volume("XXBTZUSD")


class TestTrading:
    @pytest.fixture
    def trading(self):
        with patch(
            "src.kraken_api.load_dotenv",
            lambda *args, **kwargs: None
        ):
            with patch.dict(
                os.environ,
                {"API_KEY": "test_key", "API_SECRET": "test_secret"},
                clear=True
            ):
                yield Trading()

    @patch.object(Trading, '_get_response')
    def test_add_order(self, mock_get_response, trading: Trading):
        mock_get_response.return_value = {
            "descr": {
                "order": "buy 1.45 XBTUSD @ limit 27500.0"
            },
            "txid": [
                "OU22CG-KLAF2-FWUDD7"
            ]
        }

        result = trading.add_order(
            ordertype=OrderType.LIMIT,
            orderside=OrderSide.BUY,
            volume=Decimal("1.45"),
            pair="XBTUSD",
            price=Decimal("27500.0")
        )

        assert isinstance(result, Order)

        assert result.txid == "OU22CG-KLAF2-FWUDD7"
        assert result.descr.ordertype == OrderType.LIMIT
        assert result.descr.type == OrderSide.BUY
        assert result.vol == Decimal("1.45")
        assert result.descr.pair == "XBTUSD"
        assert result.price == Decimal("27500.0")
        assert result.descr.price == Decimal("27500.0")

        # mock_get_response.return_value = {
        #     "error": [],
        #     "result": {
        #         "descr": {
        #             "order":
        #             "buy 2.12340000 XBTUSD "
        #             "@ limit 25000.1 with 2:1 leverage",
        #             "close": "close position "
        #             "@ stop loss 22000.0 -> limit 21000.0"
        #         },
        #         "txid": [
        #             "OUF4EM-FRGI2-MQMWZD"
        #         ]
        #     }
        # }

    @patch.object(Trading, '_get_response')
    def test_cancel_order(self, mock_get_response, trading: Trading):
        mock_get_response.return_value = {
            "count": 1
        }

        with pytest.raises(ValueError):
            result = trading.cancel_order()

        result = trading.cancel_order("OU22CG-KLAF2-FWUDD7")

        assert isinstance(result, int)
        assert result == 1
