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


@pytest.fixture(autouse=True)
def clean_test_db():
    """Ensure tables exist, then clean up any test users afterward (their
    favourites cascade-delete with them). Tests run against the real Postgres
    DB from DATABASE_URL — every test google_sub below is prefixed 'test-' so
    this one DELETE clears everything a test could have created.
    """
    main.init_db()
    yield
    conn = main.get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE google_sub LIKE 'test-%'")
    conn.commit()
    cur.close()
    conn.close()


@pytest.fixture
def auth_headers(clean_test_db):
    """A valid Authorization header for a freshly created test user."""
    conn = main.get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (google_sub, email, name, created_at) VALUES (%s, %s, %s, %s)",
        ("test-google-sub", "test@example.com", "Test User", "2024-01-01T00:00:00+00:00"),
    )
    conn.commit()
    cur.execute("SELECT * FROM users WHERE google_sub = %s", ("test-google-sub",))
    user = cur.fetchone()
    cur.close()
    conn.close()

    token = main.issue_session_token(user["id"])
    return {"Authorization": f"Bearer {token}"}


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


def test_favourites_require_auth(client):
    assert client.get("/favourites").status_code == 401
    assert client.post("/favourites", json={"ticker": "VNQ", "asset_type": "etf"}).status_code == 401
    assert client.delete("/favourites/VNQ").status_code == 401


def test_favourites_reject_invalid_token(client):
    response = client.get("/favourites", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_add_and_get_favourites(client, auth_headers):
    response = client.post(
        "/favourites",
        json={"ticker": "vnq", "asset_type": "etf", "name": "Vanguard Real Estate ETF"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    response = client.get("/favourites", headers=auth_headers)
    assert response.status_code == 200
    favourites = response.json()
    assert len(favourites) == 1
    assert favourites[0]["ticker"] == "VNQ"
    assert favourites[0]["asset_type"] == "etf"


def test_remove_favourite(client, auth_headers):
    client.post("/favourites", json={"ticker": "AAPL", "asset_type": "stock"}, headers=auth_headers)
    response = client.delete("/favourites/aapl", headers=auth_headers)
    assert response.status_code == 200
    assert client.get("/favourites", headers=auth_headers).json() == []


def test_add_favourite_replaces_existing(client, auth_headers):
    client.post("/favourites", json={"ticker": "VNQ", "asset_type": "etf", "name": "Old Name"}, headers=auth_headers)
    client.post("/favourites", json={"ticker": "VNQ", "asset_type": "etf", "name": "New Name"}, headers=auth_headers)

    favourites = client.get("/favourites", headers=auth_headers).json()
    assert len(favourites) == 1
    assert favourites[0]["name"] == "New Name"


def test_favourites_are_scoped_per_user(client, auth_headers):
    client.post("/favourites", json={"ticker": "VNQ", "asset_type": "etf"}, headers=auth_headers)

    conn = main.get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (google_sub, email, name, created_at) VALUES (%s, %s, %s, %s)",
        ("test-other-user-sub", "other@example.com", "Other User", "2024-01-01T00:00:00+00:00"),
    )
    conn.commit()
    cur.execute("SELECT * FROM users WHERE google_sub = %s", ("test-other-user-sub",))
    other_user = cur.fetchone()
    cur.close()
    conn.close()
    other_headers = {"Authorization": f"Bearer {main.issue_session_token(other_user['id'])}"}

    assert client.get("/favourites", headers=other_headers).json() == []
    assert len(client.get("/favourites", headers=auth_headers).json()) == 1


def test_google_auth_creates_new_user(client):
    fake_claims = {"sub": "test-google-123", "email": "new@example.com", "name": "New User"}
    with patch("main.google_id_token.verify_oauth2_token", return_value=fake_claims):
        response = client.post("/auth/google", json={"credential": "fake-token"})

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert "token" in body


def test_google_auth_returns_same_user_on_repeat_login(client):
    fake_claims = {"sub": "test-google-123", "email": "repeat@example.com", "name": "Repeat User"}
    with patch("main.google_id_token.verify_oauth2_token", return_value=fake_claims):
        first = client.post("/auth/google", json={"credential": "fake-token"}).json()
        second = client.post("/auth/google", json={"credential": "fake-token"}).json()

    first_headers = {"Authorization": f"Bearer {first['token']}"}
    second_headers = {"Authorization": f"Bearer {second['token']}"}
    client.post("/favourites", json={"ticker": "VNQ", "asset_type": "etf"}, headers=first_headers)

    assert len(client.get("/favourites", headers=second_headers).json()) == 1


def test_google_auth_rejects_invalid_token(client):
    with patch("main.google_id_token.verify_oauth2_token", side_effect=ValueError("bad token")):
        response = client.post("/auth/google", json={"credential": "fake-token"})

    assert response.status_code == 401


def test_financial_insight(client):
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="Revenue is growing."))]

    fake_financials = pd.DataFrame(
        {pd.Timestamp("2024-06-30"): [1000.0], pd.Timestamp("2024-03-31"): [900.0]},
        index=["Total Revenue"],
    )
    mock_ticker = MagicMock()
    mock_ticker.quarterly_financials = fake_financials

    with patch("main.yf.Ticker", return_value=mock_ticker), \
         patch("main.openai_client.chat.completions.create", return_value=fake_response) as mock_create:
        response = client.post("/insight/VNQ")

    assert response.status_code == 200
    assert response.json()["insight"] == "Revenue is growing."
    sent_prompt = mock_create.call_args.kwargs["messages"][1]["content"]
    assert "Total Revenue" in sent_prompt


def test_company_analysis(client):
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="This company sells real estate ETFs."))]

    mock_ticker = MagicMock()
    mock_ticker.info = {"longBusinessSummary": "Vanguard Real Estate ETF tracks US real estate."}

    with patch("main.yf.Ticker", return_value=mock_ticker), \
         patch("main.openai_client.chat.completions.create", return_value=fake_response):
        response = client.post("/analysis/VNQ")

    assert response.status_code == 200
    assert "real estate" in response.json()["analysis"].lower()


def test_company_analysis_no_summary_returns_404(client):
    mock_ticker = MagicMock()
    mock_ticker.info = {}

    with patch("main.yf.Ticker", return_value=mock_ticker):
        response = client.post("/analysis/UNKNOWN")

    assert response.status_code == 404


def test_weekly_update(client):
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="Stock moved due to earnings."))]

    mock_ticker = MagicMock()
    mock_ticker.news = [{"title": "Company beats earnings expectations"}]

    with patch("main.yf.Ticker", return_value=mock_ticker), \
         patch("main.openai_client.chat.completions.create", return_value=fake_response):
        response = client.post("/weekly-update/VNQ")

    assert response.status_code == 200
    assert "earnings" in response.json()["update"].lower()


def test_weekly_update_no_news_returns_404(client):
    mock_ticker = MagicMock()
    mock_ticker.news = []

    with patch("main.yf.Ticker", return_value=mock_ticker):
        response = client.post("/weekly-update/UNKNOWN")

    assert response.status_code == 404


def test_weekly_update_handles_nested_content_format(client):
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="Summary."))]

    mock_ticker = MagicMock()
    mock_ticker.news = [{"content": {"title": "New product launch announced"}}]

    with patch("main.yf.Ticker", return_value=mock_ticker), \
         patch("main.openai_client.chat.completions.create", return_value=fake_response) as mock_create:
        response = client.post("/weekly-update/VNQ")

    assert response.status_code == 200
    sent_prompt = mock_create.call_args.kwargs["messages"][1]["content"]
    assert "New product launch announced" in sent_prompt
