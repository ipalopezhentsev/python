from __future__ import annotations

import datetime
import os.path
from dataclasses import dataclass
import csv
from math import sqrt
from typing import List, Optional, Callable, Any, Mapping

YEAR_BASE = 365


@dataclass(frozen=True)
class CouponScheduleEntry:
    coupon_date: datetime.date
    """date of holders fixing. can be missing"""
    record_date: Optional[datetime.date]
    """start of coupon accrual date"""
    start_date: datetime.date
    """in notional ccy. takes into account amortized notional"""
    value: float
    """in real percents, not in fractions of 1. Percents should be taken from notional active on coupon date"""
    yearly_prc: float

    def __post_init__(self):
        if self.coupon_date is None or self.start_date is None or self.value is None:
            raise ValueError("All arguments except record_date are mandatory")
        if self.value < 0.0 or self.yearly_prc < 0.0:
            raise ValueError("Value and percent should be positive")
        if self.record_date is not None and self.record_date > self.coupon_date:
            raise ValueError("Record date cannot be past coupon date")
        if self.start_date > self.coupon_date:
            raise ValueError("Cannot have start date past coupon date")


@dataclass(frozen=True)
class AmortizationScheduleEntry:
    """date after (!) which notional is amortized. i.e. if coupon fails on amortization date,
    the amount is paid without regard to this amortization, it will be seen only on next coupon"""
    amort_date: datetime.date
    """Percent of initial notional amortized. in real percents, not in fractions of 1"""
    value_prc: float
    """Amount on which notional is decreased in this date. in notional ccy"""
    value: float

    def __post_init__(self):
        if self.value < 0.0 or self.value_prc < 0.0:
            raise ValueError("Value and percent should be positive")


@dataclass(frozen=True)
class Bond:
    """coupons, ordered by date ascending"""
    coupons: List[CouponScheduleEntry]
    """amortizations (notional changes), ordered by date ascending. Last entry corresponds to settlement date,
    so even bonds without amortization will always contain one entry in this list"""
    amortizations: List[AmortizationScheduleEntry]
    isin: Optional[str] = None
    name: Optional[str] = None
    initial_notional: float = 1000.0
    notional_ccy: str = "RUB"

    # TODO: offers

    def __post_init__(self):
        if self.initial_notional is None or self.notional_ccy is None or \
                self.coupons is None or self.amortizations is None:
            raise ValueError("Mandatory fields not set")
        # check schedules go in increasing order (we depend on it while searching)
        self.__check_dates_ascending(self.amortizations, lambda e: e.amort_date)
        self.__check_dates_ascending(self.coupons, lambda e: e.coupon_date)
        self.__check_dates_ascending(self.coupons, lambda e: e.start_date)
        # check amortization schedule eventually repays notional (i.e. notional repayment at
        # settlement is also treated as amortization and must be present)
        percent_notional_amortized = 0.0
        notional_amortized = 0.0
        for am in self.amortizations:
            percent_notional_amortized += am.value_prc
            notional_amortized += am.value
        if percent_notional_amortized != 100.0:
            raise ValueError(f"Amortization schedule doesn't net to 100% of notional but to "
                             f"{percent_notional_amortized} (check that you have entry for settlement?)")
        if notional_amortized != self.initial_notional:
            raise ValueError(f"Amortization schedule doesn't return initial notional of {self.initial_notional}"
                             f" but to {notional_amortized}")

    @staticmethod
    def __check_dates_ascending(objs: List[Any], date_accessor: Callable[[Any], datetime.date]):
        prev_dt = None
        for entry in objs:
            dt = date_accessor(entry)
            if prev_dt is not None and dt <= prev_dt:
                raise ValueError(f"Schedule dates must be ascending, they are not: {prev_dt} vs {dt}")
            prev_dt = dt

    def notional_on_date(self, date: datetime.date) -> float:
        """returns effective notional on specified date, taking in account amortization schedule"""
        if date < self.amortizations[0].amort_date:
            return self.initial_notional
        elif date > self.amortizations[-1].amort_date:
            return 0
        else:
            accum_prc = 0.0
            for am in self.amortizations:
                if am.amort_date < date:
                    accum_prc += am.value_prc
                else:
                    break
            return self.initial_notional * (1.0 - accum_prc / 100.0)

    def coupon_on_date(self, dt: datetime.date) -> float:
        """returns coupon that should be received on dt or 0 if passed date is not from coupon schedule"""
        idx, coupon = next(filter(lambda c: c[1].coupon_date == dt, enumerate(self.coupons)), None)
        if coupon is None:
            return 0
        else:
            eff_notional = self.notional_on_date(coupon.coupon_date)
            # why? see attached test RU000A0JWSQ7.xml - coupon for 2018-06-08 has start date 2018-03-12, giving
            # 88 days diff, but the cited coupon value doesn't satisfy it, it's calculated from standard 91 days
            # diff, which appear only if we take previous coupon date 2018-03-09
            coupon_start = coupon.start_date if idx == 0 else self.coupons[idx - 1].coupon_date
            year_fract = (coupon.coupon_date - coupon_start).days / YEAR_BASE
            return round(eff_notional * (coupon.yearly_prc / 100.0) * year_fract, 2)

    def payments_since_date(self, dt: datetime.date) -> (List[CouponScheduleEntry], List[AmortizationScheduleEntry]):
        """Returns tuple where first element means coupons expected starting from the passed date (inclusively)
        and second element means the same for notional amortizations"""
        coupons = [coupon for coupon in self.coupons if coupon.coupon_date >= dt]
        amortizations = [amort for amort in self.amortizations if amort.amort_date >= dt]
        return coupons, amortizations


