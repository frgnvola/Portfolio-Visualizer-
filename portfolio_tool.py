# portfolio_tool.py
# ------------------------------------------------------------
# FULL PORTFOLIO PROCESSOR MODULE FOR FLASK DASHBOARD
# ------------------------------------------------------------

import pandas as pd
import yfinance as yf
from datetime import datetime

# ------------------------------------------------------------
# 1. PRICE FETCH FUNCTIONS
# ------------------------------------------------------------

def fetch_stock_price(ticker: str) -> float:
    t = yf.Ticker(ticker)
    hist = t.history(period="1d")

    if hist.empty:
        raise ValueError(f"No price data returned for STOCK {ticker}")

    return float(hist["Close"].iloc[-1])


def fetch_crypto_price(symbol: str) -> float:
    t = yf.Ticker(f"{symbol}-USD")
    hist = t.history(period="1d")

    if hist.empty:
        raise ValueError(f"No price data returned for CRYPTO {symbol}")

    return float(hist["Close"].iloc[-1])


def fetch_cd_price(row: pd.Series) -> float:
    """
    Price CDs without an 'extra' column.
    For your SAFRA CD, we use the known dealer bid.
    Everything else defaults to cost_basis.
    """
    cusip = str(row["ticker"]).upper()

    # Hardcode known bid
    if cusip == "BANKOFNY":     # SAFRA 3.75% CD
        return 99.632 / 100.0

    return float(row["cost_basis"])


# ------------------------------------------------------------
# 2. ROUTER FUNCTION (determines which pricing method to use)
# ------------------------------------------------------------

def fetch_price(row: pd.Series) -> float:
    atype = row["asset_type"].lower()
    t = row["ticker"]

    if atype == "stock":
        return fetch_stock_price(t)

    elif atype == "crypto":
        return fetch_crypto_price(t)

    elif atype in ("cd", "bond"):
        return fetch_cd_price(row)

    elif atype == "cash":
        return 1.0

    else:
        raise ValueError(f"Unknown asset type: {atype}")


# ------------------------------------------------------------
# 3. FUNDAMENTAL DATA FETCHER
# ------------------------------------------------------------

def fetch_fundamentals(ticker):
    t = yf.Ticker(ticker)
    info = t.info

    fundamentals = {
        "pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "ps": info.get("priceToSalesTrailing12Months"),
        "profit_margin": info.get("profitMargins"),
        "revenue_growth": info.get("revenueGrowth"),
        "eps_growth": info.get("earningsQuarterlyGrowth"),
        "beta": info.get("beta"),
        "analyst_score": info.get("recommendationMean"),
        "target_price": info.get("targetMeanPrice"),
    }
    return fundamentals


# ------------------------------------------------------------
# 4. Wrapper for fetch_fundementals to avoid errors in fetching data from yfinance (e.g. for CDs or Crypto)
# ------------------------------------------------------------

def safe_fundamentals(row):
    if row["asset_type"].lower() != "stock":
        return {
            "pe": None,
            "forward_pe": None,
            "ps": None,
            "profit_margin": None,
            "revenue_growth": None,
            "eps_growth": None,
            "beta": None,
            "analyst_score": None,
            "target_price": None,
        }

    try:
        return fetch_fundamentals(row["ticker"])
    except:
        return {
            "pe": None,
            "forward_pe": None,
            "ps": None,
            "profit_margin": None,
            "revenue_growth": None,
            "eps_growth": None,
            "beta": None,
            "analyst_score": None,
            "target_price": None,
        }

# ------------------------------------------------------------
# 5. POSITION SCORING / DECISION ENGINE
# ------------------------------------------------------------

def score_position(row):
    score = 0

    # Position-based risk
    if row["pl_pct"] > 80:
        score -= 1
    if row["weight_pct"] > 7:
        score -= 1
    if row["pl_pct"] < -20:
        score -= 1

    # Fundamentals
    if row.get("pe") and row["pe"] > 40:
        score -= 1
    if row.get("forward_pe") and row["forward_pe"] < 20:
        score += 1
    if row.get("analyst_score") and row["analyst_score"] < 2.5:
        score += 1

    return score


