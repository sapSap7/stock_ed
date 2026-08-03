"""
Unit tests for main.py's API endpoints. External calls (yfinance, ETFDB
scraping, the OpenAI/Groq client) are mocked out so tests run fast, offline,
and without spending API credits.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def sample_caches():
    """Populate the in-memory caches directly, bypassing the real startup scrape."""
    main.ETF_CACHE.clear()
    main.ETF_CACHE.extend([
        {"ticker": "VNQ", "name": "Vanguard Real Estate ETF", "category": "Real Estate", "expense_ratio": "0.13%", "aum": "$39,503.2 M"},
        {"ticker": "QQQ", "name": "Invesco QQQ Trust", "category": "Large Cap Growth Equities", "expense_ratio": "0.20%", "aum": "$300,000 M"},
    ])
    main.STOCK_CACHE.clear()
    main.STOCK_CACHE.extend([
        {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Information Technology", "sub_industry": "Technology Hardware"},
        {"ticker": "JPM", "name": "JPMorgan Chase", "sector": "Financials", "sub_industry": "Diversified Banks"},
    ])
    yield
    main.ETF_CACHE.clear()
    main.STOCK_CACHE.clear()


def test_get_etfs_returns_all(client):
    response = client.get("/etfs")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_etfs_filters_by_category_case_insensitive(client):
    response = client.get("/etfs", params={"category": "real estate"})
    assert response.status_code == 200
    tickers = [e["ticker"] for e in response.json()]
    assert tickers == ["VNQ"]


def test_get_stocks_filters_by_sector(client):
    response = client.get("/stocks", params={"sector": "Financials"})
    assert response.status_code == 200
    tickers = [s["ticker"] for s in response.json()]
    assert tickers == ["JPM"]


def test_get_categories(client):
    response = client.get("/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["etf_categories"] == ["Large Cap Growth Equities", "Real Estate"]
    assert data["stock_sectors"] == ["Financials", "Information Technology"]


def test_price_history(client):
    fake_history = pd.DataFrame(
        {"Open": [100.0], "Close": [101.0]},
        index=pd.to_datetime(["2024-01-02"]),
    )
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = fake_history

    with patch("main.yf.Ticker", return_value=mock_ticker):
        response = client.get("/price/VNQ")

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "VNQ"
    assert len(body["history"]) == 1


def test_price_history_not_found(client):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()

    with patch("main.yf.Ticker", return_value=mock_ticker):
        response = client.get("/price/UNKNOWN")

    assert response.status_code == 404


def test_ticker_info(client):
    mock_ticker = MagicMock()
    mock_ticker.info = {"previousClose": 101.5, "longName": "Vanguard Real Estate ETF"}

    with patch("main.yf.Ticker", return_value=mock_ticker):
        response = client.get("/info/VNQ")

    assert response.status_code == 200
    assert response.json()["info"]["longName"] == "Vanguard Real Estate ETF"


def test_ticker_info_not_found(client):
    mock_ticker = MagicMock()
    mock_ticker.info = {}

    with patch("main.yf.Ticker", return_value=mock_ticker):
        response = client.get("/info/UNKNOWN")

    assert response.status_code == 404


def test_assistant_answers_question(client):
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="An expense ratio is a fee..."))]

    with patch("main.openai_client.chat.completions.create", return_value=fake_response) as mock_create:
        response = client.post("/assistant", json={"question": "What is an expense ratio?"})

    assert response.status_code == 200
    assert "expense ratio" in response.json()["answer"].lower()
    mock_create.assert_called_once()


def test_assistant_includes_ticker_context(client):
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="VNQ is a REIT ETF."))]

    mock_ticker = MagicMock()
    mock_ticker.info = {"longName": "Vanguard Real Estate ETF", "sector": "Real Estate"}

    with patch("main.yf.Ticker", return_value=mock_ticker), \
         patch("main.openai_client.chat.completions.create", return_value=fake_response) as mock_create:
        response = client.post("/assistant", json={"question": "Explain this ETF", "ticker": "vnq"})

    assert response.status_code == 200
    sent_messages = mock_create.call_args.kwargs["messages"]
    user_message = sent_messages[1]["content"]
    assert "VNQ" in user_message
    assert "Vanguard Real Estate ETF" in user_message


def test_assistant_handles_ticker_lookup_failure_gracefully(client):
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="Some answer."))]

    with patch("main.yf.Ticker", side_effect=Exception("network error")), \
         patch("main.openai_client.chat.completions.create", return_value=fake_response):
        response = client.post("/assistant", json={"question": "Explain this", "ticker": "BADTICKER"})

    assert response.status_code == 200


def test_assistant_upstream_error_returns_500(client):
    with patch("main.openai_client.chat.completions.create", side_effect=Exception("API error")):
        response = client.post("/assistant", json={"question": "Hello"})

    assert response.status_code == 500
