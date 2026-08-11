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
- POST /assistant                -> free-text Q&A, optionally grounded in one ticker
- POST /auth/google              -> verify a Google ID token, issue our own session token
- GET/POST/DELETE /favourites     -> saved tickers, per logged-in user (requires Authorization: Bearer <token>)
- POST /insight/{ticker}         -> AI summary of recent revenue/profit trends
- POST /analysis/{ticker}        -> AI summary of business model/revenue streams/risks
- POST /weekly-update/{ticker}   -> AI summary of recent news headlines and likely impact

Auth: requires GOOGLE_CLIENT_ID (from Google Cloud Console) and JWT_SECRET
(any random string) set in .env.

Database: requires DATABASE_URL (a Postgres connection string, e.g. from
Neon) set in .env. Used for users/favourites.

Caveat: scraping ETFDB for every ETF at startup can take a while (there are
thousands of ETFs, one scrape request each). ETF_SCRAPE_LIMIT below caps it
for local development; remove/raise it for a full run.
"""

import os
from datetime import datetime, timedelta, timezone
from io import StringIO
import jwt
import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
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

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7

if not JWT_SECRET:
    JWT_SECRET = "dev-secret-change-me"
    print("WARNING: JWT_SECRET not set in .env — using an insecure dev default. Set a real random value before deploying.")

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

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            google_sub TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            name TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS favourites (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            ticker TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            name TEXT,
            added_at TEXT NOT NULL,
            UNIQUE(user_id, ticker)
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


init_db()


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


@app.on_event("startup")
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


class GoogleAuthRequest(BaseModel):
    credential: str  # the ID token handed to the frontend by Google's Sign-In button


def issue_session_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_or_create_user(google_sub: str, email: str, name: str | None) -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE google_sub = %s", (google_sub,))
    user = cur.fetchone()
    if user is None:
        cur.execute(
            "INSERT INTO users (google_sub, email, name, created_at) VALUES (%s, %s, %s, %s)",
            (google_sub, email, name, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        cur.execute("SELECT * FROM users WHERE google_sub = %s", (google_sub,))
        user = cur.fetchone()
    cur.close()
    conn.close()
    return user


@app.post("/auth/google")
async def auth_google(payload: GoogleAuthRequest):
    """Verify a Google ID token, then issue our own session token for the matching user."""
    try:
        claims = google_id_token.verify_oauth2_token(
            payload.credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    user = get_or_create_user(claims["sub"], claims["email"], claims.get("name"))
    token = issue_session_token(user["id"])
    return {"token": token, "user": {"email": user["email"], "name": user["name"]}}


def get_current_user(authorization: str = Header(None)) -> dict:
    """FastAPI dependency: extracts and validates the session token, returns the user row."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (payload["user_id"],))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class FavouriteRequest(BaseModel):
    ticker: str
    asset_type: str  # "etf" or "stock"
    name: str | None = None


@app.get("/favourites")
async def get_favourites(current_user: dict = Depends(get_current_user)):
    """Return the logged-in user's saved favourites, most recently added first."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM favourites WHERE user_id = %s ORDER BY added_at DESC",
        (current_user["id"],),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/favourites")
async def add_favourite(payload: FavouriteRequest, current_user: dict = Depends(get_current_user)):
    """Add (or update) a ticker in the logged-in user's favourites."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO favourites (user_id, ticker, asset_type, name, added_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, ticker)
        DO UPDATE SET asset_type = EXCLUDED.asset_type, name = EXCLUDED.name, added_at = EXCLUDED.added_at
        """,
        (current_user["id"], payload.ticker.upper(), payload.asset_type, payload.name, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "added"}


@app.delete("/favourites/{ticker}")
async def remove_favourite(ticker: str, current_user: dict = Depends(get_current_user)):
    """Remove a ticker from the logged-in user's favourites."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM favourites WHERE ticker = %s AND user_id = %s",
        (ticker.upper(), current_user["id"]),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "removed"}


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


NOT_ADVICE_RULE = (
    "You are not a licensed financial advisor: never tell the user what to buy, sell, "
    "or how to allocate their money."
)

