from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import Prediction, Outcome, Coin
from app.models.outcome import OUTCOME_RESULTS

outcomes_bp = Blueprint("outcomes", __name__)


@outcomes_bp.route("/")
@login_required
def list_outcomes():
    pending  = (Prediction.query.filter(~Prediction.outcome.has())
                .order_by(Prediction.created_at.desc()).limit(50).all())
    resolved = (Prediction.query.filter(Prediction.outcome.has())
                .order_by(Prediction.created_at.desc()).limit(50).all())
    return render_template("outcomes.html", pending=pending, resolved=resolved)


@outcomes_bp.route("/mark/<int:pred_id>", methods=["POST"])
@login_required
def mark_outcome(pred_id: int):
    pred    = Prediction.query.get_or_404(pred_id)
    is_json = request.is_json
    data    = request.json if is_json else request.form
    result  = data.get("result")

    if result not in OUTCOME_RESULTS:
        msg = f"Invalid result. Use: {OUTCOME_RESULTS}"
        if is_json: return jsonify({"ok": False, "error": msg}), 400
        flash(msg, "error"); return redirect(url_for("outcomes.list_outcomes"))

    outcome = pred.outcome or Outcome(prediction_id=pred_id)
    if not outcome.id: db.session.add(outcome)
    outcome.result            = result
    outcome.actual_profit_pct = float(data.get("actual_profit_pct")) if data.get("actual_profit_pct") else None
    outcome.exit_price        = float(data.get("exit_price"))        if data.get("exit_price")        else None
    outcome.hours_to_outcome  = float(data.get("hours_to_outcome"))  if data.get("hours_to_outcome")  else None
    outcome.notes             = data.get("notes", "")
    db.session.commit()

    retrain_result = {"ok": False}
    if result != "ongoing":
        try:
            from app.services.ml_service import run_maybe_retrain
            retrain_result = run_maybe_retrain()
        except Exception: pass

    if is_json:
        return jsonify({"ok": True, "outcome_id": outcome.id, "retrain": retrain_result})

    if retrain_result.get("ok"):
        flash(f"Outcome saved + model retrained ({retrain_result.get('train_accuracy',0):.1%} accuracy).", "success")
    else:
        flash(f"Outcome recorded: {result}.", "success")
    return redirect(url_for("outcomes.list_outcomes"))
