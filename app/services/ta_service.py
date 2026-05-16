"""
Technical Analysis Service — pure numpy/pandas, zero extra dependencies.

Indicators computed:
  - RSI (14)
  - MACD (12/26/9 EMA)
  - Bollinger Bands (20 SMA ± 2σ)
  - EMA 20 and EMA 50
  - Volume trend (simple: last 3-day avg vs prior 3-day avg)
  - Support / Resistance (recent swing low / high over last 14 candles)

Each indicator returns a signal dict:
  {"value": ..., "signal": "bullish"|"bearish"|"neutral", "note": str}

Public API:
  run_ta(symbol: str) -> dict | None
    Returns the full TA result dict ready to JSON-serialize and store,
    or None if OHLCV data is unavailable.

  ta_summary_text(ta: dict) -> str
    Returns a compact one-line summary for injection into the AI prompt.
"""
import logging
import math
from typing import Optional

import numpy as np

from app.services.coingecko_service import fetch_ohlcv

logger = logging.getLogger(__name__)

# ── helpers ────────────────────────────────────────────────────────────────

def _ema(values: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    result = np.full_like(values, np.nan, dtype=np.float64)
    if len(values) < period:
        return result
    k = 2.0 / (period + 1)
    result[period - 1] = np.mean(values[:period])
    for i in range(period, len(values)):
        result[i] = values[i] * k + result[i - 1] * (1 - k)
    return result


def _sma(values: np.ndarray, period: int) -> np.ndarray:
    result = np.full_like(values, np.nan, dtype=np.float64)
    for i in range(period - 1, len(values)):
        result[i] = np.mean(values[i - period + 1 : i + 1])
    return result


# ── indicators ─────────────────────────────────────────────────────────────

def _calc_rsi(closes: np.ndarray, period: int = 14) -> dict:
    if len(closes) < period + 1:
        return {"value": None, "signal": "neutral", "note": "Not enough data"}
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs  = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1 + rs))
    rsi = round(rsi, 2)
    if rsi >= 70:
        signal, note = "bearish", f"RSI {rsi} — overbought territory"
    elif rsi <= 30:
        signal, note = "bullish", f"RSI {rsi} — oversold, potential bounce"
    else:
        signal, note = "neutral", f"RSI {rsi} — mid-range, no extreme"
    return {"value": rsi, "signal": signal, "note": note}


def _calc_macd(closes: np.ndarray) -> dict:
    if len(closes) < 35:
        return {"value": None, "histogram": None, "signal": "neutral", "note": "Not enough data"}
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line   = ema12 - ema26
    signal_line = _ema(macd_line[~np.isnan(macd_line)], 9)
    # Align: take last values
    valid_macd = macd_line[~np.isnan(macd_line)]
    if len(signal_line) < 2 or len(valid_macd) < 2:
        return {"value": None, "histogram": None, "signal": "neutral", "note": "Not enough data"}
    macd_val = round(float(valid_macd[-1]), 6)
    sig_val  = round(float(signal_line[-1]), 6)
    hist     = round(macd_val - sig_val, 6)
    prev_hist = round(float(valid_macd[-2]) - float(signal_line[-2]), 6)
    if hist > 0 and hist > prev_hist:
        signal, note = "bullish", f"MACD histogram expanding above zero ({hist:+.4f})"
    elif hist > 0:
        signal, note = "neutral", f"MACD positive but momentum slowing ({hist:+.4f})"
    elif hist < 0 and hist < prev_hist:
        signal, note = "bearish", f"MACD histogram expanding below zero ({hist:+.4f})"
    else:
        signal, note = "neutral", f"MACD negative but pressure easing ({hist:+.4f})"
    return {"value": macd_val, "histogram": hist, "signal": signal, "note": note}


