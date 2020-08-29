import xml.etree.ElementTree as ET
from datetime import date

import requests

from investments.instruments import Bond, AmortizationScheduleEntry, CouponScheduleEntry

ISS_URL = "https://iss.moex.com/iss/"


def load_coupon_schedule_xml(isin: str) -> str:
    url = f"{ISS_URL}securities/{isin}/bondization.xml?iss.meta=off"
    data = requests.get(url)
    return data.text


def __parse_am_entry(am_entry) -> AmortizationScheduleEntry:
    str_date = am_entry.get("amortdate")
    am_date = date.fromisoformat(str_date)
    value_prc = float(am_entry.get("valueprc"))
    value = float(am_entry.get("value"))
    return AmortizationScheduleEntry(am_date, value_prc, value)


def __parse_coupon_entry(cp_entry) -> CouponScheduleEntry:
    cp_date = date.fromisoformat(cp_entry.get("coupondate"))
    str_rec_date = cp_entry.get("recorddate")
    rec_date = date.fromisoformat(str_rec_date) if str_rec_date != "" else None
    st_date = date.fromisoformat(cp_entry.get("startdate"))
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
