#!/usr/bin/python3
import sys
import requests
import re
import datetime
import os
from pathlib import Path
import csv
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText


def find_dates(indicators_parent):
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


def find_ccy_pair(course_item) -> str:
    ccy = course_item.find("div", class_="indicator_el_title").text.strip()
    ccy = str(ccy).upper()
    if "США" in ccy:
        ccy_pair = "USDRUB"
    elif "ЕВРО" in ccy:
        ccy_pair = "EURRUB"
    else:
        ccy_pair = "UNKNOWN"
    return ccy_pair


def find_rates(dates, indicators_parent):
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
            for_date[ccy_pair] = dict(rate=rate, ts=datetime.datetime.now())
            idx_date += 1
    return rates_by_dates


def download_fresh_rates_by_dates(url, html_dump_filename):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
# encoding needed for saving of rouble sign
    with open(html_dump_filename, 'w', encoding='utf-8') as html_file:
        print(f'Dumping to {html_dump_filename}')
        html_file.write(soup.prettify())
    indicators_parent = soup.find("div", class_="indicators")
    dates = find_dates(indicators_parent)
    rates_by_dates = find_rates(dates, indicators_parent)
    return rates_by_dates


def load_existing_rates(filename):
    f = Path(filename)
    rates_by_dates = {}
    if f.exists():
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
                for_date[ccy_pair] = dict(rate=rate, ts=ts)
    return rates_by_dates


def save_rates(rates_by_dates, filename):
    with open(filename, 'w', newline='') as f:
        csv_writer = csv.writer(f)
        for date, rates_for_date in rates_by_dates.items():
            for ccy_pair, rates in rates_for_date.items():
                rate = rates["rate"]
                ts = rates["ts"]
                csv_writer.writerow([date, ccy_pair, rate, ts])


# returns true if there were changes applied to rates_by_dates_existing
def append_rates(rates_by_dates_existing, rates_by_dates_delta):
    modified = False
    for date, new_rates_for_date in rates_by_dates_delta.items():
        if date not in rates_by_dates_existing:
            rates_by_dates_existing[date] = new_rates_for_date
            modified = True
        else:
            existing_for_date = rates_by_dates_existing[date]
            for ccy_pair, rates in new_rates_for_date.items():
                if ccy_pair not in existing_for_date:
                    existing_for_date[ccy_pair] = rates
                    modified = True
    return modified


def send_mail(email_address, msg_header, msg_text):
    msg = MIMEText(msg_text)
    msg['Subject'] = msg_header
    msg['From'] = "cbr-rates-reporter"
    msg['To'] = email_address
    s = smtplib.SMTP('localhost')
    s.sendmail(msg['From'], [email_address], msg.as_string())
    s.quit()


def prepare_mail_text(rates_by_dates_existing, rel_eps):
    sorted_dates = sorted(rates_by_dates_existing.keys())
    last_date = sorted_dates[-1]
    prev_date = sorted_dates[-2]

    last_rates = rates_by_dates_existing[last_date]
    prev_rates = rates_by_dates_existing[prev_date]

    violating_rates = {}
    for ccy_pair, last_rates in last_rates.items():
        if ccy_pair in prev_rates:
            last_rate = last_rates["rate"]
            prev_rate = prev_rates[ccy_pair]["rate"]
            rel_diff = abs(last_rate - prev_rate) / max(abs(last_rate), abs(prev_rate))
            if rel_diff > rel_eps:
                violating_rates[ccy_pair] = dict(rate_now=last_rate, rate_yesterday=prev_rate, rel_diff=rel_diff)

    if len(violating_rates) != 0:
        header = f"WARN: {', '.join(violating_rates.keys())} rate jump"
        msg = f"The following rates jumped by more than {rel_eps * 100.0}%:\n"
        for item in violating_rates.items():
            msg += f"{item[0]}: {item[1]['rate_yesterday']} -> {item[1]['rate_now']} (rel.diff={100.0*item[1]['rel_diff']}%)\n"
    else:
        header = f"All rates jumped less than {rel_eps * 100.0}%\n"
        msg = ""
    return header, msg


def main():
    script_dir = sys.path[0]
    rates_history_filename = f"{script_dir}/rates.csv"
    html_dump_filename = f"{script_dir}/cbr-{str(datetime.datetime.now()).replace(':', '.')}.html"
    url = "https://cbr.ru"
    email = "root"
    rel_eps = 0.01

    print(f'Working dir: {os.getcwd()}')
    print(f'Script dir: {script_dir}')
    print(f"Loading existing rates from {rates_history_filename}")
    rates_by_dates_existing = load_existing_rates(rates_history_filename)

    print(f"Downloading new rates from {url}")
    rates_by_dates_delta = download_fresh_rates_by_dates(url, html_dump_filename)

    if append_rates(rates_by_dates_existing, rates_by_dates_delta):
        print(f"Saving new rates to {rates_history_filename}")
        save_rates(rates_by_dates_existing, rates_history_filename)

        header, msg = prepare_mail_text(rates_by_dates_existing, rel_eps)
        if msg != "":
            send_mail(email, header, msg)
            print(header)
            print(msg)
        else:
            print("Skip sending mail, no rates jump")
    else:
        print("No changes since previous check")
    print("Done")


if __name__ == '__main__':
    main()
