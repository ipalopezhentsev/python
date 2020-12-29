import argparse
import investments.moex


def main():
    parser = argparse.ArgumentParser(
        description="Downloads EOD OLHC data from Moscow Exchange (MOEX) "
                    "and saves to CSV files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("codes", help="Codes of instruments on MOEX (e.g. EUR_RUB__TOM USD000UTSTOM)."
                                      "To get it, check "
                                      "https://iss.moex.com/iss/history/engines/currency/markets/selt/boards/cets/securities.csv"
                                      " - you need SECID column", nargs="+", metavar="CODE")
    args = parser.parse_args()
    for code in args.codes:
        olhc_series = investments.moex.load_olhc_table(code, from_date=None)
        olhc_series.save_to_csv(code + ".csv")


if __name__ == "__main__":
    main()
