#!/usr/bin/env python3
from __future__ import annotations

import sys
from typing import List, MutableMapping, Dict, Mapping, Optional
import requests
import re
import datetime
import os
import os.path
import csv
import argparse
import smtplib
from dataclasses import dataclass
from email.mime.text import MIMEText

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class RatesInfo:
    rate: float
    ts: datetime


CcyPair = str


@dataclass(frozen=True)
class RatesViolation:
    rate_now: float
    rate_yesterday: float
    rel_diff: float


class RatesTable:
    def __init__(self, rates_by_dates: MutableMapping[datetime.date, MutableMapping[CcyPair, RatesInfo]]):
        self.by_dates = rates_by_dates

    def append_rates(self, other: RatesTable) -> bool:
        """Modifies self absorbing new info from the other argument and returns true if
        there were new data absorbed"""
        modified = False
        for date, other_rates_for_date in other.by_dates.items():
            if date not in self.by_dates:
                self.by_dates[date] = other_rates_for_date
                modified = True
            else:
                existing_for_date = self.by_dates[date]
                for ccy_pair, other_rate_for_pair in other_rates_for_date.items():
                    if ccy_pair not in existing_for_date:
                        existing_for_date[ccy_pair] = other_rate_for_pair
                        modified = True
        return modified

    def find_violating_rates(self, rel_eps: float) -> Dict[CcyPair, RatesViolation]:
        """Finds ccy pairs whose rates changed in relative terms more than specified rel_eps
        between last available day and the day before that"""
        sorted_dates = sorted(self.by_dates.keys())
        last_date = sorted_dates[-1]
        prev_date = sorted_dates[-2]
        last_rates: MutableMapping[CcyPair, RatesInfo] = self.by_dates[last_date]
        prev_rates: MutableMapping[CcyPair, RatesInfo] = self.by_dates[prev_date]
        violating_rates: Dict[CcyPair, RatesViolation] = {}
        for ccy_pair, last_rate_for_pair in last_rates.items():
            if ccy_pair in prev_rates:
                last_rate = last_rate_for_pair.rate
                prev_rate = prev_rates[ccy_pair].rate
                rel_diff = (last_rate - prev_rate) / max(abs(last_rate), abs(prev_rate))
                if rel_diff > rel_eps:
                    violating_rates[ccy_pair] = RatesViolation(last_rate, prev_rate, rel_diff)
        return violating_rates


def find_dates(indicators_parent) -> List[datetime.date]:
    indicators_dates = indicators_parent.find("div", class_="home-indicators_titles") \
        .find_all("div", class_="indicator_col-title")
    dates = []
    date_regex = re.compile(r"(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})")
    for header_item in indicators_dates:
        m = date_regex.search(header_item.string)
        day = m.group("day")
        month = m.group("month")
        year = m.group("year")
        date = datetime.date(int(year), int(month), int(day))
        dates.append(date)
    return dates


def find_ccy_pair(course_item) -> CcyPair:
    ccy = course_item.find("div", class_="indicator_el_title").text.strip()
    ccy = str(ccy).upper()
    if "США" in ccy:
        ccy_pair = "USDRUB"
    elif "ЕВРО" in ccy:
        ccy_pair = "EURRUB"
    else:
        ccy_pair = "UNKNOWN"
    return ccy_pair


def find_rates(dates: List[datetime.date], indicators_parent) -> RatesTable:
    rates_by_dates = {}
    indicators_courses = indicators_parent.find_all("div", class_="indicator_course")
    for course_item in indicators_courses:
        ccy_pair = find_ccy_pair(course_item)
        rates_for_ccy_pair = course_item.find_all("div", class_="indicator_el_value")
        idx_date = 0
        for rate_node in rates_for_ccy_pair:
            rate = rate_node.contents[0].string
            rate = float(rate.replace(",", "."))
            date = dates[idx_date]
            if date in rates_by_dates:
                for_date = rates_by_dates[date]
            else:
                for_date = {}
                rates_by_dates[date] = for_date
            for_date[ccy_pair] = RatesInfo(rate=rate, ts=datetime.datetime.now())
            idx_date += 1
    return RatesTable(rates_by_dates)


def download_fresh_rates_by_dates(cbr_html, html_dump_filename: Optional[str]) -> RatesTable:
    soup = BeautifulSoup(cbr_html, 'html.parser')
    # encoding needed for saving of rouble sign
    if html_dump_filename:
        with open(html_dump_filename, 'w', encoding='utf-8') as html_file:
            print(f'Dumping to {html_dump_filename}')
            html_file.write(soup.prettify())
    indicators_parent = soup.find("div", class_="indicators")
    dates = find_dates(indicators_parent)
    return find_rates(dates, indicators_parent)


