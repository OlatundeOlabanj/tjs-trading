import json
import logging
from flask import Blueprint, jsonify, Response, stream_with_context, current_app
from flask_login import login_required
from app import db
from app.models import ScanSession, Coin, Prediction
from app.services.cmc_service import CMCService
from app.services.analysis_service import AnalysisService
from app.services.ta_service import run_ta, ta_summary_text

logger = logging.getLogger(__name__)
scan_bp = Blueprint("scan", __name__)


@scan_bp.route("/run", methods=["POST"])
@login_required
def run_scan():
    session = ScanSession(status="pending")
    db.session.add(session)
    db.session.commit()
    try:
        svc  = CMCService()
        data = svc.run_scan()
        g = data.get("global", {})
        session.btc_dominance    = g.get("btc_dominance")
        session.total_market_cap = g.get("total_market_cap")
        session.total_volume_24h = g.get("total_volume_24h")
        for raw in data.get("gainers", []):
            db.session.add(_make_coin(session.id, raw, "gainer"))
        for raw in data.get("losers", []):
            db.session.add(_make_coin(session.id, raw, "loser"))
        session.status = "coins_ready"
        db.session.commit()
        db.session.refresh(session)
        coins_out = [c.to_dict() for c in session.coins]
        return jsonify({
            "ok": True, "session_id": session.id,
            "global":  data.get("global", {}),
            "gainers": [c for c in coins_out if c["category"] == "gainer"],
            "losers":  [c for c in coins_out if c["category"] == "loser"],
        })
    except RuntimeError as e:
        session.status = "failed"; session.error_message = str(e)
        db.session.commit()
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("Scan failed")
        session.status = "failed"; session.error_message = str(e)
        db.session.commit()
        return jsonify({"ok": False, "error": "Scan failed. Check server logs."}), 500


@scan_bp.route("/stream/<int:session_id>")
@login_required
def stream_analysis(session_id: int):
    session = ScanSession.query.get_or_404(session_id)
    api_key = current_app.config.get("GROQ_API_KEY", "")

    def generate():
        def evt(payload): return f"data: {json.dumps(payload)}\n\n"

        if not api_key:
            yield evt({"type": "error", "message": "GROQ_API_KEY not configured."})
            return

        coins = Coin.query.filter_by(session_id=session_id).all()
        if not coins:
            yield evt({"type": "error", "message": "No coins for this session."})
            return

        total = len(coins)
        yield evt({"type": "start", "total": total, "session_id": session_id})

        try:
            svc = AnalysisService(api_key)
        except RuntimeError as e:
            yield evt({"type": "error", "message": str(e)}); return

        completed = errors = 0
        for coin in coins:
            yield evt({"type": "analyzing", "symbol": coin.symbol, "name": coin.name,
                        "current": completed + 1, "total": total})

            # Fetch TA for crypto coins (best-effort — never blocks the scan)
            ta_result  = None
            ta_text    = None
            if coin.category in ("gainer", "loser", "search"):
                try:
                    ta_result = run_ta(coin.symbol)
                    if ta_result:
                        ta_text = ta_summary_text(ta_result)
                        yield evt({"type": "ta_ready", "symbol": coin.symbol,
                                   "ta_overall": ta_result.get("overall", {})})
                except Exception:
                    pass  # TA failure must never kill the scan

            result = svc.analyze_coin(coin.to_dict(), ta_text=ta_text)
            if result is None:
                errors += 1
                yield evt({"type": "coin_error", "symbol": coin.symbol, "message": "Analysis failed."})
                continue

            pred = _make_prediction(session_id, coin.id, result, ta_result)
            db.session.add(pred)
            db.session.commit()
            db.session.refresh(pred)

            ml_confidence = None
            try:
                from app.ml.predictor import predict_confidence
                ml_confidence = predict_confidence(pred, coin)
                if ml_confidence is not None:
                    pred.ml_confidence = ml_confidence
                    db.session.commit()
            except Exception: pass

            completed += 1
            yield evt({"type": "prediction", "prediction_id": pred.id,
                        "coin_id": coin.id, "ml_confidence": ml_confidence, **result})

        session.status = "complete"
        db.session.commit()
        yield evt({"type": "done", "session_id": session_id,
                    "completed": completed, "errors": errors, "total": total})

    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@scan_bp.route("/sessions")
@login_required
def list_sessions():
    sessions = ScanSession.query.order_by(ScanSession.created_at.desc()).limit(20).all()
    return jsonify([s.to_dict() for s in sessions])


def _make_coin(session_id, raw, category):
    return Coin(session_id=session_id, cmc_id=raw.get("cmc_id"),
                symbol=raw.get("symbol",""), name=raw.get("name",""),
                cmc_rank=raw.get("cmc_rank"), category=category,
                price_usd=raw.get("price_usd",0.0), market_cap=raw.get("market_cap"),
                volume_24h=raw.get("volume_24h"), change_1h=raw.get("change_1h"),
                change_24h=raw.get("change_24h",0.0), change_7d=raw.get("change_7d"),
                circulating_supply=raw.get("circulating_supply"), max_supply=raw.get("max_supply"))


def _make_prediction(session_id, coin_id, r, ta_result=None):
    import json as _json
    return Prediction(session_id=session_id, coin_id=coin_id,
                      sentiment_bullish=r.get("sentiment_bullish"),
                      sentiment_bearish=r.get("sentiment_bearish"),
                      sentiment_neutral=r.get("sentiment_neutral"),
                      sentiment_label=r.get("sentiment_label"),
                      meta_score=r.get("meta_score"),
                      profit_potential_min=r.get("profit_potential_min"),
                      profit_potential_max=r.get("profit_potential_max"),
                      entry_low=r.get("entry_low"), entry_high=r.get("entry_high"),
                      target_price=r.get("target_price"), stop_loss=r.get("stop_loss"),
                      recommended_leverage=r.get("recommended_leverage"),
                      leverage_note=r.get("leverage_note"),
                      verdict=r.get("verdict"), summary=r.get("summary"),
                      ta_data=_json.dumps(ta_result) if ta_result else None)
