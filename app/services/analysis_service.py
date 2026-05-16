"""
Analysis Service — Groq (llama-3.3-70b-versatile, hardcoded)
Asset-type aware: crypto, forex, commodity prompts with correct profit targets.
"""
import json
import logging
import re
from typing import Optional

from groq import Groq

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"

CRYPTO_SYSTEM = """You are TJ's Crypto Trading Analyst. Analyze the given coin data and produce a trade signal.

RULES:
- Only recommend a trade if there is a realistic 30-50%+ profit path
- meta_score >= 80 AND bullish >= 65: up to 10x leverage
- meta_score 65-79 AND bullish >= 55: up to 5x leverage
- meta_score 50-64: up to 3x leverage
- meta_score < 50 OR rank > 200: 1x spot only
- verdict: "strong" = meta_score >= 70 and R/R >= 2:1, "moderate" = 50-69, "weak" = below 50

Return ONLY a raw JSON object. No markdown, no backticks, nothing else.

{
  "sentiment_bullish": <int 0-100>,
  "sentiment_bearish": <int 0-100>,
  "sentiment_neutral": <int 0-100>,
  "sentiment_label": "<bullish|bearish|neutral>",
  "meta_score": <int 0-100>,
  "profit_potential_min": <float>,
  "profit_potential_max": <float>,
  "entry_low": <float>,
  "entry_high": <float>,
  "target_price": <float>,
  "stop_loss": <float>,
  "recommended_leverage": "<e.g. 3x>",
  "leverage_note": "<max 12 words>",
  "verdict": "<strong|moderate|weak>",
  "summary": "<2-3 sharp sentences: what is happening, why, key risk>"
}"""

FOREX_SYSTEM = """You are TJ's Forex Trading Analyst. Analyze the given FX pair and produce a trade signal.

RULES:
- Forex profit targets are smaller: realistic targets are 0.5-3% per trade
- Leverage for forex is higher due to smaller moves: max 20x on majors, 10x on exotics
- meta_score >= 75: up to 20x on major pairs (EUR/USD, GBP/USD, USD/JPY)
- meta_score 55-74: up to 10x
- meta_score < 55: up to 5x
- verdict: "strong" = meta_score >= 65 and clear directional bias, "moderate" = 45-64, "weak" = below 45
- Entry/target/stop should be in the quote currency price (e.g. 1.0850 for EURUSD)

Return ONLY a raw JSON object. No markdown, no backticks, nothing else.

{
  "sentiment_bullish": <int 0-100>,
  "sentiment_bearish": <int 0-100>,
  "sentiment_neutral": <int 0-100>,
  "sentiment_label": "<bullish|bearish|neutral>",
  "meta_score": <int 0-100>,
  "profit_potential_min": <float, e.g. 0.5>,
  "profit_potential_max": <float, e.g. 2.0>,
  "entry_low": <float>,
  "entry_high": <float>,
  "target_price": <float>,
  "stop_loss": <float>,
  "recommended_leverage": "<e.g. 10x>",
  "leverage_note": "<max 12 words>",
  "verdict": "<strong|moderate|weak>",
  "summary": "<2-3 sharp sentences: pair direction, key driver, risk level>"
}"""

COMMODITY_SYSTEM = """You are TJ's Commodity Trading Analyst. Analyze the given commodity and produce a trade signal.

RULES:
- Commodity profit targets: Gold 0.5-4%, Silver 1-6%
- Gold leverage max 20x, Silver max 15x (high volatility)
- meta_score >= 75: max leverage for that commodity
- meta_score 55-74: half the max leverage
- meta_score < 55: 5x max
- verdict: "strong" = meta_score >= 65, "moderate" = 45-64, "weak" = below 45

Return ONLY a raw JSON object. No markdown, no backticks, nothing else.

{
  "sentiment_bullish": <int 0-100>,
  "sentiment_bearish": <int 0-100>,
  "sentiment_neutral": <int 0-100>,
  "sentiment_label": "<bullish|bearish|neutral>",
  "meta_score": <int 0-100>,
  "profit_potential_min": <float>,
  "profit_potential_max": <float>,
  "entry_low": <float>,
  "entry_high": <float>,
  "target_price": <float>,
  "stop_loss": <float>,
  "recommended_leverage": "<e.g. 10x>",
  "leverage_note": "<max 12 words>",
  "verdict": "<strong|moderate|weak>",
  "summary": "<2-3 sharp sentences: what is driving the move, key level, risk>"
}"""