def _calc_bollinger(closes: np.ndarray, period: int = 20) -> dict:
    if len(closes) < period:
        return {"upper": None, "middle": None, "lower": None,
                "bandwidth": None, "signal": "neutral", "note": "Not enough data"}
    sma    = _sma(closes, period)
    mid    = float(sma[-1])
    window = closes[-period:]
    std    = float(np.std(window, ddof=1))
    upper  = round(mid + 2 * std, 6)
    lower  = round(mid - 2 * std, 6)
    mid    = round(mid, 6)
    price  = float(closes[-1])
    bw     = round((upper - lower) / mid * 100, 2) if mid else 0
    if price >= upper:
        signal, note = "bearish", f"Price at upper band ${upper:.4f} — overbought"
    elif price <= lower:
        signal, note = "bullish", f"Price at lower band ${lower:.4f} — oversold / support"
    else:
        pos = (price - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
        if pos > 0.65:
            signal, note = "neutral", f"Price in upper half of bands ({pos:.0%})"
        else:
            signal, note = "neutral", f"Price in lower half of bands ({pos:.0%})"
    return {"upper": upper, "middle": mid, "lower": lower,
            "bandwidth": bw, "signal": signal, "note": note}


def _calc_ema_cross(closes: np.ndarray) -> dict:
    if len(closes) < 52:
        # try with what we have
        pass
    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    # Find last valid values
    v20 = next((x for x in reversed(ema20) if not math.isnan(x)), None)
    v50 = next((x for x in reversed(ema50) if not math.isnan(x)), None)
    if v20 is None or v50 is None:
        return {"ema20": None, "ema50": None, "signal": "neutral", "note": "Not enough data"}
    v20 = round(v20, 6)
    v50 = round(v50, 6)
    price = float(closes[-1])
    if v20 > v50:
        if price > v20:
            signal, note = "bullish", f"Price above EMA20 {v20:.4f} > EMA50 {v50:.4f} — bullish alignment"
        else:
            signal, note = "neutral", f"EMA20 {v20:.4f} > EMA50 {v50:.4f} but price below EMA20"
    else:
        if price < v20:
            signal, note = "bearish", f"Price below EMA20 {v20:.4f} < EMA50 {v50:.4f} — bearish alignment"
        else:
            signal, note = "neutral", f"EMA20 {v20:.4f} < EMA50 {v50:.4f} but price above EMA20"
    return {"ema20": v20, "ema50": v50, "signal": signal, "note": note}


def _calc_volume_trend(volumes: np.ndarray) -> dict:
    if len(volumes) < 6:
        return {"recent_avg": None, "prior_avg": None, "signal": "neutral", "note": "Not enough volume data"}
    recent = float(np.mean(volumes[-3:]))
    prior  = float(np.mean(volumes[-6:-3]))
    if prior == 0:
        return {"recent_avg": None, "prior_avg": None, "signal": "neutral", "note": "Volume data unavailable"}
    ratio = recent / prior
    recent_r = round(recent, 2)
    prior_r  = round(prior, 2)
    if ratio >= 1.3:
        signal, note = "bullish", f"Volume surging — recent avg {ratio:.1f}x prior average"
    elif ratio >= 1.05:
        signal, note = "neutral", f"Volume slightly elevated ({ratio:.2f}x prior)"
    elif ratio <= 0.7:
        signal, note = "bearish", f"Volume declining — recent avg {ratio:.1f}x prior average"
    else:
        signal, note = "neutral", f"Volume stable ({ratio:.2f}x prior)"
    return {"recent_avg": recent_r, "prior_avg": prior_r, "signal": signal, "note": note}


def _calc_support_resistance(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> dict:
    if len(highs) < 5:
        return {"support": None, "resistance": None, "signal": "neutral", "note": "Not enough data"}
    window = min(14, len(highs))
    resistance = round(float(np.max(highs[-window:])), 6)
    support    = round(float(np.min(lows[-window:])),  6)
    price      = float(closes[-1])
    rng        = resistance - support
    if rng == 0:
        return {"support": support, "resistance": resistance,
                "signal": "neutral", "note": "Price range too tight"}
    pos = (price - support) / rng
    if pos >= 0.8:
        signal, note = "bearish", f"Price near resistance ${resistance:.4f} ({pos:.0%} of range)"
    elif pos <= 0.2:
        signal, note = "bullish", f"Price near support ${support:.4f} ({pos:.0%} of range)"
    else:
        signal, note = "neutral", f"Price mid-range between S ${support:.4f} / R ${resistance:.4f}"
    return {"support": support, "resistance": resistance, "signal": signal, "note": note}


# ── scoring ────────────────────────────────────────────────────────────────

def _overall_signal(indicators: dict) -> dict:
    """Tally signals across all indicators and return overall bias + score."""
    weights = {
        "rsi": 2, "macd": 3, "bollinger": 2,
        "ema_cross": 2, "volume": 1, "support_resistance": 2,
    }
    bull = bear = neut = 0
    for key, w in weights.items():
        sig = indicators.get(key, {}).get("signal", "neutral")
        if sig == "bullish":   bull += w
        elif sig == "bearish": bear += w
        else:                  neut += w
    total = bull + bear + neut or 1
    bull_pct = round(bull / total * 100)
    bear_pct = round(bear / total * 100)
    if bull_pct >= 55:
        label = "bullish"
    elif bear_pct >= 55:
        label = "bearish"
    else:
        label = "neutral"
    return {
        "label": label,
        "bullish_pct": bull_pct,
        "bearish_pct": bear_pct,
        "neutral_pct": 100 - bull_pct - bear_pct,
    }


# ── public API ─────────────────────────────────────────────────────────────

def run_ta(symbol: str) -> Optional[dict]:
    """
    Compute full TA for a crypto symbol.
    Returns a JSON-serialisable dict or None if data unavailable.
    """
    candles = fetch_ohlcv(symbol)
    if len(candles) < 7:
        logger.info(f"TA skipped for {symbol} — only {len(candles)} candles")
        return None

    closes  = np.array([c["close"]  for c in candles], dtype=np.float64)
    highs   = np.array([c["high"]   for c in candles], dtype=np.float64)
    lows    = np.array([c["low"]    for c in candles], dtype=np.float64)
    volumes = np.array([c["volume"] for c in candles], dtype=np.float64)

    indicators = {
        "rsi":               _calc_rsi(closes),
        "macd":              _calc_macd(closes),
        "bollinger":         _calc_bollinger(closes),
        "ema_cross":         _calc_ema_cross(closes),
        "volume":            _calc_volume_trend(volumes),
        "support_resistance": _calc_support_resistance(highs, lows, closes),
    }
    overall = _overall_signal(indicators)

    return {
        "symbol":     symbol.upper(),
        "candle_count": len(candles),
        "overall":    overall,
        "indicators": indicators,
    }


def ta_summary_text(ta: dict) -> str:
    """
    Returns a compact text block for injecting into the AI prompt.
    Example:
      TECHNICAL ANALYSIS (14 candles):
      Overall: BULLISH (bull 60% / bear 20% / neutral 20%)
      RSI: neutral — RSI 52.3 — mid-range, no extreme
      MACD: bullish — histogram expanding above zero (+0.0023)
      ...
    """
    if not ta:
        return ""
    overall = ta.get("overall", {})
    lines = [
        f"TECHNICAL ANALYSIS ({ta.get('candle_count', '?')} daily candles):",
        f"Overall: {overall.get('label', '?').upper()} "
        f"(bull {overall.get('bullish_pct', 0)}% / "
        f"bear {overall.get('bearish_pct', 0)}% / "
        f"neutral {overall.get('neutral_pct', 0)}%)",
    ]
    for key in ("rsi", "macd", "bollinger", "ema_cross", "volume", "support_resistance"):
        ind = ta.get("indicators", {}).get(key, {})
        sig  = ind.get("signal", "?")
        note = ind.get("note", "")
        label = key.replace("_", " ").upper()
        lines.append(f"{label}: {sig} — {note}")
    return "\n".join(lines)
