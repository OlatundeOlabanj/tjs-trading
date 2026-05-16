# Upgrade Notes — v1.1

## Changes in this version

### Bug Fix: CMC scan returning 0 coins
The `market_cap_min` filter is now passed directly to the CoinMarketCap API
(`market_cap_min` param on `/v1/cryptocurrency/listings/latest`) so filtering
happens server-side before sorting. Previously the app fetched `n*3` raw
results sorted by 24h change, then post-filtered by market cap — but top
gainers/losers are almost always micro-caps, so the client-side filter wiped
them all. **No migration needed** for this fix.

### Feature: Technical Analysis per coin
- New service `app/services/coingecko_service.py` — free OHLCV from CoinGecko,
  no API key required
- New service `app/services/ta_service.py` — RSI, MACD, Bollinger Bands,
  EMA 20/50, Volume trend, Support/Resistance using pure numpy (no TA-lib)
- `Prediction` model has a new `ta_data TEXT` column (JSON blob)
- TA summary is injected into the Groq prompt for crypto assets, so AI
  predictions are now grounded in price-action data
- `prediction_detail.html` shows a full TA section with per-indicator signal
  badges (Bullish / Bearish / Neutral)
- FX and commodity assets skip TA gracefully with a note

## Database migration required

Run this after pulling the update:

```bash
flask --app run.py db migrate -m "add ta_data to predictions"
flask --app run.py db upgrade
```

Or for SQLite (dev), you can also just drop and recreate:

```bash
rm instance/tjs_trading_dev.db
flask --app run.py db upgrade
```
