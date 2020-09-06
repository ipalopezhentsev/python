import unittest
from datetime import date, timedelta

from investments.instruments import Bond, AmortizationScheduleEntry, CouponScheduleEntry, YEAR_BASE


class TestCouponScheduleEntry(unittest.TestCase):
    @unittest.expectedFailure
    def test_cannot_put_negative_value(self):
        CouponScheduleEntry(date(2019, 9, 6), date(2019, 9, 5), date(2019, 9, 3),
                            value=-1.0, yearly_prc=10.0)

    @unittest.expectedFailure
    def test_cannot_put_negative_prc(self):
        CouponScheduleEntry(date(2019, 9, 6), date(2019, 9, 5), date(2019, 9, 3),
                            value=1.0, yearly_prc=-10.0)

    @unittest.expectedFailure
    def test_cannot_put_record_date_after_coupon_date(self):
        CouponScheduleEntry(coupon_date=date(2019, 9, 6), record_date=date(2019, 9, 7), start_date=date(2019, 9, 3),
                            value=1.0, yearly_prc=10.0)

    @unittest.expectedFailure
    def test_cannot_put_start_date_after_coupon_date(self):
        CouponScheduleEntry(coupon_date=date(2019, 9, 6), record_date=date(2019, 9, 5), start_date=date(2019, 9, 7),
                            value=1.0, yearly_prc=10.0)


class TestBond(unittest.TestCase):
    @unittest.expectedFailure
    def test_cannot_create_bond_with_not_increasing_amort_dates(self):
        amortizations = [AmortizationScheduleEntry(date(2019, 9, 6), 30.0, 300.0),
                         # note date goes before first date, this is wrong
                         AmortizationScheduleEntry(date(2019, 9, 3), 70.0, 700.0)]
        Bond(coupons=[], amortizations=amortizations)

    @unittest.expectedFailure
    def test_cannot_create_bond_with_not_increasing_coupon_dates(self):
        amortizations = [AmortizationScheduleEntry(date(2019, 9, 3), 100.0, 1000.0)]
        coupons = [CouponScheduleEntry(date(2018, 1, 1), None, date(2017, 1, 1), 10.0, 10.0),
                   # note date goes before first date, this is wrong
                   CouponScheduleEntry(date(2017, 12, 1), None, date(2017, 11, 30), 10.0, 10.0)]
        Bond(coupons=coupons, amortizations=amortizations)

    @unittest.expectedFailure
    def test_cannot_create_bond_with_not_fully_amortized_notional_prc(self):
        amortizations = [AmortizationScheduleEntry(date(2019, 9, 3), 10.0, 100.0)]
        Bond(coupons=[], amortizations=amortizations)

    @unittest.expectedFailure
    def test_cannot_create_bond_with_not_fully_amortized_notional(self):
        amortizations = [AmortizationScheduleEntry(date(2019, 9, 3), 100.0, 999.0)]
        Bond(coupons=[], amortizations=amortizations)

    def test_notional_on_date(self):
        initial_notional = 1000
        am_dt1 = date(2019, 9, 6)
        am_dt2 = date(2020, 9, 4)
        am_dt3 = date(2021, 9, 3)
        amortizations = [AmortizationScheduleEntry(am_dt1, 30.0, 300.0),
                         AmortizationScheduleEntry(am_dt2, 30.0, 300.0),
                         AmortizationScheduleEntry(am_dt3, 40.0, 400.0)]
        b = Bond(initial_notional=initial_notional, coupons=[], amortizations=amortizations)
        # date before first amortization - notional should equal initial notional
        one_day = timedelta(days=1)

        self.assertEqual(b.notional_on_date(am_dt1 - one_day), initial_notional)
        # on amortization date - notional still stays the same, it affects only next coupons
        self.assertEqual(b.notional_on_date(am_dt1), initial_notional)
        notional_after_am_dt1 = initial_notional * (1 - amortizations[0].value_prc / 100.0)
        self.assertAlmostEqual(b.notional_on_date(am_dt1 + one_day), notional_after_am_dt1)

        self.assertEqual(b.notional_on_date(am_dt2 - one_day), notional_after_am_dt1)
        self.assertEqual(b.notional_on_date(am_dt2), notional_after_am_dt1)
        notional_after_am_dt2 = initial_notional * (
                1 - (amortizations[0].value_prc + amortizations[0].value_prc) / 100.0)
        self.assertAlmostEqual(b.notional_on_date(am_dt2 + one_day), notional_after_am_dt2)

        self.assertEqual(b.notional_on_date(am_dt3 - one_day), notional_after_am_dt2)
        self.assertEqual(b.notional_on_date(am_dt3), notional_after_am_dt2)
        # last amortization date is settlement date
        notional_after_settlement = 0.0
        self.assertAlmostEqual(b.notional_on_date(am_dt3 + one_day), notional_after_settlement)

    def test_coupon_on_date(self):
        initial_notional = 1000
        coup1_start_date = date(2017, 12, 8)
        coup1_date = date(2018, 3, 9)
        # note start coupon date != prev coupon date! due to holidays.
        # but coupon value disregards this start date and takes it from
        # prev. coupon date
        coup2_start_date = date(2018, 3, 12)
        coup2_date = date(2018, 6, 8)
        coupons = [CouponScheduleEntry(coup1_date, None, coup1_start_date, 0.0, 11.7),
                   CouponScheduleEntry(coup2_date, None, coup2_start_date, 0.0, 11.7)]
        amortizations = [AmortizationScheduleEntry(date(2018, 1, 1), 30.0, 300.0),
                         AmortizationScheduleEntry(coup2_date, 70.0, 700.0)]
        b = Bond(initial_notional=initial_notional, coupons=coupons, amortizations=amortizations)
        notional_on_coup2 = b.notional_on_date(coup2_date)
        self.assertEqual(notional_on_coup2, 700.0)
        # note we find days between coupon date 1 & 2, not from coupon 2 start/end date, because otherwise they
        # won't match due to different day counts due to holidays
        coupon_days = (coup2_date - coup1_date).days
        expected_coupon1 = round((coupon_days / YEAR_BASE) *
                                 (coupons[0].yearly_prc / 100.0) * notional_on_coup2, 2)
        coupon_days_wrong = (coup2_date - coupons[1].start_date).days
        expected_coupon1_wrong = round((coupon_days_wrong / YEAR_BASE) *
                                       (coupons[0].yearly_prc / 100.0) * notional_on_coup2, 2)
        self.assertAlmostEqual(b.coupon_on_date(coup2_date), expected_coupon1)
        self.assertNotAlmostEqual(expected_coupon1, expected_coupon1_wrong)

    def test_payments_since_date(self):
        coup1_start_date = date(2017, 12, 8)
        coup1_date = date(2018, 3, 9)
        coup2_start_date = date(2018, 3, 12)
        coup2_date = date(2018, 6, 8)
        coupons = [CouponScheduleEntry(coup1_date, None, coup1_start_date, 0.0, 11.7),
                   CouponScheduleEntry(coup2_date, None, coup2_start_date, 0.0, 11.7)]
        amortizations = [AmortizationScheduleEntry(date(2018, 1, 1), 30.0, 300.0),
                         AmortizationScheduleEntry(coup2_date, 70.0, 700.0)]
        b = Bond(coupons=coupons, amortizations=amortizations)
        cps, ams = b.payments_since_date(date(2018, 5, 8))
        assert cps == [coupons[1]]
        assert ams == [amortizations[1]]


if __name__ == '__main__':
    unittest.main()
