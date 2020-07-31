import unittest
from datetime import date, datetime

from scrapers.parse_cbr import RatesInfo
from scrapers.parse_cbr import RatesTable


class TestRatesInfo(unittest.TestCase):
    def test_can_read_properties(self):
        r = 2.0
        ts = datetime.now()
        subj = RatesInfo(r, ts)
        self.assertEqual(subj.rate, r)
        self.assertEqual(subj.ts, ts)
        ts = datetime.now()
        self.assertNotEqual(subj.ts, ts)


class TestRatesTable(unittest.TestCase):
    def test_basic_usage(self):
        subj = RatesTable({date(2020, 7, 14):
                               {"EURRUB": RatesInfo(80, datetime.now()),
                                "USDRUB": RatesInfo(75, datetime.now())}
                           })
        self.assertTrue(date(2020,7,14) in subj.by_dates)
        self.assertEqual(len(subj.by_dates[date(2020,7,14)]), 2)

    def test_append_rates(self):
        subj = RatesTable({})
        subj.append_rates(RatesTable({date(2020,7,14): {
            "EURRUB": RatesInfo(80, datetime.now())
        }}))
        self.assertTrue(date(2020,7,14) in subj.by_dates)
        self.assertEqual(len(subj.by_dates[date(2020,7,14)]),1)
        subj.append_rates(RatesTable({date(2020,7,14): {
            "USDRUB": RatesInfo(75, datetime.now())
        }}))
        d = subj.by_dates[date(2020,7,14)]
        self.assertTrue("EURRUB" in d)
        self.assertTrue("USDRUB" in d)
        self.assertEqual(d["EURRUB"].rate, 80)
        self.assertEqual(d["USDRUB"].rate, 75)

    def test_find_violating_rates(self):
        d1 = date(2020,7,14)
        d2 = date(2020,7,15)
        eur_on_d1 = 75
        usd_on_d1 = 70
        eps = 0.01
        now = datetime.now()
        #make eur violate eps
        eur_on_d2 = eur_on_d1 * (1 + eps + 0.001)
        #and usd not
        usd_on_d2 = usd_on_d1 * (1 + eps - 0.001)
        subj = RatesTable({d1: {"EURRUB": RatesInfo(eur_on_d1, now),
                                "USDRUB": RatesInfo(usd_on_d1, now)},
                           d2: {"EURRUB": RatesInfo(eur_on_d2, now),
                                "USDRUB": RatesInfo(usd_on_d2, now)}})
        viols = subj.find_violating_rates(eps)
        self.assertTrue("EURRUB" in viols)
        self.assertTrue("USDRUB" not in viols)


if __name__ == '__main__':
    unittest.main()
