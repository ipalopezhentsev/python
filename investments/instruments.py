from datetime import date
from dataclasses import dataclass
from typing import List, Optional, Callable, Any

YEAR_BASE = 365


@dataclass(frozen=True)
class CouponScheduleEntry:
    coupon_date: date
    """date of holders fixing. can be missing"""
    record_date: Optional[date]
    """start of coupon accrual date"""
    start_date: date
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
    amort_date: date
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
    def __check_dates_ascending(objs: List[Any], date_accessor: Callable[[Any], date]):
        prev_dt = None
        for entry in objs:
            dt = date_accessor(entry)
            if prev_dt is not None and dt <= prev_dt:
                raise ValueError(f"Schedule dates must be ascending, they are not: {prev_dt} vs {dt}")
            prev_dt = dt

    def notional_on_date(self, date: date) -> float:
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

    def coupon_on_date(self, dt: date) -> float:
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

    def payments_since_date(self, dt: date) -> (List[CouponScheduleEntry], List[AmortizationScheduleEntry]):
        """Returns tuple where first element means coupons expected starting from the passed date (inclusively)
        and second element means the same for notional amortizations"""
        coupons = [coupon for coupon in self.coupons if coupon.coupon_date >= dt]
        amortizations = [amort for amort in self.amortizations if amort.amort_date >= dt]
        return coupons, amortizations
