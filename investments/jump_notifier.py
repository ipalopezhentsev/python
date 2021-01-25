import os
import sys
import signal
import argparse
import smtplib
from email.mime.text import MIMEText
import sched
from typing import List, Dict, Optional, Set

from investments import moex, instruments
import logging
import datetime
import investments.logsetup

logger = logging.getLogger(__name__)


def instrument_to_filename(instr: moex.Instrument):
    return f"data/{instr.code}.csv"


def get_initial_series(instrums: List[moex.Instrument]) -> Dict[moex.Instrument, instruments.OHLCSeries]:
    res = {}
    for instrument in instrums:
        try:
            fname = instrument_to_filename(instrument)
            if os.path.exists(fname):
                series = instruments.OHLCSeries.load_from_csv(fname)
            else:
                series = instruments.OHLCSeries(instrument.code, [], name=None)
        except Exception as e:
            logger.error(f"Error loading initial data for {instrument}", exc_info=e, stack_info=True)
            # give it chance to load from http
            series = instruments.OHLCSeries(instrument.code, [], name=None)
        res[instrument] = series
    return res


def refresh_series(cur_series: Dict[moex.Instrument, instruments.OHLCSeries]) \
        -> (Dict[moex.Instrument, instruments.OHLCSeries], Dict[moex.Instrument, Exception]):
    """gets new entries into series from web. Returns dict of instrument to loading error"""
    good_series = {}
    errors = {}
    for instr, series in cur_series.items():
        try:
            instr.update_ohlc_table(series)
            good_series[instr] = series
        except Exception as ex:
            errors[instr] = ex
    return good_series, errors


def get_triggered_signals(series: Dict[moex.Instrument, instruments.OHLCSeries],
                          window_size: int, num_std_devs_thresh: float) \
        -> (Dict[moex.Instrument, str], Dict[moex.Instrument, str]):
    """returns tuple whose first element is triggered instruments and second is all others, with clarifying message"""
    # TODO: for bonds: add notification its price gets < 100.
    triggered = {}
    not_triggered = {}
    for instr, ser in series.items():
        try:
            quote = instr.load_intraday_quotes()
            if not quote.is_trading:
                logger.info(f"Skipping {instr} as it's not currently trading")
                continue
            mean = ser.mean_of_last_elems(window_size)
            std_dev = ser.std_dev_of_last_elems(window_size, mean=mean)
            rate = quote.last
            rel_diff = (rate - mean) / max(rate, mean)
            nstd_devs = num_std_devs_thresh * std_dev
            observed_num_std_devs_jump = abs(rate-mean)/std_dev
            if rate > mean + nstd_devs:
                triggered[instr] = f"Jump UP {round(rel_diff * 100.0, 2)}% to {rate} " \
                                   f"from average of {round(mean, 2)} of last {window_size} days " \
                                   f"(jump of {round(observed_num_std_devs_jump, 2)} std. devs from mean)"
                logger.warning(f"{instr} triggered")
            elif rate < mean - nstd_devs:
                triggered[instr] = f"Jump DOWN {round(rel_diff * 100.0, 2)}% to {rate} " \
                                   f"from average of {round(mean, 2)} of last {window_size} days " \
                                   f"(jump of {round(observed_num_std_devs_jump, 2)} std. devs from mean)"
                logger.warning(f"{instr} triggered")
            else:
                not_triggered[instr] = f"{rate} is {round(rel_diff * 100.0, 2)}% jump over last " \
                                       f"{window_size} days average of {round(mean, 2)} " \
                                       f"(jump of {round(observed_num_std_devs_jump, 2)} std. devs from mean)"
        except Exception as ex:
            logger.error(f"Error happened getting intraday rates for {instr}", exc_info=ex, stack_info=True)
            triggered[instr] = f"Could not get intraday rates: {ex}"
    return triggered, not_triggered


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


def get_mail_text(triggered_signals: Dict[moex.Instrument, str],
                  not_triggered_instruments: Dict[moex.Instrument, str],
                  errors: Dict[moex.Instrument, Exception]) -> (str, str):
    header = "WARN: Jumps found for " + ", ".join(map(lambda i: i.code, triggered_signals.keys()))
    msg = "Triggered instruments:\n"
    for instr, sig in triggered_signals.items():
        msg += f"{instr}: {sig}\n"
    if len(not_triggered_instruments) != 0:
        msg += "\n\nNot triggered instruments:\n"
        for instr, txt in not_triggered_instruments.items():
            msg += f"{instr}: {txt}\n"
    if len(errors) != 0:
        msg += "\n\nErrors:\n\n"
        for instr, err in errors.items():
            msg += f"{instr}: {err}\n\n"
    return header, msg