ASSISTANT_SYSTEM_PROMPT = (
    "You are a financial education assistant embedded in a stock/ETF tracking app. "
    "Explain financial terms and describe stocks/ETFs in plain, accessible language. "
    f"{NOT_ADVICE_RULE} Stick to explaining concepts and describing the data given to you."
)

INSIGHT_SYSTEM_PROMPT = (
    "You are a financial education assistant. Given a company's recent quarterly "
    "financial statement data, explain in simple, plain-English terms: revenue "
    f"growth trends, profit trends, and any notable concerns. {NOT_ADVICE_RULE}"
)

ANALYSIS_SYSTEM_PROMPT = (
    "You are a financial education assistant. Given a company's business summary, "
    "explain in simple, plain-English terms: its business model, main revenue "
    f"streams, key growth drivers, and major risks. {NOT_ADVICE_RULE}"
)

WEEKLY_UPDATE_SYSTEM_PROMPT = (
    "You are a financial education assistant. Given a list of recent news headlines "
    "about a company, summarize what's been happening, why the stock may have moved, "
    "and the likely short-term vs long-term impact on the business. Only use "
    f"information from the headlines given; do not invent events. {NOT_ADVICE_RULE}"
)


def call_ai(system_prompt: str, user_prompt: str) -> str:
    response = openai_client.chat.completions.create(
        model=AI_MODEL,
        max_tokens=600,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def format_quarterly_financials(tk) -> str:
    fin = tk.quarterly_financials
    if fin is None or fin.empty:
        return "No financial statement data available."

    lines = []
    for row_name in ("Total Revenue", "Gross Profit", "Operating Income", "Net Income"):
        if row_name in fin.index:
            values = fin.loc[row_name].dropna()
            formatted = ", ".join(f"{col.strftime('%Y-%m-%d')}: {val:,.0f}" for col, val in values.items())
            if formatted:
                lines.append(f"{row_name}: {formatted}")

    return "\n".join(lines) if lines else "No matching financial line items available."


def extract_headline(item: dict) -> str | None:
    if not isinstance(item, dict):
        return None
    if item.get("title"):
        return item["title"]
    content = item.get("content")
    if isinstance(content, dict):
        return content.get("title")
    return None


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
        return {"answer": call_ai(ASSISTANT_SYSTEM_PROMPT, user_prompt)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/insight/{ticker}")
async def get_financial_insight(ticker: str):
    """AI summary of a ticker's recent revenue/profit trends and concerns."""
    try:
        tk = yf.Ticker(ticker.upper())
        financials_text = format_quarterly_financials(tk)
        user_prompt = f"Ticker: {ticker.upper()}\nRecent quarterly financials:\n{financials_text}"
        return {"ticker": ticker.upper(), "insight": call_ai(INSIGHT_SYSTEM_PROMPT, user_prompt)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analysis/{ticker}")
async def get_company_analysis(ticker: str):
    """AI analysis of a ticker's business model, revenue streams, growth drivers, and risks."""
    try:
        tk = yf.Ticker(ticker.upper())
        summary = tk.info.get("longBusinessSummary")
        if not summary:
            raise HTTPException(status_code=404, detail=f"No business summary available for {ticker}")
        user_prompt = f"Ticker: {ticker.upper()}\nBusiness summary:\n{summary}"
        return {"ticker": ticker.upper(), "analysis": call_ai(ANALYSIS_SYSTEM_PROMPT, user_prompt)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/weekly-update/{ticker}")
async def get_weekly_update(ticker: str):
    """AI summary of a ticker's recent news headlines: what happened and likely impact."""
    try:
        tk = yf.Ticker(ticker.upper())
        news_items = tk.news or []
        headlines = [h for item in news_items[:8] if (h := extract_headline(item))]
        if not headlines:
            raise HTTPException(status_code=404, detail=f"No recent news found for {ticker}")
        user_prompt = f"Ticker: {ticker.upper()}\nRecent headlines:\n" + "\n".join(f"- {h}" for h in headlines)
        return {"ticker": ticker.upper(), "update": call_ai(WEEKLY_UPDATE_SYSTEM_PROMPT, user_prompt)}
    except HTTPException:
        raise
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
