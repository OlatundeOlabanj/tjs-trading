import logging
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from app import db
from app.models import Coin, Prediction
from app.services.cmc_service import CMCService
from app.services.frankfurter_service import FrankfurterService
from app.services.analysis_service import AnalysisService
from app.services.ta_service import run_ta, ta_summary_text

logger = logging.getLogger(__name__)
search_bp = Blueprint("search", __name__)


@search_bp.route("/coin", methods=["POST"])
@login_required
def search_coin():
    query = (request.json or {}).get("query", "").strip()
    if not query:
        return jsonify({"ok": False, "error": "Query is required."}), 400

    api_key = current_app.config.get("GROQ_API_KEY", "")
    if not api_key:
        return jsonify({"ok": False, "error": "GROQ_API_KEY not configured."}), 500

    # Try CMC first
    coin_data = None
    source = "crypto"
    try:
        cmc = CMCService()
        coin_data = cmc.search_coin(query)
    except Exception as e:
        logger.warning(f"CMC search failed for '{query}': {e}")

    # Fall back to Frankfurter for FX/commodities
    if not coin_data:
        try:
            fx = FrankfurterService()
            coin_data = fx.resolve(query)
            if coin_data:
                source = coin_data.get("category", "forex")
        except Exception as e:
            logger.warning(f"Frankfurter search failed for '{query}': {e}")

    if not coin_data:
        return jsonify({"ok": False, "error": f"Could not find '{query}'. Try a symbol like BTC, EURUSD, or Gold."}), 404

    # Persist coin (no session_id for searches)
    coin = Coin(
        session_id=None,
        cmc_id=coin_data.get("cmc_id"),
        symbol=coin_data.get("symbol", query.upper()),
        name=coin_data.get("name", query),
        cmc_rank=coin_data.get("cmc_rank"),
        category=coin_data.get("category", "search"),
        price_usd=coin_data.get("price_usd", 0.0),
        market_cap=coin_data.get("market_cap"),
        volume_24h=coin_data.get("volume_24h"),
        change_1h=coin_data.get("change_1h"),
        change_24h=coin_data.get("change_24h", 0.0),
        change_7d=coin_data.get("change_7d"),
    )
    db.session.add(coin)
    db.session.commit()
    db.session.refresh(coin)

    # Run TA for crypto assets (best-effort — never blocks)
    ta_result = None
    ta_text   = None
    asset_cat = coin_data.get("category", "search")
    if asset_cat not in ("forex", "commodity"):
        try:
            ta_result = run_ta(coin.symbol)
            if ta_result:
                ta_text = ta_summary_text(ta_result)
        except Exception as e:
            logger.warning(f"TA failed for '{query}': {e}")

    # Run AI analysis
    try:
        svc    = AnalysisService(api_key)
        result = svc.analyze_coin(coin.to_dict(), ta_text=ta_text)
    except Exception as e:
        logger.error(f"Analysis error for '{query}': {e}")
        result = None

    if not result:
        return jsonify({"ok": False, "error": "AI analysis failed. Try again."}), 500

    # Persist prediction
    import json as _json
    pred = Prediction(
        session_id=None, coin_id=coin.id,
        sentiment_bullish=result.get("sentiment_bullish"),
        sentiment_bearish=result.get("sentiment_bearish"),
        sentiment_neutral=result.get("sentiment_neutral"),
        sentiment_label=result.get("sentiment_label"),
        meta_score=result.get("meta_score"),
        profit_potential_min=result.get("profit_potential_min"),
        profit_potential_max=result.get("profit_potential_max"),
        entry_low=result.get("entry_low"),
        entry_high=result.get("entry_high"),
        target_price=result.get("target_price"),
        stop_loss=result.get("stop_loss"),
        recommended_leverage=result.get("recommended_leverage"),
        leverage_note=result.get("leverage_note"),
        verdict=result.get("verdict"),
        summary=result.get("summary"),
        ta_data=_json.dumps(ta_result) if ta_result else None,
    )
    db.session.add(pred)
    db.session.commit()

    return jsonify({
        "ok":   True,
        "source": source,
        "coin": coin.to_dict(),
        "prediction": {**pred.to_dict(), **result},
        "prediction_id": pred.id,
    })
