"""
Frankfurter Service — Free FX + Commodity rates (no API key needed)
Source: api.frankfurter.app (ECB data)
Supports: major FX pairs, Gold (XAU), Silver (XAG)
"""
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://api.frankfurter.app"

# Alias table: nickname -> base/quote
ALIASES = {
    # Common nicknames
    "pound":   ("GBP", "USD"), "sterling": ("GBP", "USD"),
    "euro":    ("EUR", "USD"), "eur":      ("EUR", "USD"),
    "yen":     ("USD", "JPY"), "jpy":      ("USD", "JPY"),
    "franc":   ("USD", "CHF"), "chf":      ("USD", "CHF"),
    "loonie":  ("USD", "CAD"), "cad":      ("USD", "CAD"),
    "aussie":  ("AUD", "USD"), "aud":      ("AUD", "USD"),
    "kiwi":    ("NZD", "USD"), "nzd":      ("NZD", "USD"),
    "naira":   ("USD", "NGN"), "ngn":      ("USD", "NGN"),
    "rand":    ("USD", "ZAR"), "zar":      ("USD", "ZAR"),
    # Metals
    "gold":    ("XAU", "USD"), "xau":      ("XAU", "USD"), "xauusd": ("XAU", "USD"),
    "silver":  ("XAG", "USD"), "xag":      ("XAG", "USD"), "xagusd": ("XAG", "USD"),
    # Common pairs
    "eurusd":  ("EUR", "USD"), "gbpusd":   ("GBP", "USD"),
    "usdjpy":  ("USD", "JPY"), "gbpjpy":   ("GBP", "JPY"),
    "usdchf":  ("USD", "CHF"), "usdcad":   ("USD", "CAD"),
    "audusd":  ("AUD", "USD"), "nzdusd":   ("NZD", "USD"),
    "usdngn":  ("USD", "NGN"),
}

# Frankfurter doesn't support XAU/XAG natively — we use a static approximate
# For demo/prediction purposes; real gold data would need metals API
METAL_APPROX = {
    "XAU": {"price": 3300.0, "change_24h": 0.8,  "name": "Gold",   "symbol": "XAUUSD"},
    "XAG": {"price": 33.0,   "change_24h": 0.5,  "name": "Silver", "symbol": "XAGUSD"},
}

SUPPORTED_CURRENCIES = {
    "AUD","BGN","BRL","CAD","CHF","CNY","CZK","DKK","EUR","GBP",
    "HKD","HUF","IDR","ILS","INR","ISK","JPY","KRW","MXN","MYR",
    "NOK","NZD","PHP","PLN","RON","SEK","SGD","THB","TRY","USD",
    "ZAR","NGN",
}


class FrankfurterService:

    def resolve(self, query: str) -> Optional[dict]:
        """
        Resolve query string to a market data dict.
        Returns same shape as CMCService._parse() for compatibility.
        """
        q = query.strip().lower().replace("/", "").replace("-", "").replace(" ", "")

        # 1. Check alias table
        if q in ALIASES:
            base, quote = ALIASES[q]
            return self._fetch(base, quote)

        # 2. Metal check
        qu = q.upper()
        if qu in METAL_APPROX:
            return self._metal(qu)

        # 3. Try as 6-char pair e.g. EURUSD
        if len(q) == 6:
            base, quote = q[:3].upper(), q[3:].upper()
            if base in SUPPORTED_CURRENCIES or quote in SUPPORTED_CURRENCIES:
                return self._fetch(base, quote)

        # 4. Single currency vs USD
        qu3 = qu[:3]
        if qu3 in SUPPORTED_CURRENCIES:
            return self._fetch(qu3, "USD") if qu3 != "USD" else self._fetch("EUR", "USD")

        return None

    def _fetch(self, base: str, quote: str) -> Optional[dict]:
        try:
            # Current rate
            r = requests.get(f"{BASE_URL}/latest", params={"from": base, "to": quote}, timeout=8)
            r.raise_for_status()
            current = r.json()
            current_rate = current.get("rates", {}).get(quote)
            if not current_rate:
                return None

            # Yesterday rate for 24h change
            r2 = requests.get(f"{BASE_URL}/1999-01-04", params={"from": base, "to": quote}, timeout=8)
            # Use a recent date for change calc
            import datetime
            yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
            r2 = requests.get(f"{BASE_URL}/{yesterday}", params={"from": base, "to": quote}, timeout=8)
            prev_rate = None
            if r2.status_code == 200:
                prev_rate = r2.json().get("rates", {}).get(quote)

            change_24h = 0.0
            if prev_rate and prev_rate > 0:
                change_24h = round((current_rate - prev_rate) / prev_rate * 100, 4)

            pair = f"{base}/{quote}"
            category = "commodity" if base in ("XAU", "XAG") else "forex"

            return {
                "cmc_id":    None,
                "symbol":    pair.replace("/", ""),
                "name":      _pair_name(base, quote),
                "cmc_rank":  None,
                "category":  category,
                "price_usd": current_rate,
                "market_cap": None,
                "volume_24h": None,
                "change_1h":  None,
                "change_24h": change_24h,
                "change_7d":  None,
                "circulating_supply": None,
                "max_supply": None,
                "base_currency":  base,
                "quote_currency": quote,
            }
        except Exception as e:
            logger.error(f"Frankfurter error {base}/{quote}: {e}")
            return None

    def _metal(self, symbol: str) -> dict:
        m = METAL_APPROX[symbol]
        return {
            "cmc_id": None, "symbol": m["symbol"], "name": m["name"],
            "cmc_rank": None, "category": "commodity",
            "price_usd": m["price"], "market_cap": None, "volume_24h": None,
            "change_1h": None, "change_24h": m["change_24h"], "change_7d": None,
            "circulating_supply": None, "max_supply": None,
        }


def _pair_name(base: str, quote: str) -> str:
    names = {
        "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound",
        "JPY": "Japanese Yen", "CHF": "Swiss Franc", "CAD": "Canadian Dollar",
        "AUD": "Australian Dollar", "NZD": "New Zealand Dollar",
        "NGN": "Nigerian Naira", "ZAR": "South African Rand",
        "XAU": "Gold", "XAG": "Silver",
    }
    b = names.get(base, base)
    q = names.get(quote, quote)
    return f"{b} / {q}"