field_date = "DATE"
field_open = "OPEN"
field_low = "LOW"
field_high = "HIGH"
field_close = "CLOSE"
field_num_trades = "NUM_TRADES"
field_volume = "VOLUME"
field_waprice = "WAPRICE"
ohlc_fieldnames = [field_date, field_open, field_high, field_low, field_close,
                   field_num_trades, field_volume, field_waprice]


@dataclass(frozen=True)
class OHLC:
    date: datetime.date
    open: float
    high: float
    low: float
    close: float
    num_trades: int
    """in roubles (FX), in lots (bonds, shares)"""
    volume: float
    """average price in this interval weighted by volume of trades inside this interval"""
    waprice: float

    def __post_init__(self):
        if self.date is None:
            raise ValueError("Date must be filled")
        if self.low > self.high:
            raise ValueError(f"Low ({self.low}) should be >= High ({self.high})")
        if not (self.low <= self.open <= self.high):
            raise ValueError(f"Open ({self.open}) must be between Low ({self.low}) and High ({self.high})")
        if not (self.low <= self.close <= self.high):
            raise ValueError(f"Close ({self.close}) must be between Low ({self.low}) and High ({self.high})")
        # cannot check this as many bonds violate it
        # if not (self.low <= self.waprice <= self.high):
        #     raise ValueError(f"WAPrice ({self.waprice}) must be between Low ({self.low}) and High ({self.high})")

    def to_csv_row(self) -> Mapping[str, Any]:
        return {field_date: self.date.isoformat(), field_open: str(self.open), field_high: str(self.high),
                field_low: str(self.low), field_close: str(self.close), field_num_trades: str(self.num_trades),
                field_volume: str(self.volume), field_waprice: str(self.waprice)}

    @staticmethod
    def from_csv_row(row: Mapping[str, Any]) -> OHLC:
        return OHLC(date=datetime.date.fromisoformat(row[field_date]), open=float(row[field_open]),
                    high=float(row[field_high]), low=float(row[field_low]), close=float(row[field_close]),
                    num_trades=int(row[field_num_trades]), volume=float(row[field_volume]),
                    waprice=float(row[field_waprice]))


@dataclass()
class OHLCSeries:
    """it's meant to be just string, to not bring dependency on MOEX classes via Instrument"""
    instr_code: str
    """ordered by date ascending"""
    ohlc_series: List[OHLC]
    """longer user friendly name from exchange"""
    # TODO: persist to csv
    name: Optional[str] = None

    def __post_init__(self):
        prev_date: Optional[datetime.date] = None
        for entry in self.ohlc_series:
            cur_date = entry.date
            if prev_date is not None and prev_date >= cur_date:
                raise ValueError(f"Series must have ascending dates, they are not: {prev_date} vs {cur_date}")
            prev_date = cur_date

    def __str__(self) -> str:
        return "OHLCSeries[" + self.name if self.name is not None else self.instr_code + "]"

    def is_empty(self):
        return len(self.ohlc_series) == 0

    def append(self, other: OHLCSeries):
        """appends to this instance contents of the other table.
        Its dates must not intersect our dates and be higher than our last date."""
        if other.instr_code != self.instr_code:
            raise ValueError(f"Instruments do not match: {self.instr_code} vs {self.instr_code}")
        if other.is_empty():
            return
        if not self.is_empty():
            our_last_date: datetime.date = self.ohlc_series[-1].date
            their_last_date: datetime.date = other.ohlc_series[0].date
            if our_last_date >= their_last_date:
                raise ValueError(f"First date ({their_last_date}) must be > {our_last_date}")
        self.ohlc_series.extend(other.ohlc_series)
        if other.name is not None:
            self.name = other.name

    def save_to_csv(self, filename):
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=ohlc_fieldnames)
            writer.writeheader()
            for ohlc in self.ohlc_series:
                row = ohlc.to_csv_row()
                writer.writerow(row)

    @staticmethod
    def load_from_csv(filename) -> OHLCSeries:
        instr_code = os.path.splitext(os.path.basename(filename))[0]
        series: List[OHLC] = []
        with open(filename, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ohlc = OHLC.from_csv_row(row)
                series.append(ohlc)
        # TODO: persist name
        return OHLCSeries(instr_code, series, name=None)

    def mean_of_last_elems(self, num_elems: int,
                           field_getter: Callable[[OHLC], float] = lambda x: x.close) -> float:
        """gets average of last num_elems values of this series, for field specified by field_getter"""
        if len(self.ohlc_series) < num_elems:
            raise ValueError(f"Series has less than {num_elems}")
        agg_val = 0.0
        for ohlc in self.ohlc_series[-num_elems:]:
            agg_val += field_getter(ohlc)
        return agg_val / num_elems

    def std_dev_of_last_elems(self, num_elems,
                              field_getter: Callable[[OHLC], float] = lambda x: x.close,
                              mean: Optional[float] = None) -> float:
        """gets standard deviation of last num_elems values of this series, for field specified by field_getter"""
        if mean is None:
            mean = self.mean_of_last_elems(num_elems, field_getter)
        if len(self.ohlc_series) < num_elems:
            raise ValueError(f"Series has less than {num_elems}")
        agg_val = 0.0
        # "Corrected sample standard deviation"
        # TODO: std dev of log returns instead?
        for ohlc in self.ohlc_series[-num_elems:]:
            agg_val += (field_getter(ohlc) - mean) ** 2
        return sqrt(agg_val / (num_elems - 1))


@dataclass(frozen=True)
class IntradayQuote:
    instrument: str
    # price of last trade
    last: float
    num_trades: int
    # True if is trading at time of query
    is_trading: bool
    # time of latest trade?
    time: datetime.time


class MovingAvgCalculator:
    """calculates moving average given window size"""

    def __init__(self, window: int):
        if window < 2:
            raise ValueError("Window must be at least 2")
        self.window = window
        self.buffer: List[float] = [0.0] * window
        self.cur_idx = 0
        self.agg_sum = 0.0
        self.num_inserted = 0

    def add(self, elem: float) -> None:
        val_to_subtract = self.buffer[self.cur_idx]
        self.buffer[self.cur_idx] = elem
        self.agg_sum -= val_to_subtract
        self.agg_sum += elem
        self.cur_idx = self.cur_idx + 1 if self.cur_idx != self.window - 1 else 0
        # 'if' is for protection from overflow which will turn avg to None
        if self.num_inserted < self.window:
            self.num_inserted += 1

    def avg(self) -> Optional[float]:
        return self.agg_sum / self.window if self.num_inserted >= self.window else None