def decision_label(score):
    if score >= 2:
        return "Strong Buy"
    if score == 1:
        return "Buy / Hold"
    if score == 0:
        return "Review"
    if score == -1:
        return "Trim"
    return "Sell"


# ------------------------------------------------------------
# 5. INSIGHT STRING BUILDER
# ------------------------------------------------------------

def build_insight(row):
    insights = []

    if row["pl_pct"] > 80:
        insights.append("Large unrealized gain")

    if row["pl_pct"] < -20:
        insights.append("Large loss")

    if row["weight_pct"] > 7:
        insights.append("High concentration")

    if row.get("pe") and row["pe"] > 40:
        insights.append("High valuation")

    if row.get("analyst_score") and row["analyst_score"] < 2:
        insights.append("Analysts bullish")

    return "; ".join(insights) if insights else "Stable"


# ------------------------------------------------------------
# 6. MAIN FUNCTION FOR FLASK TO CALL
# ------------------------------------------------------------

def load_and_process_portfolio():

    # Load CSV (make sure it has: asset_type, ticker, shares, cost_basis)
    portfolio = pd.read_csv("portfolio.csv")

    # Fetch prices
    portfolio["current_price"] = portfolio.apply(fetch_price, axis=1)

    # Core metrics
    portfolio["market_value"] = portfolio["shares"] * portfolio["current_price"]
    portfolio["cost_value"] = portfolio["shares"] * portfolio["cost_basis"]
    portfolio["pl_dollar"] = portfolio["market_value"] - portfolio["cost_value"]
    portfolio["pl_pct"] = (portfolio["pl_dollar"] / portfolio["cost_value"]) * 100

    total_value = portfolio["market_value"].sum(skipna=True)

    portfolio["weight_pct"] = (
        portfolio["market_value"] / total_value * 100
    )

    # Fundamentals
    fundamentals = portfolio.apply(safe_fundamentals, axis=1)
    fundamentals_df = pd.DataFrame(fundamentals.tolist())
    portfolio = pd.concat([portfolio, fundamentals_df], axis=1)

    # Scoring + decisions
    portfolio["score"] = portfolio.apply(score_position, axis=1)
    portfolio["decision"] = portfolio["score"].apply(decision_label)
    portfolio["insights"] = portfolio.apply(build_insight, axis=1)

    # Rounding
    portfolio["shares"] = portfolio["shares"].round(3)
    portfolio["current_price"] = portfolio["current_price"].round(2)
    portfolio["market_value"] = portfolio["market_value"].round(2)
    portfolio["cost_value"] = portfolio["cost_value"].round(2)
    portfolio["pl_dollar"] = portfolio["pl_dollar"].round(2)
    portfolio["pl_pct"] = portfolio["pl_pct"].round(2)
    portfolio["weight_pct"] = portfolio["weight_pct"].round(2)

    return portfolio


def format_for_display(df: pd.DataFrame) -> pd.DataFrame:
    display = df.copy()

    fund_cols = [
        "pe", "forward_pe", "ps",
        "profit_margin", "revenue_growth", "eps_growth",
        "beta", "analyst_score", "target_price"
    ]

    # Convert all fundamental columns to string FIRST
    for col in fund_cols:
        if col in display.columns:
            display[col] = display[col].apply(
                lambda x: "" if pd.isna(x) else str(round(x, 2)) if isinstance(x, (int, float)) else str(x)
            )

    # Blank rows for non-stock assets
    mask_non_stock = display["asset_type"].str.lower() != "stock"
    for col in fund_cols:
        if col in display.columns:
            display.loc[mask_non_stock, col] = ""

    # Replace remaining NaN with blank
    display = display.fillna("")

    return display