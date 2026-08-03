import yfinance as yf

# Example: VNQ = Vanguard Real Estate ETF (a REIT ETF)
symbol = "VNQ"

# Download 5 most recent days of price data
etf = yf.Ticker(symbol)
history = etf.history(period="5d")

print(f"=== {symbol} Info ===")
print(etf.info)  # Company details
print("\n=== Price History (last 5 days) ===")
print(history)