class AnalysisService:
    def __init__(self, api_key: str, model: str = None):
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set. Get a free key at console.groq.com")
        self.client = Groq(api_key=api_key)
        self.model  = GROQ_MODEL  # always hardcoded

    def analyze_coin(self, coin: dict, system_prompt_override: str = None,
                     ta_text: str = None) -> Optional[dict]:
        category  = coin.get("category", "gainer")
        asset_type = _get_asset_type(category)

        if system_prompt_override:
            system = system_prompt_override
        elif asset_type == "forex":
            system = FOREX_SYSTEM
        elif asset_type == "commodity":
            system = COMMODITY_SYSTEM
        else:
            system = CRYPTO_SYSTEM

        user_msg = _build_user_msg(coin, asset_type)
        if ta_text and asset_type == "crypto":
            user_msg = user_msg + f"\n\n{ta_text}"

        try:
            logger.info(f"Groq [{asset_type}] analyzing {coin.get('symbol')}")
            resp = self.client.chat.completions.create(
                model=self.model,
                max_tokens=768,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user_msg},
                ],
            )
            raw = resp.choices[0].message.content
            if not raw:
                logger.warning(f"Empty Groq response for {coin.get('symbol')}")
                return None
            return self._parse(raw, coin)
        except Exception as e:
            logger.error(f"Groq error for {coin.get('symbol')}: {e}")
            return None

    def _parse(self, raw: str, coin: dict) -> Optional[dict]:
        text = re.sub(r"```(?:json)?", "", raw.strip()).strip().rstrip("`")
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            logger.error(f"No JSON for {coin.get('symbol')}: {text[:120]}")
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error {coin.get('symbol')}: {e}")
            return None

        # Normalise sentiments
        bull  = int(data.get("sentiment_bullish", 50))
        bear  = int(data.get("sentiment_bearish", 30))
        neut  = int(data.get("sentiment_neutral", 20))
        total = bull + bear + neut
        if total > 0 and total != 100:
            bull = round(bull / total * 100)
            bear = round(bear / total * 100)
            neut = 100 - bull - bear
        data["sentiment_bullish"] = bull
        data["sentiment_bearish"] = bear
        data["sentiment_neutral"] = neut
        data["meta_score"] = max(0, min(100, int(data.get("meta_score", 50))))

        if data.get("verdict") not in ("strong", "moderate", "weak"):
            s = data["meta_score"]
            data["verdict"] = "strong" if s >= 70 else "moderate" if s >= 50 else "weak"

        category   = coin.get("category", "gainer")
        asset_type = _get_asset_type(category)
        data["recommended_leverage"] = _enforce_leverage(
            data.get("recommended_leverage", "1x"),
            data["meta_score"], bull,
            coin.get("cmc_rank"), asset_type,
        )

        data.update({
            "symbol":     coin.get("symbol"),
            "name":       coin.get("name"),
            "price_usd":  coin.get("price_usd"),
            "change_24h": coin.get("change_24h"),
            "category":   category,
            "coin_db_id": coin.get("id"),
        })
        return data


# ── HELPERS ────────────────────────────────────────────────────────────

def _get_asset_type(category: str) -> str:
    if category in ("forex",):       return "forex"
    if category in ("commodity",):   return "commodity"
    return "crypto"


