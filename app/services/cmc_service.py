"""
CoinMarketCap Service
- Gainers/losers with market cap filter ($50M+ by default)
- Coin search by name or symbol
"""
import time
import logging
from typing import Optional
import requests
from flask import current_app

logger = logging.getLogger(__name__)

_cache: dict = {}
_cache_ts: dict = {}


def _cached(key: str, ttl: int, fetch_fn):
    now = time.time()
    if key in _cache and (now - _cache_ts.get(key, 0)) < ttl:
        return _cache[key]
    result = fetch_fn()
    if result is not None:
        _cache[key] = result
        _cache_ts[key] = now
    return result


class CMCService:
    BASE_URL = "https://pro-api.coinmarketcap.com"

    def __init__(self):
        self.api_key   = current_app.config.get("CMC_API_KEY", "")
        self.cache_ttl = current_app.config.get("CMC_CACHE_SECONDS", 120)
        self.limit     = current_app.config.get("SCAN_LIMIT", 10)
        self.mcap_min  = current_app.config.get("MARKET_CAP_MIN", 50_000_000)
        if not self.api_key:
            raise RuntimeError("CMC_API_KEY is not set. Get a free key at coinmarketcap.com/api")

    def _headers(self):
        return {"Accepts": "application/json", "X-CMC_PRO_API_KEY": self.api_key}

    def _get(self, endpoint: str, params: dict) -> Optional[dict]:
        try:
            r = requests.get(
                f"{self.BASE_URL}{endpoint}",
                headers=self._headers(), params=params, timeout=10
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            logger.error(f"CMC timeout: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"CMC error {endpoint}: {e}")
            return None

    # ── GAINERS ──────────────────────────────────────────────
    def get_top_gainers(self, limit: int = None) -> list:
        n = limit or self.limit
        def fetch():
            data = self._get("/v1/cryptocurrency/listings/latest", {
                "limit": n,
                "sort": "percent_change_24h",
                "sort_dir": "desc",
                "cryptocurrency_type": "all",
                "convert": "USD",
                "market_cap_min": self.mcap_min,   # server-side filter — fixes 0-coin scans
            })
            if not data: return []
            return [self._parse(c, "gainer") for c in data.get("data", [])]
        return _cached(f"gainers_{n}_{self.mcap_min}", self.cache_ttl, fetch) or []

    # ── LOSERS ───────────────────────────────────────────────
    def get_top_losers(self, limit: int = None) -> list:
        n = limit or self.limit
        def fetch():
            data = self._get("/v1/cryptocurrency/listings/latest", {
                "limit": n,
                "sort": "percent_change_24h",
                "sort_dir": "asc",
                "cryptocurrency_type": "all",
                "convert": "USD",
                "market_cap_min": self.mcap_min,   # server-side filter — fixes 0-coin scans
            })
            if not data: return []
            return [self._parse(c, "loser") for c in data.get("data", [])]
        return _cached(f"losers_{n}_{self.mcap_min}", self.cache_ttl, fetch) or []

    # ── GLOBAL METRICS ───────────────────────────────────────
    def get_global_metrics(self) -> Optional[dict]:
        def fetch():
            data = self._get("/v1/global-metrics/quotes/latest", {"convert": "USD"})
            if not data: return None
            d = data.get("data", {})
            q = d.get("quote", {}).get("USD", {})
            return {
                "btc_dominance": d.get("btc_dominance"),
                "eth_dominance": d.get("eth_dominance"),
                "total_market_cap": q.get("total_market_cap"),
                "total_volume_24h": q.get("total_volume_24h"),
            }
        return _cached("global_metrics", self.cache_ttl, fetch)

    # ── SEARCH ───────────────────────────────────────────────
    def search_coin(self, query: str) -> Optional[dict]:
        """
        Two-path resolution:
        1. Fast path: treat query as symbol → /quotes/latest
        2. Slow path: search /cryptocurrency/map for name match
        """
        q = query.strip().upper()

        # Fast path — try as symbol directly
        data = self._get("/v1/cryptocurrency/quotes/latest", {
            "symbol": q, "convert": "USD"
        })
        if data and "data" in data:
            entries = data["data"]
            # quotes/latest returns dict keyed by symbol
            for sym, coin_data in entries.items():
                if isinstance(coin_data, list):
                    coin_data = coin_data[0]
                return self._parse(coin_data, "search")

        # Slow path — name search via map
        map_data = self._get("/v1/cryptocurrency/map", {
            "listing_status": "active",
            "limit": 5000,
        })
        if not map_data: return None

        ql = query.strip().lower()
        match = None
        for entry in map_data.get("data", []):
            name_match   = entry.get("name", "").lower() == ql
            symbol_match = entry.get("symbol", "").upper() == q
            if name_match or symbol_match:
                match = entry
                break
            # Partial name match fallback
            if ql in entry.get("name", "").lower() and not match:
                match = entry

        if not match:
            return None

        # Fetch full quote for the matched coin
        symbol = match.get("symbol", "")
        quote_data = self._get("/v1/cryptocurrency/quotes/latest", {
            "symbol": symbol, "convert": "USD"
        })
        if not quote_data or "data" not in quote_data:
            return None

        entries = quote_data["data"]
        for sym, coin_data in entries.items():
            if isinstance(coin_data, list):
                coin_data = coin_data[0]
            return self._parse(coin_data, "search")

        return None

    # ── COMBINED SCAN ────────────────────────────────────────
    def run_scan(self, limit: int = None) -> dict:
        n = limit or self.limit
        return {
            "gainers": self.get_top_gainers(n),
            "losers":  self.get_top_losers(n),
            "global":  self.get_global_metrics() or {},
        }

    # ── PARSER ───────────────────────────────────────────────
    @staticmethod
    def _parse(raw: dict, category: str) -> dict:
        quote = raw.get("quote", {}).get("USD", {})
        return {
            "cmc_id":    raw.get("id"),
            "symbol":    raw.get("symbol", ""),
            "name":      raw.get("name", ""),
            "cmc_rank":  raw.get("cmc_rank"),
            "category":  category,
            "price_usd": quote.get("price", 0.0),
            "market_cap":         quote.get("market_cap"),
            "volume_24h":         quote.get("volume_24h"),
            "change_1h":          quote.get("percent_change_1h"),
            "change_24h":         quote.get("percent_change_24h", 0.0),
            "change_7d":          quote.get("percent_change_7d"),
            "circulating_supply": raw.get("circulating_supply"),
            "max_supply":         raw.get("max_supply"),
        }
