from datetime import date, time
import os
from unittest.mock import MagicMock

import pytest

import investments.moex as m
from investments.instruments import CouponScheduleEntry, AmortizationScheduleEntry, OLHC, OLHCSeries


class TestMoex:
    def test_can_parse_bond(self, sample_bond_xml: str):
        bond = m.parse_coupon_schedule_xml(sample_bond_xml)
        assert bond.isin == "RU000A0JWSQ7"
        assert bond.name == "Мордовия 34003 обл."
        assert bond.initial_notional == 1000
        assert bond.notional_ccy == "RUB"

        assert bond.coupons == [
            CouponScheduleEntry(date(2016, 12, 9), None, date(2016, 9, 9), 29.17, 11.7),
            CouponScheduleEntry(date(2017, 3, 10), None, date(2016, 12, 9), 29.17, 11.7),
            CouponScheduleEntry(date(2017, 6, 9), None, date(2017, 3, 10), 29.17, 11.7),
            CouponScheduleEntry(date(2017, 9, 8), None, date(2017, 6, 9), 29.17, 11.7),
            CouponScheduleEntry(date(2017, 12, 8), date(2017, 12, 7), date(2017, 9, 8), 29.17, 11.7),
            CouponScheduleEntry(date(2018, 3, 9), date(2018, 3, 7), date(2017, 12, 8), 29.17, 11.7),
            CouponScheduleEntry(date(2018, 6, 8), date(2018, 6, 7),
                                # note start coupon date != prev coupon date! due to holidays.
                                # but coupon value disregards this start date and takes it from
                                # prev. coupon date
                                date(2018, 3, 12), 29.17, 11.7),
            CouponScheduleEntry(date(2018, 9, 7), date(2018, 9, 6), date(2018, 6, 8), 29.17, 11.7),
            CouponScheduleEntry(date(2018, 12, 7), date(2018, 12, 6), date(2018, 9, 7), 29.17, 11.7),
            CouponScheduleEntry(date(2019, 3, 8), date(2019, 3, 7), date(2018, 12, 7), 29.17, 11.7),
            CouponScheduleEntry(date(2019, 6, 7), date(2019, 6, 6), date(2019, 3, 8), 29.17, 11.7),
            CouponScheduleEntry(date(2019, 9, 6), date(2019, 9, 5), date(2019, 6, 7), 29.17, 11.7),
            CouponScheduleEntry(date(2019, 12, 6), date(2019, 12, 5), date(2019, 9, 6), 20.42, 11.7),
            CouponScheduleEntry(date(2020, 3, 6), date(2020, 3, 5), date(2019, 12, 6), 20.42, 11.7),
            CouponScheduleEntry(date(2020, 6, 5), date(2020, 6, 4), date(2020, 3, 6), 20.42, 11.7),
            CouponScheduleEntry(date(2020, 9, 4), date(2020, 9, 3), date(2020, 6, 5), 20.42, 11.7),
            CouponScheduleEntry(date(2020, 12, 4), date(2020, 12, 3), date(2020, 9, 4), 11.67, 11.7),
            CouponScheduleEntry(date(2021, 3, 5), date(2021, 3, 4), date(2020, 12, 4), 11.67, 11.7),
            CouponScheduleEntry(date(2021, 6, 4), date(2021, 6, 3), date(2021, 3, 5), 11.67, 11.7),
            CouponScheduleEntry(date(2021, 9, 3), date(2021, 9, 2), date(2021, 6, 4), 11.67, 11.7)
        ]

        assert bond.amortizations == [
            AmortizationScheduleEntry(date(2019, 9, 6), 30.0, 300.0),
            AmortizationScheduleEntry(date(2020, 9, 4), 30.0, 300.0),
            AmortizationScheduleEntry(date(2021, 9, 3), 40.0, 400.0)
        ]

        # assert our calculations match those from exchange
        for coupon in bond.coupons:
            try:
                assert coupon.value == bond.coupon_on_date(coupon.coupon_date)
            except:
                print(coupon)
                raise

    def test_can_parse_olhc(self, sample_olhc_csv: str):
        olhc: OLHCSeries = m.parse_olhc_csv("eurrub", sample_olhc_csv)
        assert not olhc.is_empty()
        s = olhc.olhc_series
        assert s[0] == OLHC(date(2005, 6, 20), open=34.79, low=34.7701, high=34.83, close=34.81, num_trades=21,
                            volume=157224489.9, waprice=34.8073)
        assert s[-1] == OLHC(date(2005, 11, 7), open=34.97, low=33.925, high=34.97, close=34.01, num_trades=57,
                             volume=142336864.5, waprice=34.0031)

    def test_can_load_full_olhc_from_partials(self):
        instr = "i"
        olhc1 = OLHC(date(2005, 6, 20), open=10.0, low=5.0, high=15.0, close=12.0, num_trades=1,
                     volume=100.0, waprice=11.0)
        olhc2 = OLHC(date(2005, 6, 23), open=10.0, low=5.0, high=15.0, close=13.0, num_trades=2,
                     volume=100.0, waprice=11.0)
        partial_replies = [OLHCSeries(instr, [olhc1]),
                           OLHCSeries(instr, [olhc2]),
                           OLHCSeries(instr, [])]
        mocked_loader = MagicMock(side_effect=partial_replies)
        full_table = m.load_olhc_table(instr, None, mocked_loader)
        assert not full_table.is_empty()
        assert full_table.olhc_series == [olhc1, olhc2]

    def test_can_parse_day_quotes(self, sample_today_rates_xml: str):
        today_quotes = m.parse_intraday_quotes(sample_today_rates_xml)
        assert today_quotes.instrument == "USD000UTSTOM"
        assert today_quotes.last == 74.415
        assert today_quotes.num_trades == 65036
        assert today_quotes.trading_status is False
        assert today_quotes.time == time(23, 49, 59)


@pytest.fixture()
def sample_bond_xml() -> str:
    with read_file("RU000A0JWSQ7.xml") as f:
        yield f.read()


@pytest.fixture()
def sample_olhc_csv() -> str:
    with read_file("eurrub.csv") as f:
        yield f.read()


@pytest.fixture()
def sample_today_rates_xml() -> str:
    with read_file("USD000UTSTOM.xml") as f:
        yield f.read()


def read_file(rel_name: str):
    # without abs path it cannot find file when running under unittest discover -
    # its current dir is two levels higher
    test_file_abs = os.path.join(os.path.dirname(__file__), rel_name)
    return open(test_file_abs, "r", encoding="utf-8")
