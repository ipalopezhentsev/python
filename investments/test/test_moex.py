from datetime import date
import os

import pytest

import investments.moex as m
from investments.instruments import CouponScheduleEntry, AmortizationScheduleEntry


class TestMoex:
    def test_can_parse_bond(self, sample_bond_xml):
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


@pytest.fixture()
def sample_bond_xml():
    # without abs path it cannot find file when running under unittest discover -
    # its current dir is two levels higher
    test_file_abs = os.path.join(os.path.dirname(__file__), "RU000A0JWSQ7.xml")
    with open(test_file_abs, "r", encoding="utf-8") as f:
        yield f.read()
