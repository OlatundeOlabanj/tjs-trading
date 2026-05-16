from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app.models import Prediction, Coin

predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.route("/")
@login_required
def list_predictions():
    preds = (Prediction.query.order_by(Prediction.created_at.desc()).limit(100).all())
    return render_template("predictions.html", predictions=preds)


@predictions_bp.route("/<int:pred_id>")
@login_required
def prediction_detail(pred_id: int):
    pred = Prediction.query.get_or_404(pred_id)
    coin = Coin.query.get(pred.coin_id)
    return render_template("prediction_detail.html", pred=pred, coin=coin)


@predictions_bp.route("/api/list")
@login_required
def api_list():
    preds = Prediction.query.order_by(Prediction.created_at.desc()).limit(50).all()
    out = []
    for p in preds:
        d = p.to_dict()
        coin = Coin.query.get(p.coin_id)
        if coin:
            d.update({"symbol": coin.symbol, "name": coin.name,
                      "price_usd": coin.price_usd, "change_24h": coin.change_24h,
                      "category": coin.category})
        out.append(d)
    return jsonify(out)
