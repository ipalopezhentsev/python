import os
import sys
import signal
import argparse
import smtplib
from dataclasses import dataclass
from email.mime.text import MIMEText
import sched
from typing import List, Dict, Optional, Set

from investments import moex, instruments
import logging
import datetime
import investments.logsetup

logger = logging.getLogger(__name__)
one_day = datetime.timedelta(days=1)


def code_to_filename(code: str):
    return code + ".csv"


def get_initial_series(codes: List[str]) -> Dict[str, instruments.OHLCSeries]:
    res = {}
    for code in codes:
        try:
            fname = code_to_filename(code)
            if os.path.exists(fname):
                series = instruments.OHLCSeries.load_from_csv(fname)
            else:
                series = instruments.OHLCSeries(code, [])
        except Exception as e:
            logger.error(f"Error loading initial data for {code}", exc_info=e, stack_info=True)
            # give it chance to load from http
            series = instruments.OHLCSeries(code, [])
        res[code] = series
    return res


def refresh_series(cur_series: Dict[str, instruments.OHLCSeries]) \
        -> (Dict[str, instruments.OHLCSeries], Dict[str, Exception]):
    """gets new entries into series from web. Returns dict of instrument to loading error"""
    good_series = {}
    errors = {}
    for instr, series in cur_series.items():
        try:
            if not series.is_empty():
                from_date = series.ohlc_series[-1].date + one_day
            else:
                from_date = None
            addition = moex.load_ohlc_table(instr, from_date)
            series.append(addition)
            good_series[instr] = series
        except Exception as ex:
            errors[instr] = ex
    return good_series, errors


def get_triggered_signals(series: Dict[str, instruments.OHLCSeries],
                          window_size: int, rel_eps: float) -> Dict[str, str]:
    res = {}
    for instr, ser in series.items():
        quote = moex.load_intraday_quotes(instr)
        if not quote.is_trading:
            logger.info(f"Skipping {instr} as it's not currently trading")
            continue
        avg_of_last_days = ser.avg_of_last_elems(window_size)
        rate = quote.last
        rel_diff = (rate - avg_of_last_days) / max(rate, avg_of_last_days)
        if rel_diff > rel_eps:
            res[instr] = f"Jump UP {round(rel_diff * 100.0, 2)}% to {rate} " \
                         f"from average of last {window_size} days {avg_of_last_days}"
        elif rel_diff < -rel_eps:
            res[instr] = f"Jump DOWN {round(rel_diff * 100.0, 2)}% to {rate} " \
                         f"from average of last {window_size} days {avg_of_last_days}"
        else:
            logger.info(f"{instr} intraday price {rate} did not jump {rel_eps * 100.0}% over last "
                        f"{window_size} days average of {avg_of_last_days}")

    return res


def send_mail(email_address: str, msg_header: str, msg_text: str) -> None:
    msg = MIMEText(msg_text)
    msg['Subject'] = msg_header
    msg['From'] = "jump-notifier"
    # msg['From'] = email_address
    msg['To'] = email_address
    mail_server = smtplib.SMTP('localhost')

    # {
    # mail_server = smtplib.SMTP('smtp.mail.ru', 587)
    # mail_server.ehlo()
    # mail_server.starttls()
    # mail_server.ehlo()
    # login = ""
    # password = ""
    # mail_server.login(login, password)
    # }

    mail_server.sendmail(msg['From'], [email_address], msg.as_string())
    mail_server.quit()


def get_mail_text(triggered_signals: Dict[str, str], errors: Dict[str, Exception]) -> (str, str):
    header = "WARN: Jumps found for " + ", ".join(triggered_signals.keys())
    msg = ""
    for instr, sig in triggered_signals.items():
        msg += f"{instr}: {sig}\n"
    if len(errors) != 0:
        msg += "\n"
        for instr, err in errors.items():
            msg += f"{instr}: {err}\n"
    return header, msg


