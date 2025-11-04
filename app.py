# ---------- Data loading (robust to column name cases/aliases) ----------
import os
import pandas as pd
import streamlit as st
from datetime import timedelta
from decimal import Decimal

@st.cache_data
def load_data(csv_path: str) -> pd.DataFrame:
    """
    Load CSV and normalize columns in a case-insensitive way.
    Accepts common aliases like Symbol->Name, Ticker->Name, Close Price->Close, etc.
    Required logical columns: date, open, high, low, close, name
    """
    df = pd.read_csv(csv_path)

    # Strip whitespace from headers
    df.columns = [c.strip() for c in df.columns]

    # Build a case-insensitive lookup from lowercase->actual
    lower_to_actual = {c.lower(): c for c in df.columns}

    # Helper to resolve a column by preferred names (case-insensitive)
    def resolve(preferred_names):
        for p in preferred_names:
            if p.lower() in lower_to_actual:
                return lower_to_actual[p.lower()]
        return None

    # Resolve required logical columns, allowing aliases
    date_col  = resolve(["Date", "date"])
    open_col  = resolve(["Open", "open", "Open Price", "open_price"])
    high_col  = resolve(["High", "high"])
    low_col   = resolve(["Low", "low"])
    close_col = resolve(["Close", "close", "Adj Close", "close_price", "Close Price"])
    name_col  = resolve(["Name", "name", "Symbol", "symbol", "Ticker", "ticker", "Coin", "coin"])

    missing = []
    if date_col  is None: missing.append("Date")
    if open_col  is None: missing.append("Open")
    if high_col  is None: missing.append("High")
    if low_col   is None: missing.append("Low")
    if close_col is None: missing.append("Close")
    if name_col  is None: missing.append("Name (or Symbol/Ticker)")

    if missing:
        st.error(
            "Your CSV is missing expected columns:\n\n- " +
            "\n- ".join(missing) +
            "\n\nFound columns:\n" + ", ".join(df.columns)
        )
        st.stop()

    # Keep only needed columns and standardize types
    df = df[[date_col, open_col, high_col, low_col, close_col, name_col]].dropna()
    # Rename to canonical names used by the rest of the app
    df = df.rename(columns={
        date_col:  "Date",
        open_col:  "Open",
        high_col:  "High",
        low_col:   "Low",
        close_col: "Close",
        name_col:  "Name",
    })

    # Parse dates
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    return df

@st.cache_data
def build_index(df: pd.DataFrame):
    """
    Build nested map: data[ticker][date] -> {open,high,low,close}
    (Assumes df columns are canonical after load_data())
    """
    data = {}
    for name, g in df.groupby("Name"):
        g = g.sort_values("Date")
        data[name] = {
            d.date(): {
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
            }
            for d, o, h, l, c in zip(g["Date"], g["Open"], g["High"], g["Low"], g["Close"])
        }
    return data

# ---------- Use the functions ----------
CSV_PATH = os.path.join(os.path.dirname(__file__), "CryptoCoins_Prices", "combined.csv")
df = load_data(CSV_PATH)
data = build_index(df)

tickers = sorted(data.keys())

# Derive global date bounds from canonical "Date"
all_dates = df["Date"].dt.date
min_d, max_d = min(all_dates), max(all_dates)

# Default buy date = max - 14 days (clamped)
from datetime import timedelta
default_buy = max(min_d, (max_d - timedelta(days=14)))
