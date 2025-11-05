

import os
from datetime import date, timedelta
from decimal import Decimal
import pandas as pd
import streamlit as st

# ---------- Streamlit setup ----------
st.set_page_config(page_title="Crypto Trade Profit Calculator", page_icon="💹", layout="centered")
st.title("💹 Crypto Trade Profit Calculator")
st.caption("Calculate crypto trade profit/loss from historical data. Supports multiple coins and optional AI insights.")

# ---------- Data loading (robust to capitalization) ----------
@st.cache_data
def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    lower_map = {c.lower(): c for c in df.columns}

    def resolve(names):
        for n in names:
            if n.lower() in lower_map:
                return lower_map[n.lower()]
        return None

    date_col = resolve(["Date", "date"])
    open_col = resolve(["Open", "open"])
    high_col = resolve(["High", "high"])
    low_col = resolve(["Low", "low"])
    close_col = resolve(["Close", "close", "Adj Close", "close_price", "Close Price"])
    name_col = resolve(["Name", "name", "Symbol", "symbol", "Ticker", "ticker", "Coin", "coin"])

    missing = []
    if date_col is None: missing.append("Date")
    if open_col is None: missing.append("Open")
    if high_col is None: missing.append("High")
    if low_col is None: missing.append("Low")
    if close_col is None: missing.append("Close")
    if name_col is None: missing.append("Name (or Symbol/Ticker)")

    if missing:
        st.error("⚠️ Your CSV file is missing these columns:")
        st.code("\n".join(missing))
        st.write("Found columns:", list(df.columns))
        st.stop()

    df = df[[date_col, open_col, high_col, low_col, close_col, name_col]].dropna()
    df = df.rename(columns={
        date_col: "Date",
        open_col: "Open",
        high_col: "High",
        low_col: "Low",
        close_col: "Close",
        name_col: "Name",
    })
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    return df


@st.cache_data
def build_index(df: pd.DataFrame):
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


# ---------- Load dataset ----------
CSV_PATH = os.path.join(os.path.dirname(__file__), "CryptoCoins_Prices", "combined.csv")

st.subheader("📊 Dataset Diagnostics")
st.write("Looking for file:", CSV_PATH)
st.write("File exists?:", os.path.exists(CSV_PATH))

if not os.path.exists(CSV_PATH):
    st.error("❌ CSV file not found. Please ensure it's at `CryptoCoins_Prices/combined.csv` in your repo.")
    st.stop()

try:
    df = load_data(CSV_PATH)
except Exception as e:
    st.error("❌ Failed to read your CSV file. See details below:")
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("⚠️ CSV loaded but contains no valid data after cleaning. Check column names and formatting.")
    st.stop()

st.success(f"✅ Loaded {len(df):,} rows across {df['Name'].nunique()} coins.")
st.dataframe(df.head(5), use_container_width=True)

data = build_index(df)
tickers = sorted(data.keys())
if not tickers:
    st.error("❌ No tickers found after grouping by 'Name' column.")
    st.stop()

# ---------- Date bounds ----------
all_dates = df["Date"].dt.date
min_d, max_d = min(all_dates), max(all_dates)
default_buy = max(min_d, (max_d - timedelta(days=14)))

# ---------- Sidebar inputs ----------
with st.sidebar:
    st.header("⚙️ Trade Inputs")
    default_primary = tickers.index("BTC") if "BTC" in tickers else 0
    coin1 = st.selectbox("Primary coin", tickers, index=default_primary)
    qty = st.number_input("Quantity", min_value=0.00000001, value=1.0, step=0.01, format="%.8f")

    d_buy = st.date_input("Purchase date", value=default_buy, min_value=min_d, max_value=max_d, key="buy_date")
    d_sell = st.date_input("Sell date", value=max_d, min_value=min_d, max_value=max_d, key="sell_date")

    if d_buy > d_sell:
        st.warning("Purchase date is after sell date — adjusted to match sell date.")
        d_buy = d_sell

    compare = st.checkbox("Compare with another coin")
    default_secondary = tickers.index("ETH") if "ETH" in tickers else 0
    coin2 = st.selectbox("Secondary coin", tickers, index=default_secondary, disabled=not compare)