def _build_user_msg(coin: dict, asset_type: str) -> str:
    symbol   = coin.get("symbol", "")
    name     = coin.get("name", symbol)
    price    = coin.get("price_usd", 0)
    chg_1h   = coin.get("change_1h")  or 0
    chg_24h  = coin.get("change_24h") or 0
    chg_7d   = coin.get("change_7d")  or 0
    vol_24h  = coin.get("volume_24h") or 0
    mcap     = coin.get("market_cap") or 0
    rank     = coin.get("cmc_rank")   or "N/A"
    category = coin.get("category", "")

    if chg_24h > 10:    momentum = "STRONG UPTREND"
    elif chg_24h > 3:   momentum = "MODERATE UPTREND"
    elif chg_24h > -3:  momentum = "SIDEWAYS"
    elif chg_24h > -10: momentum = "MODERATE DOWNTREND"
    else:               momentum = "STRONG DOWNTREND"

    if asset_type == "forex":
        base = coin.get("base_currency", symbol[:3])
        quote = coin.get("quote_currency", symbol[3:])
        return (
            f"Analyze this FX pair for a trade:\n\n"
            f"PAIR: {name} ({symbol})\n"
            f"TYPE: Foreign Exchange\n\n"
            f"RATE DATA:\n"
            f"  Current Rate: {price:.5f}\n"
            f"  Change 24H: {chg_24h:+.4f}%\n"
            f"  Base Currency: {base}\n"
            f"  Quote Currency: {quote}\n\n"
            f"MOMENTUM: {momentum}\n\n"
            f"Provide a complete FX trade analysis. Return ONLY the JSON object."
        )

    if asset_type == "commodity":
        return (
            f"Analyze this commodity for a trade:\n\n"
            f"COMMODITY: {name} ({symbol})\n"
            f"TYPE: Commodity\n\n"
            f"PRICE DATA:\n"
            f"  Current Price: ${price:,.2f}\n"
            f"  Change 24H: {chg_24h:+.2f}%\n\n"
            f"MOMENTUM: {momentum}\n\n"
            f"Provide a complete commodity trade analysis. Return ONLY the JSON object."
        )

    # Crypto
    vol_str  = f"${vol_24h/1e6:.1f}M" if vol_24h else "N/A"
    mcap_str = f"${mcap/1e9:.2f}B"    if mcap    else "N/A"
    vol_mcap = (vol_24h / mcap * 100) if mcap > 0 else 0

    return (
        f"Analyze this coin for a spot trade:\n\n"
        f"COIN: {name} ({symbol})\n"
        f"CMC RANK: #{rank}\n"
        f"CATEGORY: {category.upper()}\n\n"
        f"PRICE DATA:\n"
        f"  Price: ${price}\n"
        f"  Change 1H: {chg_1h:+.2f}%\n"
        f"  Change 24H: {chg_24h:+.2f}%\n"
        f"  Change 7D: {chg_7d:+.2f}%\n"
        f"  Volume 24H: {vol_str}\n"
        f"  Market Cap: {mcap_str}\n"
        f"  Vol/MCap Ratio: {vol_mcap:.2f}%\n\n"
        f"MOMENTUM: {momentum}\n\n"
        f"Return ONLY the JSON object."
    )


def _enforce_leverage(raw_lev, meta, bull, rank, asset_type="crypto"):
    try:
        proposed = float(str(raw_lev).lower().replace("x", "").strip())
    except ValueError:
        proposed = 1.0

    if asset_type == "forex":
        cap = 20 if meta >= 75 else 10 if meta >= 55 else 5
    elif asset_type == "commodity":
        cap = 20 if meta >= 75 else 10 if meta >= 55 else 5
    else:
        rank_num = int(rank) if rank else 999
        if meta >= 80 and bull >= 65:   cap = 10
        elif meta >= 65 and bull >= 55: cap = 5
        elif meta >= 50:                cap = 3
        else:                           cap = 1
        if rank_num > 200: cap = min(cap, 2)
        if rank_num > 500: cap = 1

    final = max(1, min(proposed, cap))
    return f"{int(final)}x" if final == int(final) else f"{final}x"
