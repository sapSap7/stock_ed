"""
populate_etfs.py

One-off script to populate the `etfs` table in Postgres with ETF metadata
from yfinance (category, name, expense ratio, AUM). The app itself only
reads from this table at request time — it never scrapes on startup.
Re-run this manually whenever you want to refresh the data (e.g. for
updated AUM) or grow the ticker coverage.

Run this from your own machine, not from a cloud host: etfdb.com blocks
datacenter IPs with a Cloudflare challenge, and firing many rapid
yfinance requests from a shared cloud IP risks tripping its rate limiter.
The ticker list itself comes from pyetfdb_scraper's bundled local list
(no network call, so no risk there).

Usage:
    python populate_etfs.py [limit]
    (limit defaults to 300; there are thousands of ETFs total)
"""

import os
import sys
import time
from datetime import datetime, timezone

import psycopg2
import yfinance as yf
from dotenv import load_dotenv
from pyetfdb_scraper.etf import load_etfs

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DELAY_SECONDS = 0.5


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    tickers = load_etfs()[:limit]
    print(f"Fetching data for {len(tickers)} ETFs from yfinance (~{limit * DELAY_SECONDS / 60:.1f} min)...")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS etfs (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            category TEXT NOT NULL,
            expense_ratio TEXT,
            aum TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()

    saved = 0
    for i, ticker in enumerate(tickers, start=1):
        try:
            info = yf.Ticker(ticker).info
            category = info.get("category")
            if not category:
                print(f"[{i}/{len(tickers)}] {ticker}: skipped (no category)")
                continue
            cur.execute(
                """
                INSERT INTO etfs (ticker, name, category, expense_ratio, aum, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker)
                DO UPDATE SET name = EXCLUDED.name, category = EXCLUDED.category,
                              expense_ratio = EXCLUDED.expense_ratio, aum = EXCLUDED.aum,
                              updated_at = EXCLUDED.updated_at
                """,
                (
                    ticker,
                    info.get("longName") or info.get("shortName") or "",
                    category,
                    info.get("netExpenseRatio") or info.get("annualReportExpenseRatio") or "",
                    info.get("totalAssets") or "",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            saved += 1
            print(f"[{i}/{len(tickers)}] {ticker}: {category}")
        except Exception as e:
            print(f"[{i}/{len(tickers)}] {ticker}: skipped ({e})")
        time.sleep(DELAY_SECONDS)

    cur.close()
    conn.close()
    print(f"Done. Saved {saved} ETFs.")


if __name__ == "__main__":
    main()
