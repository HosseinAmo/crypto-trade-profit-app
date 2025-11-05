#  Crypto Trade Profit Calculator (Web)

A browser-based app to compute crypto trade **purchase total**, **sell total**, and **profit/loss** from historical data.  
Supports **date fallback** (nearest previous trading day), **coin comparison**, and optional **AI insights** via OpenAI.

##  Features
- Select coin, quantity (fractional), buy & sell dates (clamped to dataset)
- Real-time totals and profit/loss with percentage
- Compare a second coin over the same period
- Show OHLC values for buy/sell dates
- Optional AI explanation (set `OPENAI_API_KEY`)

##  Data format
CSV with columns:
