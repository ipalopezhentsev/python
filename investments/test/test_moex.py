import unittest
from datetime import date
import investments.moex as m
from investments.instruments import CouponScheduleEntry, AmortizationScheduleEntry


class TestMoex(unittest.TestCase):
    def test_can_parse_bond(self):
        with open("RU000A0JWSQ7.xml", "r", encoding="utf-8") as f:
            xml = f.read()
        bond = m.parse_coupon_schedule_xml(xml)
        self.assertEqual(bond.isin, "RU000A0JWSQ7")
        self.assertEqual(bond.name, "Мордовия 34003 обл.")
        self.assertEqual(bond.initial_notional, 1000)
        self.assertEqual(bond.notional_ccy, "RUB")

        c = bond.coupons
        self.assertEqual(len(c), 20)
        self.assertEqual(c[0], CouponScheduleEntry(date(2016, 12, 9), None,
                                                   date(2016, 9, 9), 29.17, 11.7))
        self.assertEqual(c[1], CouponScheduleEntry(date(2017, 3, 10), None,
                                                   date(2016, 12, 9), 29.17, 11.7))
        self.assertEqual(c[2], CouponScheduleEntry(date(2017, 6, 9), None,
                                                   date(2017, 3, 10), 29.17, 11.7))
        self.assertEqual(c[3], CouponScheduleEntry(date(2017, 9, 8), None,
                                                   date(2017, 6, 9), 29.17, 11.7))
        self.assertEqual(c[4], CouponScheduleEntry(date(2017, 12, 8), date(2017, 12, 7),
                                                   date(2017, 9, 8), 29.17, 11.7))
        self.assertEqual(c[5], CouponScheduleEntry(date(2018, 3, 9), date(2018, 3, 7),
                                                   date(2017, 12, 8), 29.17, 11.7))
        self.assertEqual(c[6], CouponScheduleEntry(date(2018, 6, 8), date(2018, 6, 7),
                                                   # note start coupon date != prev coupon date! due to holidays.
                                                   # but coupon value disregards this start date and takes it from
                                                   # prev. coupon date
                                                   date(2018, 3, 12), 29.17, 11.7))
        self.assertEqual(c[7], CouponScheduleEntry(date(2018, 9, 7), date(2018, 9, 6),
                                                   date(2018, 6, 8), 29.17, 11.7))
        self.assertEqual(c[8], CouponScheduleEntry(date(2018, 12, 7), date(2018, 12, 6),
                                                   date(2018, 9, 7), 29.17, 11.7))
        self.assertEqual(c[9], CouponScheduleEntry(date(2019, 3, 8), date(2019, 3, 7),
                                                   date(2018, 12, 7), 29.17, 11.7))
        self.assertEqual(c[10], CouponScheduleEntry(date(2019, 6, 7), date(2019, 6, 6),
                                                    date(2019, 3, 8), 29.17, 11.7))
        self.assertEqual(c[11], CouponScheduleEntry(date(2019, 9, 6), date(2019, 9, 5),
                                                    date(2019, 6, 7), 29.17, 11.7))
        self.assertEqual(c[12], CouponScheduleEntry(date(2019, 12, 6), date(2019, 12, 5),
                                                    date(2019, 9, 6), 20.42, 11.7))
        self.assertEqual(c[13], CouponScheduleEntry(date(2020, 3, 6), date(2020, 3, 5),
                                                    date(2019, 12, 6), 20.42, 11.7))
        self.assertEqual(c[14], CouponScheduleEntry(date(2020, 6, 5), date(2020, 6, 4),
                                                    date(2020, 3, 6), 20.42, 11.7))
        self.assertEqual(c[15], CouponScheduleEntry(date(2020, 9, 4), date(2020, 9, 3),
                                                    date(2020, 6, 5), 20.42, 11.7))
        self.assertEqual(c[16], CouponScheduleEntry(date(2020, 12, 4), date(2020, 12, 3),
                                                    date(2020, 9, 4), 11.67, 11.7))
        self.assertEqual(c[17], CouponScheduleEntry(date(2021, 3, 5), date(2021, 3, 4),
                                                    date(2020, 12, 4), 11.67, 11.7))
        self.assertEqual(c[18], CouponScheduleEntry(date(2021, 6, 4), date(2021, 6, 3),
                                                    date(2021, 3, 5), 11.67, 11.7))
        self.assertEqual(c[19], CouponScheduleEntry(date(2021, 9, 3), date(2021, 9, 2),
                                                    date(2021, 6, 4), 11.67, 11.7))

        am = bond.amortizations
        self.assertEqual(len(am), 3)
        self.assertEqual(am[0], AmortizationScheduleEntry(date(2019, 9, 6), 30.0, 300.0))
        self.assertEqual(am[1], AmortizationScheduleEntry(date(2020, 9, 4), 30.0, 300.0))
        self.assertEqual(am[2], AmortizationScheduleEntry(date(2021, 9, 3), 40.0, 400.0))

        # assert our calculations match those from exchange
        for coupon in bond.coupons:
            try:
                self.assertEqual(coupon.value, bond.coupon_on_date(coupon.coupon_date))
            except:
                print(coupon)
                raise
