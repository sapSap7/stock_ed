https://stock-ed-tracker.vercel.app/
API: https://stock-etf-tracker-api.onrender.com

A Stock & ETF Tracker 
  A full-stack app for browsing stocks and ETFs by category/sector, 
  charting price history, saving favourites, 
  and asking an AI assistant to explain financial data in plain English.

**Features**
- **Browse & filter** - S&P 500 stocks (by GICS sector) and ETFs (by category), with search
- **Dark/light theme** toggle
- **Google sign-in**
- **Price charts** - 1 year price history view per ticker
- **Favourites** - save tickers to your account (Google Sign-In), synced across devices
- **AI assistant** ask free-text questions about any stck, ETF, or financial term 
- **AI insights** (for favourited tickers):
  - **Financial Insight** — plain-English summary of recent revenue/profit trends
  - **Weekly Update** — summary of recent news headlines and likely impact
  - **Company Analysis** — business model, revenue streams, growth drivers, risks
- All AI features are explicitly educational, the assistant never gives buy/sell/hold advice

**Tech Stack**
## Backend
- FastAPI (Python) + Uvicorn
- PostgreSQL hosted on Neon via `psycopg2` for users/favourites/ETF data
- yfinance provides live price/info data
- Groq powers the AI assistant/insights
- Google OAuth + JWT sessions for auth
- pytest for test suite that mocks all external calls (yfinance, AI client)

## Frontend
- React + Vite
- Tailwind CSS
- Recharts for price charts
- lucide-react for icons

## Infrastructure/CI/CD
- Backend deployed on Render
- Frontend deployed on Vercel
- Database on Neon (serverless Postgres)
- GitHub Actions - runs the test suite on every push/PR

## Architecture notes
- **ETF data uses a "populate once, serve from DB" pattern, not scrape-on-boot.** Fetching ETF metadata from `etfdb.com` gets blocked by Cloudflare on cloud hosting IPs,
  and hammering `yfinance` for hundreds of tickers on every app restart risks tripping its rate limiter. Instead, `populate_etfs.py` is a standalone script
  (run manually, from a non-cloud IP) that populates a Postgres `etfs` table once; the app just reads from that table. Live per-ticker price/info lookups (`/price`, `/info`)
  are unaffected - those still fetch fresh data on every request.
- **Auth**: Google Identity Services hands the frontend a signed ID token; the backend verifies it against Google, creates/looks up a user by their Google account ID,
  and issues its own short-lived JWT for subsequent requests. No passwords are ever stored.
- **Startup**: the stock list (from Wikipedia's S&P 500 table) populates in a background thread on boot, so the app can accept requests immediately rather than blocking on that scrape.

## Local setup

**Backend**
```bash
python -m venv venv
venv\Scripts\Activate.ps1       # Windows PowerShell
pip install -r requirements.txt
python populate_etfs.py         # one-off: populate the etfs table
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Required in .env:
DATABASE_URL=            # Postgres connection string (e.g. from Neon)
GROQ_API_KEY=
GOOGLE_CLIENT_ID=        # from Google Cloud Console
JWT_SECRET=              # any long random string

**Frontend**
cd stock-ed
npm install
npm run dev
Required in .env:
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=

**Tests**
pytest tests/ -v
--> Runs against a real Postgres database (DATABASE_URL); all external calls (yfinance, ETFDB, the AI client) are mocked, so tests are fast and don't consume API credits.
