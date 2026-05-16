"""
CoinGecko Service — free OHLCV data, no API key required.

Fetches 90 days of daily OHLCV for a given symbol.
Tries the /coins/list endpoint to resolve CMC symbol → CoinGecko id,
then /coins/{id}/ohlc for the candle data.

Returns a list of dicts:
  [{"timestamp": int_ms, "open": f, "high": f, "low": f, "close": f, "volume": f}, ...]
sorted oldest → newest. Returns [] on any failure — callers must treat
an empty list as "TA not available" rather than an error.
"""
import logging
import time
import requests
from typing import Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://api.coingecko.com/api/v3"
TIMEOUT  = 10

# In-process cache: symbol.upper() → {"id": str, "ts": float}
_id_cache: dict = {}
# OHLCV cache: coingecko_id → {"data": list, "ts": float}
_ohlcv_cache: dict = {}
_OHLCV_TTL = 300   # 5 min — free tier rate-limits are strict


def _get(endpoint: str, params: dict = None) -> Optional[dict | list]:
    try:
        r = requests.get(
            f"{BASE_URL}{endpoint}",
            params=params or {},
            timeout=TIMEOUT,
            headers={"Accept": "application/json"},
        )
        if r.status_code == 429:
            logger.warning("CoinGecko rate limit hit — skipping TA")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"CoinGecko error {endpoint}: {e}")
        return None


def _resolve_id(symbol: str) -> Optional[str]:
    """Map a ticker symbol (e.g. 'BTC') to a CoinGecko coin id (e.g. 'bitcoin')."""
    sym = symbol.strip().upper()
    cached = _id_cache.get(sym)
    if cached and (time.time() - cached["ts"]) < 3600:
        return cached["id"]

    # /search is cheaper than /coins/list (no full list download)
    data = _get("/search", {"query": sym})
    if not data:
        return None

    coins = data.get("coins", [])
    # Prefer exact symbol match, then first result
    match = None
    for c in coins:
        if c.get("symbol", "").upper() == sym:
            match = c
            break
    if not match and coins:
        match = coins[0]
    if not match:
        return None

    cg_id = match.get("id")
    _id_cache[sym] = {"id": cg_id, "ts": time.time()}
    return cg_id


def fetch_ohlcv(symbol: str, days: int = 90) -> list:
    """
    Fetch daily OHLCV candles for `symbol` over the last `days` days.
    Returns a list of dicts sorted oldest → newest, or [] on failure.

    NOTE: CoinGecko /ohlc granularity is determined by the `days` param:
      1–14  days → hourly candles  (NOT daily — volume alignment breaks)
      15–90 days → daily candles   ← we use 90 as the default
      91+   days → daily candles
    Always use days >= 15 to guarantee daily granularity.
    """
    cg_id = _resolve_id(symbol)
    if not cg_id:
        logger.info(f"CoinGecko: no id found for {symbol}")
        return []

    cached = _ohlcv_cache.get(cg_id)
    if cached and (time.time() - cached["ts"]) < _OHLCV_TTL:
        return cached["data"]

    # /ohlc returns [[timestamp_ms, open, high, low, close], ...]
    # days param must be 1|7|14|30|90|180|365|max
    raw = _get(f"/coins/{cg_id}/ohlc", {"vs_currency": "usd", "days": days})
    if not raw or not isinstance(raw, list):
        return []

    # Volume comes from market_chart — merge it in if possible (best-effort)
    vol_map: dict = {}
    mchart = _get(f"/coins/{cg_id}/market_chart",
                  {"vs_currency": "usd", "days": days, "interval": "daily"})
    if mchart:
        for ts_ms, vol in mchart.get("total_volumes", []):
            # Round to day bucket (midnight UTC) so keys line up with OHLC
            day_ts = int(ts_ms // 86_400_000) * 86_400_000
            vol_map[day_ts] = float(vol)

    candles = []
    for row in raw:
        ts_ms  = int(row[0])
        day_ts = int(ts_ms // 86_400_000) * 86_400_000
        candles.append({
            "timestamp": ts_ms,
            "open":   float(row[1]),
            "high":   float(row[2]),
            "low":    float(row[3]),
            "close":  float(row[4]),
            "volume": vol_map.get(day_ts, 0.0),
        })

    candles.sort(key=lambda x: x["timestamp"])
    _ohlcv_cache[cg_id] = {"data": candles, "ts": time.time()}
    return candles
