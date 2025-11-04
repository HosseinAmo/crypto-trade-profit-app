import pandas as pd
import streamlit as st
from datetime import date, timedelta
from decimal import Decimal

st.set_page_config(page_title="Crypto Trade Profit Calculator", page_icon="💹", layout="centered")

@st.cache_data
def load_data():
    # expects columns: date, open, high, low, close, volume, name, marketcap
    df = pd.read_csv("CryptoCoins_Prices/combined.csv")
    # normalize types
    df["date"] = pd.to_datetime(df["date"]).dt.date
    # keep only needed columns
    df = df[["date", "open", "high", "low", "close", "name"]].dropna()
    return df

df = load_data()
coins = sorted(df["name"].unique().tolist())

# dataset bounds
min_d = df["date"].min()
max_d = df["date"].max()

st.title("Crypto Trade Profit Calculator")
st.caption("Select a coin, quantity, and dates to see trade totals and profit/loss. Optional: compare with a second coin.")

# --- Inputs ---
c1, c2, c3 = st.columns([1.2, 1, 1])
with c1:
    coin1 = st.selectbox("Primary Coin", coins, index=coins.index("BTC") if "BTC" in coins else 0)
with c2:
    qty = st.number_input("Quantity", min_value=0.00000001, value=1.0, step=0.01, format="%.8f")
with c3:
    compare = st.checkbox("Compare another coin")

if compare:
    coin2 = st.selectbox("Secondary Coin", coins, index=coins.index("ETH") if "ETH" in coins else 0)
else:
    coin2 = None

default_sell = max_d
default_buy = max(min_d, default_sell - timedelta(days=14))

d1, d2 = st.columns(2)
with d1:
    buy_date = st.date_input("Purchase Date", value=default_buy, min_value=min_d, max_value=max_d)
with d2:
    sell_date = st.date_input("Sell Date", value=default_sell, min_value=min_d, max_value=max_d)

if buy_date > sell_date:
    st.warning("Purchase date is after Sell date. Adjusting Purchase date to Sell date.")
    buy_date = sell_date

# --- Helpers ---
def get_ohlc_on_or_before(_df: pd.DataFrame, coin: str, d: date):
    sub = _df[_df["name"] == coin]
    # pick the last row with date <= d
    sub = sub[sub["date"] <= d]
    if sub.empty:
        return None, None
    row = sub.sort_values("date").iloc[-1]
    return {
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
    }, row["date"]

def money(x: Decimal | float | None) -> str:
    if x is None:
        return "N/A"
    return f"${Decimal(str(x)):,.2f}"

def profit_style(value):
    if value is None:
        return "color:black;font-weight:700;"
    if value > 0:
        return "color:green;font-weight:700;"
    if value < 0:
        return "color:red;font-weight:700;"
    return "color:black;font-weight:700;"

def totals_for(coin):
    ohlc_buy, used_buy = get_ohlc_on_or_before(df, coin, buy_date)
    ohlc_sell, used_sell = get_ohlc_on_or_before(df, coin, sell_date)
    if not ohlc_buy or not ohlc_sell:
        return None
    buy_total = Decimal(str(qty)) * Decimal(str(ohlc_buy["close"]))
    sell_total = Decimal(str(qty)) * Decimal(str(ohlc_sell["close"]))
    profit = sell_total - buy_total
    return {
        "ohlc_buy": ohlc_buy, "used_buy": used_buy,
        "ohlc_sell": ohlc_sell, "used_sell": used_sell,
        "buy_total": buy_total, "sell_total": sell_total, "profit": profit
    }

# --- Results ---
st.subheader("Results")

res1 = totals_for(coin1)
res2 = totals_for(coin2) if compare else None

# Primary card
with st.container():
    st.markdown(f"### {coin1}")
    if res1 is None:
        st.error("Not enough data for selected dates.")
    else:
        cL, cR = st.columns(2)
        with cL:
            st.write(f"**Purchase @ {res1['used_buy']}**")
            st.write(f"Close: {res1['ohlc_buy']['close']:.6f}")
            st.write(f"Open/High/Low: {res1['ohlc_buy']['open']:.6f} / {res1['ohlc_buy']['high']:.6f} / {res1['ohlc_buy']['low']:.6f}")
            st.write(f"**Purchase Total:** {money(res1['buy_total'])}")
        with cR:
            st.write(f"**Sell @ {res1['used_sell']}**")
            st.write(f"Close: {res1['ohlc_sell']['close']:.6f}")
            st.write(f"Open/High/Low: {res1['ohlc_sell']['open']:.6f} / {res1['ohlc_sell']['high']:.6f} / {res1['ohlc_sell']['low']:.6f}")
            st.write(f"**Sell Total:** {money(res1['sell_total'])}")
        st.markdown(f"<div style='{profit_style(float(res1['profit']))}'>Profit / (Loss): {money(res1['profit'])}</div>", unsafe_allow_html=True)

st.divider()

# Secondary (comparison) card
if compare:
    st.markdown(f"### {coin2}")
    if res2 is None:
        st.error("Not enough data for selected dates.")
    else:
        cL, cR = st.columns(2)
        with cL:
            st.write(f"**Purchase @ {res2['used_buy']}**")
            st.write(f"Close: {res2['ohlc_buy']['close']:.6f}")
            st.write(f"Open/High/Low: {res2['ohlc_buy']['open']:.6f} / {res2['ohlc_buy']['high']:.6f} / {res2['ohlc_buy']['low']:.6f}")
            st.write(f"**Purchase Total:** {money(res2['buy_total'])}")
        with cR:
            st.write(f"**Sell @ {res2['used_sell']}**")
            st.write(f"Close: {res2['ohlc_sell']['close']:.6f}")
            st.write(f"Open/High/Low: {res2['ohlc_sell']['open']:.6f} / {res2['ohlc_sell']['high']:.6f} / {res2['ohlc']['low']:.6f}" if 'ohlc' in res2 else f"Open/High/Low: {res2['ohlc_sell']['open']:.6f} / {res2['ohlc_sell']['high']:.6f} / {res2['ohlc_sell']['low']:.6f}")
            st.write(f"**Sell Total:** {money(res2['sell_total'])}")
        st.markdown(f"<div style='{profit_style(float(res2['profit']))}'>Profit / (Loss): {money(res2['profit'])}</div>", unsafe_allow_html=True)

    if res1 and res2:
        diff = res2["profit"] - res1["profit"]
        st.markdown(f"### Difference (Secondary − Primary): "
                    f"<span style='{profit_style(float(diff))}'>{money(diff)}</span>", unsafe_allow_html=True)

st.divider()

# --- Optional: AI advisor (OpenAI). Uncomment after adding your key to st.secrets
# import openai
# from openai import OpenAI
# client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
# if st.button("Ask AI for insight"):
#     if res1:
#         prompt = (f"Explain this trade for a beginner:\n"
#                   f"Coin: {coin1}\nQuantity: {qty}\nBuy date: {buy_date}, buy close: {res1['ohlc_buy']['close']}\n"
#                   f"Sell date: {sell_date}, sell close: {res1['ohlc_sell']['close']}\n"
#                   f"Profit: {money(res1['profit'])}. Keep it concise and neutral.")
#         resp = client.chat.completions.create(model="gpt-5", messages=[{"role":"user","content":prompt}])
#         st.info(resp.choices[0].message.content)
