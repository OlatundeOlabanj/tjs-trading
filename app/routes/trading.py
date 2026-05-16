import logging
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app import db
from app.models import Trade
from app.models.api_key import ApiKey
from app.services.bybit_service import BybitService
from app.services.crypto_utils import decrypt

logger = logging.getLogger(__name__)
trading_bp = Blueprint("trading", __name__)


def _get_bybit(key_id: int) -> tuple:
    """Return (BybitService, ApiKey) or (None, None)."""
    key = ApiKey.query.filter_by(id=key_id, user_id=current_user.id, is_active=True).first()
    if not key: return None, None
    try:
        svc = BybitService(decrypt(key.api_key), decrypt(key.api_secret), is_live=key.is_live)
        return svc, key
    except Exception as e:
        logger.error(f"Bybit init error: {e}"); return None, None


@trading_bp.route("/")
@login_required
def trade_history():
    trades = (Trade.query.filter_by(user_id=current_user.id)
              .order_by(Trade.placed_at.desc()).limit(50).all())
    keys   = ApiKey.query.filter_by(user_id=current_user.id, is_active=True).all()
    return render_template("trading/history.html", trades=trades, keys=keys)


@trading_bp.route("/order", methods=["POST"])
@login_required
def place_order():
    data = request.json or {}
    key_id        = data.get("key_id")
    symbol        = data.get("symbol", "").strip()
    side          = data.get("side", "Buy")
    qty           = float(data.get("qty", 0))
    stop_loss     = data.get("stop_loss")
    take_profit   = data.get("take_profit")
    leverage      = int(data.get("leverage", 1))
    prediction_id = data.get("prediction_id")
    asset_type    = data.get("asset_type", "crypto")

    if not symbol or qty <= 0:
        return jsonify({"ok": False, "error": "Symbol and qty are required."}), 400

    # Log the trade intent regardless of exchange execution
    trade = Trade(
        user_id=current_user.id,
        prediction_id=prediction_id,
        symbol=symbol, side=side, qty=qty,
        stop_loss=float(stop_loss) if stop_loss else None,
        take_profit=float(take_profit) if take_profit else None,
        leverage=f"{leverage}x",
        asset_type=asset_type,
        status="LOGGED",
    )

    if key_id:
        svc, key = _get_bybit(int(key_id))
        if svc:
            result = svc.place_order(
                symbol=symbol, side=side, qty=qty,
                stop_loss=float(stop_loss) if stop_loss else None,
                take_profit=float(take_profit) if take_profit else None,
                leverage=leverage,
            )
            if result:
                trade.order_id   = result.get("orderId")
                trade.status     = "PLACED"
                trade.is_live    = key.is_live
                trade.exchange   = key.exchange
                trade.api_key_id = key.id
                key.last_used    = db.func.now()
            else:
                trade.status = "FAILED"
                db.session.add(trade)
                db.session.commit()
                return jsonify({"ok": False, "error": "Bybit rejected the order. Check symbol and account."}), 400

    db.session.add(trade)
    db.session.commit()
    return jsonify({"ok": True, "trade": trade.to_dict()})


@trading_bp.route("/balance")
@login_required
def get_balance():
    key_id = request.args.get("key_id", type=int)
    if not key_id:
        return jsonify({"ok": False, "error": "key_id required"}), 400
    svc, _ = _get_bybit(key_id)
    if not svc:
        return jsonify({"ok": False, "error": "Invalid or missing API key."}), 404
    balance = svc.get_wallet_balance()
    return jsonify({"ok": True, "balance": balance})


@trading_bp.route("/positions")
@login_required
def get_positions():
    key_id = request.args.get("key_id", type=int)
    if not key_id:
        return jsonify({"ok": False, "error": "key_id required"}), 400
    svc, _ = _get_bybit(key_id)
    if not svc:
        return jsonify({"ok": False, "error": "Invalid or missing API key."}), 404
    positions = svc.get_positions()
    return jsonify({"ok": True, "positions": positions})


@trading_bp.route("/order/<int:trade_id>/cancel", methods=["POST"])
@login_required
def cancel_order(trade_id: int):
    trade = Trade.query.filter_by(id=trade_id, user_id=current_user.id).first_or_404()
    if not trade.order_id:
        return jsonify({"ok": False, "error": "No exchange order ID on this trade."}), 400
    key = ApiKey.query.filter_by(id=trade.api_key_id, user_id=current_user.id).first()
    if not key:
        return jsonify({"ok": False, "error": "API key not found."}), 404
    svc, _ = _get_bybit(key.id)
    if svc and svc.cancel_order(trade.symbol, trade.order_id):
        trade.status = "CANCELLED"
        db.session.commit()
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Cancel failed."}), 400


@trading_bp.route("/api/history")
@login_required
def api_history():
    trades = (Trade.query.filter_by(user_id=current_user.id)
              .order_by(Trade.placed_at.desc()).limit(50).all())
    return jsonify([t.to_dict() for t in trades])
