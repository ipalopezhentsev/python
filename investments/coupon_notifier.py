import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from email import encoders
from typing import List
import datetime
import argparse
import json
import sys

import requests
from bs4 import BeautifulSoup

ISS_URL = "https://iss.moex.com/iss/"

def old_main():
    CRLF = "\r\n"
    login = "iliks@mail.ru"
    password = ""  # mail.ru
    attendees = ["@mail.ru"]
    organizer = "ORGANIZER;CN=organiser:mailto:iliks" + CRLF + " @mail.ru"
    fro = "iliks@mail.ru"

    ddtstart = datetime.datetime.now()
    dtoff = datetime.timedelta(days=1)
    dur = datetime.timedelta(hours=1)
    ddtstart = ddtstart + dtoff
    dtend = ddtstart + dur
    dtstamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
    dtstart = ddtstart.strftime("%Y%m%dT%H%M%SZ")
    dtend = dtend.strftime("%Y%m%dT%H%M%SZ")

    description = "DESCRIPTION: test invitation from pyICSParser" + CRLF
    attendee = ""
    for att in attendees:
        attendee += "ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-    PARTICIPANT;PARTSTAT=ACCEPTED;RSVP=TRUE" + CRLF + " ;CN=" + att + ";X-NUM-GUESTS=0:" + CRLF + " mailto:" + att + CRLF
    ical = "BEGIN:VCALENDAR" + CRLF + "PRODID:pyICSParser" + CRLF + "VERSION:2.0" + CRLF + "CALSCALE:GREGORIAN" + CRLF
    ical += "METHOD:REQUEST" + CRLF + "BEGIN:VEVENT" + CRLF + "DTSTART:" + dtstart + CRLF + "DTEND:" + dtend + CRLF + "DTSTAMP:" + dtstamp + CRLF + organizer + CRLF
    ical += "UID:FIXMEUID" + dtstamp + CRLF
    ical += attendee + "CREATED:" + dtstamp + CRLF + description + "LAST-MODIFIED:" + dtstamp + CRLF + "LOCATION:" + CRLF + "SEQUENCE:0" + CRLF + "STATUS:CONFIRMED" + CRLF
    ical += "SUMMARY:test " + ddtstart.strftime(
        "%Y%m%d @ %H:%M") + CRLF + "TRANSP:OPAQUE" + CRLF + "END:VEVENT" + CRLF + "END:VCALENDAR" + CRLF

    eml_body = "Email body visible in the invite of outlook and outlook.com but not google calendar"
    eml_body_bin = "This is the email body in binary - two steps"
    msg = MIMEMultipart('mixed')
    msg['Reply-To'] = fro
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = "pyICSParser invite" + dtstart
    msg['From'] = fro
    msg['To'] = ",".join(attendees)

    part_email = MIMEText(eml_body, "html")
    part_cal = MIMEText(ical, 'calendar;method=REQUEST')

    # msgAlternative = MIMEMultipart('alternative')
    msgAlternative = MIMEMultipart('mixed')
    msg.attach(msgAlternative)

    # ical_atch = MIMEBase('application/ics', ' ;name="%s"' % "invite.ics")
    ical_atch = MIMEBase('text/calendar', ' ;name="%s"' % "invite.ics")
    ical_atch.set_payload(ical)
    encoders.encode_base64(ical_atch)
    ical_atch.add_header('Content-Disposition', 'attachment; filename="%s"' % "invite.ics")

    eml_atch = MIMEText('', 'plain')
    encoders.encode_base64(eml_atch)
    eml_atch.add_header('Content-Transfer-Encoding', "")

    msgAlternative.attach(part_email)
    msgAlternative.attach(part_cal)

    # mailServer = smtplib.SMTP('smtp.gmail.com', 587)
    # mailServer = smtplib.SMTP('smtp.mail.ru', 465)
    mailServer = smtplib.SMTP('smtp.mail.ru', 587)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(login, password)
    mailServer.sendmail(fro, attendees, msg.as_string())
    mailServer.close()


def load_coupon_schedule_json(isin: str)-> "json":
    url = f"{ISS_URL}{isin}/bondization.json"
    data = requests.get(url)
    return json.loads(data.text)


class AmmortizationScheduleEntry:
    pass

class CouponScheduleEntry:
    def __init__(self, coupon_date: datetime,
                 record_date: datetime,
                 start_date: datetime,
                 notional: float,
                 notional_ccy: str,
                 #in notional ccy:
                 value: float,
                 #in real percents, not in fractions of 1:
                 yearly_prc: float):
        self.coupon_date = coupon_date
        self.record_date = record_date
        self.start_date = start_date
        self.notional = notional
        self.notional_ccy = notional_ccy
        self.value = value
        self.yearly_prc = yearly_prc


class BondSchedule:
    def __init__(self, ammortizations: AmmortizationSchedule, coupons: CouponSchedule):

def parse_coupon_schedule(data: "json") -> List[CouponSchedule]:
    data["coupons"]["columns"].index("coupondate")
    #TODO: return sorted dict so I can easily find future coupons


def main():
    parser = argparse.ArgumentParser(description="Downloads official rates from Russian Central Bank and sends email "
                                                 "if there is a significant gap between today's and yesterday's rates",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--email", default="root",
                        help="E-mail address to which send warning mail in case rate jumps")
    args = parser.parse_args()
    isin = "RU000A0JXY44"
    load_coupon_schedule_json(isin)
    print(d.keys())


if __name__ == "__main__":
    main()