class Ticker:
    def __init__(self, initial_series: Dict[moex.Instrument, instruments.OHLCSeries],
                 email: str, window_size: int, num_std_devs_thresh: float, scheduler: sched.scheduler,
                 ticks_freq: int, saving_freq: datetime.timedelta):
        self.cur_series = initial_series
        self.email = email
        self.window_size = window_size
        self.num_std_devs_thresh = num_std_devs_thresh
        self.scheduler = scheduler
        self.ticks_freq = ticks_freq
        self.saving_freq = saving_freq
        self.time_last_save: Optional[datetime.datetime] = None
        self.time_last_email_sent: Optional[datetime.datetime] = None
        self.codes_sent_today: Set[moex.Instrument] = set()

    def tick(self, /, *args, **kwargs):
        now = datetime.datetime.now()
        logger.info("Start tick")
        try:
            good_series, errors = refresh_series(self.cur_series)
            triggered, not_triggered = get_triggered_signals(good_series, self.window_size, self.num_std_devs_thresh)
            # send not more than 1 warning per day (except case when more series get triggered through the day)
            day_changed_since_last_notification = self.time_last_email_sent is None or \
                                                  self.time_last_email_sent.date() != now.date()
            if day_changed_since_last_notification:
                self.codes_sent_today.clear()
            triggered_instruments_already_reported_today = len(self.codes_sent_today) != 0 and \
                                                           triggered.keys() <= self.codes_sent_today
            duplicate = not day_changed_since_last_notification and triggered_instruments_already_reported_today

            if (len(triggered) != 0 or len(errors) != 0) and not duplicate:
                (header, msg) = get_mail_text(triggered, not_triggered, errors)
                logger.info(header)
                logger.info(msg)
                send_mail(self.email, header, msg)
                self.time_last_email_sent = now
                self.codes_sent_today |= triggered.keys()
            else:
                logger.info("Skip sending email as nothing to report or already sent today. Current values:")
                for instr, text in not_triggered.items():
                    logger.info(f"{instr}: {text}")

            if self.time_last_save is None or now - self.time_last_save > self.saving_freq:
                logger.info("Saving series")
                self.save_series(good_series)
                logger.info("Done saving")
                self.time_last_save = now
        except Exception as ex:
            logger.error("Error happened on tick", exc_info=ex, stack_info=True)
        finally:
            self.scheduler.enter(self.ticks_freq, 1, self.tick, argument=(self,))
            logger.info("End tick")

    @staticmethod
    def save_series(series: Dict[moex.Instrument, instruments.OHLCSeries]):
        for instr, ser in series.items():
            try:
                fname = instrument_to_filename(instr)
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
    parser.add_argument("--ticks-freq-seconds", type=int, default=60,
                        help="Check intraday rates with this frequency, in seconds")
    parser.add_argument("--saving-freq-hours", type=int, default=24,
                        help="Save collected EOD rates to disk with this frequency, in hours")
    parser.add_argument("--num-std-devs-thresh", type=float, default=2.0,
                        help="Minimum number of standard deviations intraday rate should jump from the mean to "
                             "send warning email")
    parser.add_argument("--fx-codes",
                        help="Security ID's of FX instruments on MOEX (e.g. EUR_RUB__TOM USD000UTSTOM). "
                             "To get it, check "
                             "https://iss.moex.com/iss/history/engines/currency/markets/selt/boards/cets/securities.csv"
                             " - you need SECID column", nargs="+", metavar="FX_CODE")
    parser.add_argument("--bond-codes",
                        help="ISIN's of bond instruments on MOEX (e.g. RU000A100YG1). ",
                        nargs="+", metavar="BOND_CODE")
    parser.add_argument("--share-codes",
                        help="Security ID's (not ISIN's!) of share instruments on MOEX (e.g. SBMX). ",
                        nargs="+", metavar="SHARE_CODE")
    parser.add_argument("--index-codes",
                        help="Security ID's of indexes on MOEX (e.g. MREDC).",
                        nargs="+", metavar="INDEX_CODE")

    args = parser.parse_args()
    email = args.email
    fx_codes = args.fx_codes
    bond_codes = args.bond_codes
    share_codes = args.share_codes
    index_codes = args.index_codes
    if fx_codes is None and bond_codes is None and share_codes is None and index_codes is None:
        raise ValueError("At least one of --fx-codes, --bond-codes, --share-codes, --index-codes must be specified")
    instrums: List[moex.Instrument] = []
    if fx_codes is not None:
        instrums.extend([moex.FXInstrument(secid) for secid in fx_codes])
    if bond_codes is not None:
        instrums.extend([moex.BondInstrument(isin) for isin in bond_codes])
    if share_codes is not None:
        instrums.extend([moex.ShareInstrument(secid) for secid in share_codes])
    if index_codes is not None:
        instrums.extend([moex.IndexInstrument(secid) for secid in index_codes])
    window_size = args.window
    num_std_devs_thresh = args.num_std_devs_thresh
    ticks_freq = args.ticks_freq_seconds
    saving_freq = datetime.timedelta(hours=args.saving_freq_hours)
    logger.info(f"PID {os.getpid()}")

    s = sched.scheduler()
    initial_series = get_initial_series(instrums)
    ticker = Ticker(initial_series, email, window_size, num_std_devs_thresh, s, ticks_freq, saving_freq)
    s.enter(delay=0, priority=1, action=ticker.tick, argument=(ticker,))

    def on_sigterm(sig, stack):
        logger.info(f"Received SIGTERM ({sig}), shutting down\n{stack}")
        # TODO: save series? but should not wait for next tick which can be too far away
        exit(0)

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