def load_existing_rates(filename: str) -> RatesTable:
    rates_by_dates = {}
    if os.path.exists(filename):
        with open(filename, 'r') as ff:
            reader = csv.reader(ff)
            for line in reader:
                date = datetime.date.fromisoformat(line[0])
                ccy_pair = line[1]
                rate = float(line[2])
                ts = datetime.datetime.fromisoformat(line[3])
                if date not in rates_by_dates:
                    for_date = {}
                    rates_by_dates[date] = for_date
                else:
                    for_date = rates_by_dates[date]
                for_date[ccy_pair] = RatesInfo(rate, ts)
    return RatesTable(rates_by_dates)


def save_rates(rates_table: RatesTable, filename: str) -> None:
    with open(filename, 'w', newline='') as f:
        csv_writer = csv.writer(f)
        for date, rates_for_date in rates_table.by_dates.items():
            for ccy_pair, rates in rates_for_date.items():
                csv_writer.writerow((date, ccy_pair, rates.rate, rates.ts))


def send_mail(email_address: str, msg_header: str, msg_text: str) -> None:
    msg = MIMEText(msg_text)
    msg['Subject'] = msg_header
    msg['From'] = "cbr-rates-reporter"
    msg['To'] = email_address
    smtp = smtplib.SMTP('localhost')
    smtp.sendmail(msg['From'], [email_address], msg.as_string())
    smtp.quit()


def prepare_mail_text(violating_rates: Mapping[CcyPair, RatesViolation], rel_eps: float) -> (str, str):
    if len(violating_rates) != 0:
        header = f"WARN: {', '.join(violating_rates.keys())} rate jump"
        msg = f"The following rates jumped by more than {rel_eps * 100.0}%:\n"
        for ccy_pair, viol in violating_rates.items():
            msg += f"{ccy_pair}: {viol.rate_yesterday} -> {viol.rate_now} (rel.diff={100.0 * viol.rel_diff}%)\n"
    else:
        header = f"All rates jumped less than {rel_eps * 100.0}%\n"
        msg = ""
    return header, msg


def main() -> None:
    parser = argparse.ArgumentParser(description="Downloads official rates from Russian Central Bank and sends email "
                                                 "if there is a significant gap between today's and yesterday's rates",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--dump-html", action="store_true", default=False,
                        help="Dumps html page as it looked at time of parsing")
    parser.add_argument("--rel-eps", type=float, default=0.01,
                        help="Relative diff threshold between rate of yesterday "
                             "and rate of today to consider sending warning email")
    parser.add_argument("--email", default="root",
                        help="E-mail address to which send warning mail in case rate jumps")
    parser.add_argument("--rates-db", default="rates.csv",
                        help="File to which the script will append new rates")
    args = parser.parse_args()

    script_dir = os.path.dirname(sys.argv[0])
    rates_history_filename = os.path.join(script_dir, args.rates_db)
    html_dump_filename = os.path.join(script_dir, f"cbr-{str(datetime.datetime.now()).replace(':', '.')}.html") \
        if args.dump_html else None
    url = "https://cbr.ru"
    email = args.email
    rel_eps = args.rel_eps

    print(f'Working dir: {os.getcwd()}')
    print(f'Script dir: {script_dir}')
    print(f"Loading existing rates from {rates_history_filename}")
    rates_by_dates_existing = load_existing_rates(rates_history_filename)

    print(f"Downloading new rates from {url}")
    page = requests.get(url)
    rates_by_dates_delta = download_fresh_rates_by_dates(page.content, html_dump_filename)

    if rates_by_dates_existing.append_rates(rates_by_dates_delta):
        print(f"Saving new rates to {rates_history_filename}")
        save_rates(rates_by_dates_existing, rates_history_filename)
        violating_rates = rates_by_dates_existing.find_violating_rates(rel_eps)
        header, msg = prepare_mail_text(violating_rates, rel_eps)
        if msg != "":
            print("Jump detected, going to send mail:")
            print(header)
            print(msg)
            send_mail(email, header, msg)
        else:
            print("Skip sending mail, no rates jump")
    else:
        print("No changes since previous check")
    print("Done")


if __name__ == '__main__':
    main()
