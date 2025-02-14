
import pytest
from decimal import Decimal
from unittest.mock import patch
from src.grid import GridStrategy
from src.kraken_api import TickerInfo, TradableAssetPair


@pytest.fixture
def valid_params():
    return {
        "pair": "ETH/XBT",
        "base_price": Decimal("3000.0"),
        "percentage": Decimal("0.02"),
        "total_volume": Decimal("150"),
        "rung_count": 5,
    }


@pytest.fixture
def mock_ticker_info():
    return TickerInfo(
        name="XETHXXBT",
        a=[
            Decimal("30300.10000"),
            Decimal("1"),
            Decimal("1.000")
        ],
        b=[
            Decimal("30300.10000"),
            Decimal("1"),
            Decimal("1.000")],
        c=[
            Decimal("30303.20000"),
            Decimal("0.00067643")
        ],
        v=[
            Decimal("4083.67001100"),
            Decimal("4412.73601799")
        ],
        p=[
            Decimal("30706.77771"),
            Decimal("30689.13205")
        ],
        t=[
            34619,
            38907
        ],
        l=[
            Decimal("29868.30000"),
            Decimal("29868.30000")
        ],
        h=[
            Decimal("31631.00000"),
            Decimal("31631.00000")
        ],
        o=Decimal("30502.80000")
    )


@pytest.fixture
def mock_tradable_pairs():
    return [
        TradableAssetPair(
            name='ETH/XBT',
            altname='ETHXBT',
            wsname='ETH/XBT',
            aclass_base='currency',
            base='XETH',
            aclass_quote='currency',
            quote='XXBT',
            lot='unit',
            cost_decimals=6,
            pair_decimals=5,
            lot_decimals=8,
            lot_multiplier=1,
            leverage_buy=[2, 3, 4, 5],
            leverage_sell=[2, 3, 4, 5],
            fees=[(0, Decimal('0.26')), (50000, Decimal('0.24'))],
            fees_maker=[(0, Decimal('0.16')), (50000, Decimal('0.14'))],
            fee_volume_currency='ZUSD',
            margin_call=80,
            margin_stop=40,
            ordermin=Decimal('0.01'),
            costmin=Decimal('0.00002'),
            tick_size=Decimal('0.00001'),
            status='online',
            long_position_limit=1100,
            short_position_limit=400
        )
    ]


class TestGridStrategy:
    @pytest.mark.parametrize("invalid_param, value", [
        ("base_price", Decimal('-1000')),
        ("percentage", Decimal("-0.1")),
        ("total_volume", Decimal("-10")),
        ("rung_count", 1),
    ])
    @patch("src.grid.MarketData.get_ticker_information")
    @patch("src.grid.MarketData.get_tradable_asset_pairs")
    def test_validate_inputs(
        self,
        mock_get_tradable_asset_pairs,
        mock_get_ticker_information,
        valid_params,
        invalid_param,
        value,
        mock_tradable_pairs
    ):
        valid_params[invalid_param] = value
        mock_get_tradable_asset_pairs.return_value = mock_tradable_pairs
        with pytest.raises(ValueError):
            GridStrategy(**valid_params)

    @patch("src.grid.MarketData.get_ticker_information")
    @patch("src.grid.MarketData.get_tradable_asset_pairs")
    def test_check_valid_pair(
        self,
        mock_get_tradable_asset_pairs,
        mock_get_ticker_information,
        mock_tradable_pairs
    ):
        mock_get_tradable_asset_pairs.return_value = mock_tradable_pairs
        try:
            GridStrategy(
                pair="ETH/XBT",
                base_price=Decimal("3000.0"),
                percentage=Decimal("0.02"),
                total_volume=Decimal("150"),
                rung_count=5
            )
        except ValueError:
            pytest.fail("GridStrategy raised ValueError for a valid pair")

        def test_check_invalid_pair(
            self,
            mock_get_tradable_asset_pairs,
            valid_params,
            mock_tradable_pairs
        ):
            mock_get_tradable_asset_pairs.return_value = mock_tradable_pairs
            with pytest.raises(ValueError):
                GridStrategy(
                    pair="ABC/EFG",
                    base_price=valid_params['base_price'],
                    percentage=valid_params['percentage'],
                    total_volume=valid_params['total_volume'],
                    rung_count=valid_params['rung_count'],
                )

    @patch("src.grid.MarketData.get_ticker_information")
    @patch("src.grid.MarketData.get_tradable_asset_pairs")
    def test_update_price(
        self,
        mock_get_tradable_asset_pairs,
        mock_get_ticker_information,
        mock_tradable_pairs,
        mock_ticker_info
    ):
        mock_get_tradable_asset_pairs.return_value = mock_tradable_pairs
        mock_get_ticker_information.return_value = mock_ticker_info
        strategy = GridStrategy(
            pair="ETH/XBT",
            base_price=Decimal("3000.0"),
            percentage=Decimal("0.02"),
            total_volume=Decimal("150"),
            rung_count=5
        )
        assert strategy.pair == "ETH/XBT"
        assert strategy.current_ask == Decimal("30300.10000")
        assert strategy.current_bid == Decimal("30300.10000")

    @patch("src.grid.MarketData.get_ticker_information")
    @patch("src.grid.MarketData.get_tradable_asset_pairs")
    def test_create_rungs(
        self,
        mock_get_tradable_asset_pairs,
        mock_get_ticker_information,
        mock_tradable_pairs
    ):
        mock_get_tradable_asset_pairs.return_value = mock_tradable_pairs

        strategy = GridStrategy(
            pair="ETH/XBT",
            base_price=Decimal("3000.0"),
            percentage=Decimal("0.02"),
            total_volume=Decimal("150"),
            rung_count=5
        )
        strategy.create_rungs()

        assert len(strategy.rungs) == 5
        assert strategy.rungs[0].price == Decimal("3000.0")
        assert strategy.rungs[-1].price == (
            Decimal("3000.0") * ((1 + Decimal("0.02")) ** 4)
        )
        assert strategy.rungs[0].volume == Decimal("150") / 5
        assert all(
            rung.volume == Decimal("150") / 5 for rung in strategy.rungs
        )
        assert all(
            rung.order is None for rung in strategy.rungs
        )
