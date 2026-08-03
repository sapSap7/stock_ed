"""
main.py

Consolidated FastAPI backend for the stock & ETF tracker.

Data sources:
- pyetfdb_scraper: full ETF list + per-ETF metadata, used to build category groupings
- Wikipedia's S&P 500 table (via pandas.read_html): stock list with each company's
  GICS sector/sub-industry already labeled, no per-ticker lookup needed
- yfinance: live price history + detailed per-ticker info, for both stocks and ETFs

How to run:
1. Activate the venv, then: pip install -r requirements.txt
2. uvicorn main:app --reload --host 0.0.0.0 --port 8000
3. Interactive docs at http://localhost:8000/docs

Endpoints:
- GET /etfs?category=...        -> list ETFs, optionally filtered by category
- GET /stocks?sector=...        -> list S&P 500 stocks, optionally filtered by sector
- GET /categories               -> available ETF categories + stock sectors (for a filter dropdown)
- GET /info/{ticker}            -> detailed info for one ticker (stock or ETF)
- GET /price/{ticker}?period=1y&interval=1d -> historical price data

Caveat: scraping ETFDB for every ETF at startup can take a while (there are
thousands of ETFs, one scrape request each). ETF_SCRAPE_LIMIT below caps it
for local development; remove/raise it for a full run.
"""

import os
from io import StringIO
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pyetfdb_scraper.etf import ETF, load_etfs
import yfinance as yf
import pandas as pd
import uvicorn
from openai import OpenAI

load_dotenv()
# Groq's API is OpenAI-compatible, so the same OpenAI SDK works here, just
# pointed at Groq's base_url with a Groq API key and model name.
openai_client = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
AI_MODEL = os.getenv("AI_MODEL", "llama-3.1-8b-instant")

WIKI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

app = FastAPI(title="Stock & ETF Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ETF_SCRAPE_LIMIT = int(os.getenv("ETF_SCRAPE_LIMIT", "200"))

# In-memory caches populated at startup
ETF_CACHE = []
STOCK_CACHE = []


def extract_etf_category(info: dict) -> str:
    """Best-effort extraction of a single category label from ETFDB's scraped info."""
    dbtheme = info.get("dbtheme", {}) or {}
    return dbtheme.get("category") or dbtheme.get("asset_class") or "Uncategorized"


async def load_etf_cache():
    print("Startup: loading ETF list from ETFDB (this may take a while)...")
    try:
        tickers = load_etfs()
    except Exception as e:
        print("Error loading ETF list:", e)
        return

    found = []
    for t in tickers[:ETF_SCRAPE_LIMIT]:
        try:
            etf = ETF(t)
            info = etf.info
            found.append({
                "ticker": t,
                "name": info.get("vitals", {}).get("etf_name", ""),
                "category": extract_etf_category(info),
                "expense_ratio": info.get("vitals", {}).get("expense_ratio", ""),
                "aum": info.get("trade_data", {}).get("aum", ""),
            })
        except Exception:
            # ETFDB scraping can fail for individual tickers; skip and keep going
            continue

    ETF_CACHE.clear()
    ETF_CACHE.extend(sorted(found, key=lambda x: x["ticker"]))
    print(f"Startup: loaded {len(ETF_CACHE)} ETFs.")


def load_stock_cache():
    print("Startup: loading S&P 500 stock list from Wikipedia...")
    try:
        response = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers=WIKI_HEADERS,
        )
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
        sp500 = tables[0]
    except Exception as e:
        print("Error loading S&P 500 list:", e)
        return

    found = [
        {
            "ticker": row["Symbol"],
            "name": row["Security"],
            "sector": row["GICS Sector"],
            "sub_industry": row["GICS Sub-Industry"],
        }
        for _, row in sp500.iterrows()
    ]

    STOCK_CACHE.clear()
    STOCK_CACHE.extend(sorted(found, key=lambda x: x["ticker"]))
    print(f"Startup: loaded {len(STOCK_CACHE)} stocks.")


@app.lifespan("startup")
async def on_startup():
    await load_etf_cache()
    load_stock_cache()


@app.get("/etfs")
async def get_etfs(category: str | None = None):
    """Return cached ETFs, optionally filtered by category (case-insensitive)."""
    if category:
        return [e for e in ETF_CACHE if e["category"].lower() == category.lower()]
    return ETF_CACHE


@app.get("/stocks")
async def get_stocks(sector: str | None = None):
    """Return cached S&P 500 stocks, optionally filtered by sector (case-insensitive)."""
    if sector:
        return [s for s in STOCK_CACHE if s["sector"].lower() == sector.lower()]
    return STOCK_CACHE


@app.get("/categories")
async def get_categories():
    """Return the distinct ETF categories and stock sectors available, for a filter dropdown."""
    etf_categories = sorted({e["category"] for e in ETF_CACHE if e["category"]})
    stock_sectors = sorted({s["sector"] for s in STOCK_CACHE if s["sector"]})
    return {"etf_categories": etf_categories, "stock_sectors": stock_sectors}


@app.get("/info/{ticker}")
async def get_ticker_info(ticker: str):
    """Return live info for one ticker (works for a stock or an ETF)."""
    try:
        tk = yf.Ticker(ticker.upper())
        info = tk.info
        if not info or (info.get("regularMarketPrice") is None and info.get("previousClose") is None):
            raise HTTPException(status_code=404, detail=f"No data found for ticker {ticker}")
        return {"ticker": ticker.upper(), "info": info}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


ASSISTANT_SYSTEM_PROMPT = (
    "You are a financial education assistant embedded in a stock/ETF tracking app. "
    "Explain financial terms and describe stocks/ETFs in plain, accessible language. "
    "You are not a licensed financial advisor: never tell the user what to buy, sell, "
    "or how to allocate their money. Stick to explaining concepts and describing the "
    "data given to you."
)


class AssistantRequest(BaseModel):
    question: str
    ticker: str | None = None


@app.post("/assistant")
async def ask_assistant(payload: AssistantRequest):
    """Answer a financial question, optionally grounded in one ticker's live data."""
    user_prompt = payload.question

    if payload.ticker:
        try:
            info = yf.Ticker(payload.ticker.upper()).info
            fields = ("longName", "sector", "industry", "previousClose", "marketCap", "trailingPE", "dividendYield")
            context_lines = [f"{f}: {info[f]}" for f in fields if info.get(f) is not None]
            if context_lines:
                user_prompt = f"Ticker: {payload.ticker.upper()}\n" + "\n".join(context_lines) + f"\n\nQuestion: {payload.question}"
        except Exception:
            pass  # fall back to the question alone if the ticker lookup fails

    try:
        response = openai_client.chat.completions.create(
            model=AI_MODEL,
            max_tokens=500,
            messages=[
                {"role": "system", "content": ASSISTANT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return {"answer": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/price/{ticker}")
async def get_price_history(ticker: str, period: str = "1y", interval: str = "1d"):
    """Return historical OHLC price data for `ticker` using yfinance.
    period examples: '1y', '6mo', '1mo', 'max'
    interval examples: '1d', '1wk', '1h' (minute data limited)
    """
    try:
        tk = yf.Ticker(ticker.upper())
        hist = tk.history(period=period, interval=interval)
        if hist.empty:
            raise HTTPException(status_code=404, detail="No price data found for ticker")
        records = hist.reset_index().to_dict(orient="records")
        return {"ticker": ticker.upper(), "history": records}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
