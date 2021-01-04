from __future__ import annotations
import logging
import xml.etree.ElementTree as ET
import datetime
from typing import Callable, Optional
from abc import ABC, abstractmethod
import investments.logsetup

import requests
import csv

from investments.instruments import Bond, AmortizationScheduleEntry, CouponScheduleEntry, OHLC, OHLCSeries, \
    IntradayQuote

ISS_URL = "https://iss.moex.com/iss/"
logger = logging.getLogger(__name__)


def load_coupon_schedule_xml(isin: str) -> str:
    url = f"{ISS_URL}securities/{isin}/bondization.xml?iss.meta=off"
    data = requests.get(url)
    return data.text


def __parse_am_entry(am_entry) -> AmortizationScheduleEntry:
    str_date = am_entry.get("amortdate")
    am_date = datetime.date.fromisoformat(str_date)
    value_prc = float(am_entry.get("valueprc"))
    value = float(am_entry.get("value"))
    return AmortizationScheduleEntry(am_date, value_prc, value)


def __parse_coupon_entry(cp_entry) -> CouponScheduleEntry:
    cp_date = datetime.date.fromisoformat(cp_entry.get("coupondate"))
    str_rec_date = cp_entry.get("recorddate")
    rec_date = datetime.date.fromisoformat(str_rec_date) if str_rec_date != "" else None
    st_date = datetime.date.fromisoformat(cp_entry.get("startdate"))
    val = float(cp_entry.get("value"))
    yearly_prc = float(cp_entry.get("valueprc"))
    return CouponScheduleEntry(cp_date, rec_date, st_date, val, yearly_prc)


def parse_coupon_schedule_xml(data: str) -> Bond:
    root = ET.fromstring(data)
    first_row = next(root.iter("row"))
    isin = first_row.get("isin")
    name = first_row.get("name")
    # note: reply rows contain "facevalue" but it's incorrect, it's "current facevalue"
    initial_notional = float(first_row.get("initialfacevalue"))
    notional_ccy = first_row.get("faceunit")

    am_schedule = [__parse_am_entry(am_entry) for am_entry in root.findall(".//data[@id='amortizations']//row")]
    cp_schedule = [__parse_coupon_entry(cp_entry) for cp_entry in root.findall(".//data[@id='coupons']//row")]

    return Bond(isin=isin, name=name, initial_notional=initial_notional, notional_ccy=notional_ccy,
                coupons=cp_schedule, amortizations=am_schedule)


def load_bond(isin: str) -> Bond:
    xml = load_coupon_schedule_xml(isin)
    return parse_coupon_schedule_xml(xml)


def parse_ohlc_csv(instr: str, reply: str) -> OHLCSeries:
    lines = reply.split("\n")[2:]
    # note field names in moex reply are OLHC (parsed here), but our native csv
    # (in instruments module) is OHLC as market convention
    reader = csv.DictReader(lines, delimiter=";")
    series = []
    for row in reader:
        try:
            num_trades = int(row["NUMTRADES"])
            date = datetime.date.fromisoformat(row["TRADEDATE"])
            if num_trades != 0:
                ohlc = OHLC(date=date, open=float(row["OPEN"]),
                            low=float(row["LOW"]), high=float(row["HIGH"]), close=float(row["CLOSE"]),
                            num_trades=num_trades, volume=float(row["VOLRUR"]), waprice=float(row["WAPRICE"]))
                series.append(ohlc)
            else:
                logger.info(f"Skipping {date} for {instr} as it had no trades")

        except ValueError as e:
            raise ValueError(f"Error happened for row {row}", e)
    return OHLCSeries(instr, series)


def __load_partial_ohlc_table_csv(instr: str, from_date: Optional[datetime.date]) -> OHLCSeries:
    """Loads certain number of lines from from_date. So to read the whole available
    data you must call this function until it returns empty table"""
    fr = ""
    if from_date is not None:
        fr = f"?from={from_date.isoformat()}"
    url = f"{ISS_URL}history/engines/currency/markets/selt/boards/cets/securities/{instr}/candleborders.csv{fr}"

    # will return not more than 100 entries from the beginning of history
    reply = requests.get(url).text
    return parse_ohlc_csv(instr, reply)


def load_ohlc_table(instr: str, from_date: Optional[datetime.date] = None,
                    partial_loader: Callable[[str, Optional[datetime.date]], OHLCSeries]
                    = __load_partial_ohlc_table_csv) -> OHLCSeries:
    """Loads full history of rates of specified instrument, starting from from_date"""
    series = OHLCSeries(instr, [])
    date = from_date
    while True:
        logger.info(f"Loading {instr} from {date if date is not None else 'beginning'}")
        addition = partial_loader(instr, date)
        if addition.is_empty():
            break
        else:
            series.append(addition)
            date = addition.ohlc_series[-1].date + datetime.timedelta(days=1)
    return series


def parse_intraday_quotes(reply: str) -> IntradayQuote:
    root = ET.fromstring(reply)
    row = root.findall(".//data[@id='marketdata']//row")[0]

    # TRADINGSTATUS is "T"/"N"
    is_trading = True if row.get("TRADINGSTATUS") == "T" else False
    return IntradayQuote(instrument=row.get("SECID"), last=float(row.get("LAST")),
                         num_trades=int(row.get("NUMTRADES")), is_trading=is_trading,
                         time=datetime.time.fromisoformat(row.get("TIME")))


def load_intraday_quotes(instr: str) -> IntradayQuote:
    url = f"{ISS_URL}engines/currency/markets/selt/boards/CETS/securities/{instr}.xml?iss.meta=off"
    data = requests.get(url)
    return parse_intraday_quotes(data.text)