# ---------- Helpers ----------
def price_on_or_before(ticker: str, d: date):
    mp = data[ticker]
    if d in mp:
        return mp[d], d
    keys = sorted(mp.keys())
    lo, hi = 0, len(keys) - 1
    cand = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if keys[mid] == d:
            cand = keys[mid]; break
        elif keys[mid] < d:
            cand = keys[mid]; lo = mid + 1
        else:
            hi = mid - 1
    if cand is None:
        return None, None
    return mp[cand], cand


def money(x: Decimal | float | None) -> str:
    if x is None: return "N/A"
    return f"${Decimal(str(x)):,.2f}"


def result_block(ticker, qty, d_buy, d_sell):
    ohlc_b, used_b = price_on_or_before(ticker, d_buy)
    ohlc_s, used_s = price_on_or_before(ticker, d_sell)
    if not ohlc_b or not ohlc_s:
        return None
    buy_total = Decimal(str(qty)) * Decimal(str(ohlc_b["close"]))
    sell_total = Decimal(str(qty)) * Decimal(str(ohlc_s["close"]))
    profit = sell_total - buy_total
    pct = (profit / buy_total * Decimal("100")) if buy_total != 0 else Decimal("0")
    return {
        "buy_total": buy_total, "sell_total": sell_total, "profit": profit, "pct": pct,
        "buy_used": used_b, "sell_used": used_s, "buy": ohlc_b, "sell": ohlc_s
    }


# ---------- Main results ----------
col1, col2 = st.columns(2)
with col1:
    st.subheader(f"📈 Primary: {coin1}")
    r1 = result_block(coin1, qty, d_buy, d_sell)
    if r1:
        st.metric("Purchase total", money(r1["buy_total"]))
        st.metric("Sell total", money(r1["sell_total"]))
        delta = f"{r1['pct']:.2f}%"
        delta_color = "normal" if r1["profit"] >= 0 else "inverse"
        st.metric("Profit / (Loss)", money(r1["profit"]), delta, delta_color=delta_color)
        st.caption(f"Buy @ {r1['buy_used']} — Close: {r1['buy']['close']}")
        st.caption(f"Sell @ {r1['sell_used']} — Close: {r1['sell']['close']}")
    else:
        st.warning("No valid prices for selected dates.")

with col2:
    if compare:
        st.subheader(f"📉 Secondary: {coin2}")
        r2 = result_block(coin2, qty, d_buy, d_sell)
        if r2:
            st.metric("Purchase total", money(r2["buy_total"]))
            st.metric("Sell total", money(r2["sell_total"]))
            delta = f"{r2['pct']:.2f}%"
            delta_color = "normal" if r2["profit"] >= 0 else "inverse"
            st.metric("Profit / (Loss)", money(r2["profit"]), delta, delta_color=delta_color)
            st.caption(f"Buy @ {r2['buy_used']} — Close: {r2['buy']['close']}")
            st.caption(f"Sell @ {r2['sell_used']} — Close: {r2['sell']['close']}")
        else:
            st.warning("No valid prices for selected dates.")

st.divider()

# ---------- Optional AI Insights (Free via Groq) ----------
st.subheader("🤖 AI Insight (Groq Free API)")
st.caption("Uses Groq's open LLaMA 3 model — no OpenAI credits required!")

prompt = st.text_area("Ask something like: 'Explain my profit in simple terms'")

if st.button("Ask AI"):
    api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
    if not api_key:
        st.error("⚠️ No Groq API key found. Add one in Streamlit Secrets.")
    else:
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key
            )

            context = f"""
            Coin: {coin1}
            Quantity: {qty}
            Buy date: {d_buy}
            Sell date: {d_sell}
            Result: {r1}
            """
            if compare and 'r2' in locals() and r2:
                context += f"\nComparison coin: {coin2}\nComparison result: {r2}\n"

            q = f"Given the context above, answer clearly: {prompt}"

            resp = client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct-0905",
                messages=[{"role": "user", "content": context + '\n' + q}],
                temperature=0.3,
            )

            st.success(resp.choices[0].message.content)
        except Exception as e:
            st.error(f"Error: {e}")