@dataclass
class Ctx:
    cur_series: Dict[str, instruments.OHLCSeries]
    email: str
    window_size: int
    rel_eps: float
    scheduler: sched.scheduler
    ticks_freq: int
    saving_freq: datetime.timedelta
    time_last_save: Optional[datetime.datetime]
    time_last_email_sent: Optional[datetime.datetime]
    codes_last_sent: Optional[Set[str]]


def tick(ctx: Ctx):
    now = datetime.datetime.now()
    logger.info("Start tick")
    try:
        good_series, errors = refresh_series(ctx.cur_series)
        triggered_signals = get_triggered_signals(good_series, ctx.window_size, ctx.rel_eps)
        # send not more than 1 warning per day (except case when more series get triggered through the day)
        not_duplicate = ctx.time_last_email_sent is None or now.date() != ctx.time_last_email_sent.date() \
            or ctx.codes_last_sent is None or ctx.codes_last_sent != triggered_signals.keys()

        if (len(triggered_signals) != 0 or len(errors) != 0) and not_duplicate:
            (header, msg) = get_mail_text(triggered_signals, errors)
            logger.info(header)
            logger.info(msg)
            send_mail(ctx.email, header, msg)
            ctx.time_last_email_sent = now
            ctx.codes_last_sent = triggered_signals.keys()
        else:
            logger.info("Skip sending email as nothing to report or report was already sent today")

        if ctx.time_last_save is None or now - ctx.time_last_save > ctx.saving_freq:
            logger.info("Saving series")
            save_series(good_series)
            logger.info("Done saving")
            ctx.time_last_save = now
    except Exception as ex:
        logger.error("Error happened on tick", exc_info=ex, stack_info=True)
    finally:
        ctx.scheduler.enter(ctx.ticks_freq, 1, tick, argument=(ctx,))
        logger.info("End tick")


def save_series(series: Dict[str, instruments.OHLCSeries]):
    for instr, ser in series.items():
        try:
            fname = code_to_filename(instr)
            ser.save_to_csv(fname)
        except Exception as ex:
            logger.error(f"Failed to save series for {instr}", exc_info=ex, stack_info=True)


def main():
    parser = argparse.ArgumentParser(
        description="Sends mail if intraday quotes for specified instruments deviate "
                    "significantly from previous days average",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--email", default="root", help="E-mail address to which send notifications")
    parser.add_argument("--window", type=int, default=5, help="Number of business days to calculate average")
    parser.add_argument("--ticks-freq", type=int, default=60,
                        help="Check intraday rates with this frequency, in seconds")
    parser.add_argument("--saving-freq", type=int, default=24,
                        help="Save collected EOD rates to disk with this frequency, in hours")
    parser.add_argument("--rel-eps", type=float, default=0.01,
                        help="Relative diff threshold between rate of last days (number is set by window size) "
                             "and today's intraday rate to send warning email")
    parser.add_argument("codes",
                        help="Codes of instruments on MOEX (e.g. EUR_RUB__TOM USD000UTSTOM). "
                             "To get it, check "
                             "https://iss.moex.com/iss/history/engines/currency/markets/selt/boards/cets/securities.csv"
                             " - you need SECID column", nargs="+", metavar="CODE")

    args = parser.parse_args()
    email = args.email
    codes = args.codes
    window_size = args.window
    rel_eps = args.rel_eps
    ticks_freq = args.ticks_freq
    saving_freq = datetime.timedelta(hours=args.saving_freq)
    logger.info(f"PID {os.getpid()}")

    s = sched.scheduler()
    initial_series = get_initial_series(codes)
    ctx = Ctx(initial_series, email, window_size, rel_eps, s, ticks_freq, saving_freq, None, None, None)
    s.enter(delay=0, priority=1, action=tick, argument=(ctx,))

    def on_sigterm(sig, stack):
        logger.info(f"Received SIGTERM ({sig}), shutting down\n{stack}")
        # TODO: save series? but should not wait for next tick which can be too far away
        exit(1)

    signal.signal(signal.SIGTERM, on_sigterm)

    s.run()


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


if __name__ == "__main__":
    sys.excepthook = handle_exception
    main()
