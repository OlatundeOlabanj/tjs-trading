from flask import Blueprint, jsonify
from flask_login import login_required
from app.models import ScanSession, Coin, Prediction, Trade
from app import db

api_bp = Blueprint("api", __name__)


@api_bp.route("/status")
@login_required
def status():
    last = ScanSession.query.order_by(ScanSession.created_at.desc()).first()
    return jsonify({
        "ok": True,
        "total_sessions":    ScanSession.query.count(),
        "total_coins":       Coin.query.count(),
        "total_predictions": Prediction.query.count(),
        "last_scan": last.to_dict() if last else None,
    })


@api_bp.route("/coins/latest")
@login_required
def latest_coins():
    last = (ScanSession.query
            .filter(ScanSession.status.in_(["complete", "coins_ready"]))
            .order_by(ScanSession.created_at.desc()).first())
    if not last:
        return jsonify({"ok": False, "error": "No scans yet"}), 404
    return jsonify({
        "ok": True, "session": last.to_dict(),
        "gainers": [c.to_dict() for c in last.coins if c.category == "gainer"],
        "losers":  [c.to_dict() for c in last.coins if c.category == "loser"],
    })
