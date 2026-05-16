import math
import numpy as np
from typing import Optional

FEATURE_NAMES = [
    "change_1h", "change_24h", "abs_change_24h", "change_7d",
    "volume_to_mcap_ratio", "log_volume_24h", "log_market_cap",
    "rank_bucket", "is_gainer", "sentiment_bullish", "sentiment_bearish",
    "sentiment_bull_bear_ratio", "meta_score", "profit_potential_min",
    "profit_potential_max", "profit_range", "risk_reward_ratio",
    "entry_to_price_pct", "leverage_numeric", "stop_distance_pct",
]
N_FEATURES = len(FEATURE_NAMES)


def _parse_leverage(lev_str):
    if not lev_str: return 1.0
    try: return float(str(lev_str).lower().replace("x","").strip())
    except: return 1.0


def _rank_bucket(rank):
    if rank is None: return 3
    if rank <= 10:   return 0
    if rank <= 50:   return 1
    if rank <= 200:  return 2
    return 3


def _log10(val):
    if not val or val <= 0: return 0.0
    return math.log10(val)


def extract_features(prediction, coin) -> Optional[np.ndarray]:
    if prediction is None: return None
    price     = float(coin.price_usd)    if coin and coin.price_usd    else 0.0
    change_1h = float(coin.change_1h)    if coin and coin.change_1h    else 0.0
    change_24h= float(coin.change_24h)   if coin and coin.change_24h   else 0.0
    change_7d = float(coin.change_7d)    if coin and coin.change_7d    else 0.0
    volume    = float(coin.volume_24h)   if coin and coin.volume_24h   else 0.0
    mcap      = float(coin.market_cap)   if coin and coin.market_cap   else 0.0
    rank      = int(coin.cmc_rank)       if coin and coin.cmc_rank     else None
    is_gainer = 1.0 if (coin and coin.category == "gainer") else 0.0
    vol_mcap  = (volume / mcap) if mcap > 0 else 0.0
    meta      = float(prediction.meta_score)           if prediction.meta_score           else 50.0
    bull      = float(prediction.sentiment_bullish)    if prediction.sentiment_bullish    else 50.0
    bear      = float(prediction.sentiment_bearish)    if prediction.sentiment_bearish    else 30.0
    prof_min  = float(prediction.profit_potential_min) if prediction.profit_potential_min else 20.0
    prof_max  = float(prediction.profit_potential_max) if prediction.profit_potential_max else 40.0
    entry_low = float(prediction.entry_low)    if prediction.entry_low    else price
    entry_high= float(prediction.entry_high)   if prediction.entry_high   else price
    target    = float(prediction.target_price) if prediction.target_price else price * 1.3
    stop      = float(prediction.stop_loss)    if prediction.stop_loss    else price * 0.95
    leverage  = _parse_leverage(prediction.recommended_leverage)
    entry_mid = (entry_low + entry_high) / 2 if entry_low and entry_high else price
    rr_den    = (entry_mid - stop) if (entry_mid - stop) > 0 else 1.0
    rr_ratio  = (target - entry_mid) / rr_den
    entry_pct = ((entry_mid - price) / price * 100) if price > 0 else 0.0
    stop_dist = ((price - stop) / price * 100)       if price > 0 else 5.0

    features = np.array([
        change_1h, change_24h, abs(change_24h), change_7d,
        vol_mcap, _log10(volume), _log10(mcap),
        float(_rank_bucket(rank)), is_gainer,
        bull, bear, bull / (bear + 1.0),
        meta, prof_min, prof_max, prof_max - prof_min,
        rr_ratio, entry_pct, leverage, stop_dist,
    ], dtype=np.float32)
    return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)


def build_dataset(predictions_with_outcomes):
    X_rows, y_rows, used_ids = [], [], []
    for pred, coin, outcome in predictions_with_outcomes:
        if outcome is None: continue
        if outcome.result not in ("hit_target","partial","stopped_out","missed"): continue
        feat = extract_features(pred, coin)
        if feat is None: continue
        label = 1 if outcome.result in ("hit_target","partial") else 0
        X_rows.append(feat)
        y_rows.append(label)
        used_ids.append(pred.id)
    if not X_rows: return None, None, []
    return np.array(X_rows, dtype=np.float32), np.array(y_rows, dtype=np.int32), used_ids
