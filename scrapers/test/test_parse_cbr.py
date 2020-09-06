import os.path
from datetime import date, datetime, timedelta

import pytest

from scrapers.parse_cbr import RatesInfo, download_fresh_rates_by_dates
from scrapers.parse_cbr import RatesTable


class TestRatesInfo:
    def test_can_read_properties(self):
        r = 2.0
        ts = datetime.now()
        subj = RatesInfo(r, ts)
        assert subj.rate == r
        assert subj.ts == ts
        ts = ts + timedelta(hours=1)
        assert subj.ts != ts


class TestRatesTable:
    def test_basic_usage(self):
        subj = RatesTable({date(2020, 7, 14):
                               {"EURRUB": RatesInfo(80, datetime.now()),
                                "USDRUB": RatesInfo(75, datetime.now())}
                           })
        assert date(2020, 7, 14) in subj.by_dates
        assert len(subj.by_dates[date(2020, 7, 14)]) == 2

    def test_append_rates(self):
        subj = RatesTable({})
        subj.append_rates(RatesTable({date(2020, 7, 14): {
            "EURRUB": RatesInfo(80, datetime.now())
        }}))
        assert date(2020, 7, 14) in subj.by_dates
        assert len(subj.by_dates[date(2020, 7, 14)]) == 1
        subj.append_rates(RatesTable({date(2020, 7, 14): {
            "USDRUB": RatesInfo(75, datetime.now())
        }}))
        d = subj.by_dates[date(2020, 7, 14)]
        assert "EURRUB" in d
        assert "USDRUB" in d
        assert d["EURRUB"].rate == 80
        assert d["USDRUB"].rate == 75

    def test_find_violating_rates(self):
        d1 = date(2020, 7, 14)
        d2 = date(2020, 7, 15)
        eur_on_d1 = 75
        usd_on_d1 = 70
        eps = 0.01
        now = datetime.now()
        # make eur violate eps
        eur_on_d2 = eur_on_d1 * (1 + eps + 0.001)
        # and usd not
        usd_on_d2 = usd_on_d1 * (1 + eps - 0.001)
        subj = RatesTable({d1: {"EURRUB": RatesInfo(eur_on_d1, now),
                                "USDRUB": RatesInfo(usd_on_d1, now)},
                           d2: {"EURRUB": RatesInfo(eur_on_d2, now),
                                "USDRUB": RatesInfo(usd_on_d2, now)}})
        viols = subj.find_violating_rates(eps)
        assert "EURRUB" in viols
        assert "USDRUB" not in viols


def test_can_parse_html(html_dump):
    rates_table = download_fresh_rates_by_dates(html_dump, None)
    assert set(rates_table.by_dates.keys()) == {date(2020, 9, 4), date(2020, 9, 5)}
    d1 = rates_table.by_dates[date(2020, 9, 4)]
    assert set(d1.keys()) == {"EURRUB", "USDRUB"}
    assert d1["EURRUB"].rate == pytest.approx(89.1353)
    assert d1["USDRUB"].rate == pytest.approx(75.4680)
    d2 = rates_table.by_dates[date(2020, 9, 5)]
    assert set(d2.keys()) == {"EURRUB", "USDRUB"}
    assert d2["EURRUB"].rate == pytest.approx(89.0384)
    assert d2["USDRUB"].rate == pytest.approx(75.1823)


@pytest.fixture()
def html_dump():
    fname = os.path.join(os.path.dirname(__file__), "test.html")
    with open(fname, "r", encoding="utf-8") as f:
        yield f
