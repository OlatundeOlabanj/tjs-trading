from flask import Blueprint, render_template, jsonify, redirect, url_for, flash, request
from flask_login import login_required
from app.services.ml_service import run_training, score_session, get_stats

ml_bp = Blueprint("ml", __name__)


@ml_bp.route("/stats")
@login_required
def stats_page():
    info = get_stats()
    return render_template("ml_stats.html", info=info)


@ml_bp.route("/train", methods=["POST"])
@login_required
def trigger_train():
    force  = request.form.get("force", "0") == "1"
    result = run_training(force=force)
    if result.get("ok"):
        flash(f"Model trained — {result['n_samples']} samples, {result['train_accuracy']:.1%} accuracy.", "success")
    else:
        flash(f"Training failed: {result.get('reason')}", "error")
    if request.headers.get("Accept") == "application/json":
        return jsonify(result)
    return redirect(url_for("ml.stats_page"))


@ml_bp.route("/score/<int:session_id>", methods=["POST"])
@login_required
def score_predictions(session_id: int):
    result = score_session(session_id)
    if request.headers.get("Accept") == "application/json":
        return jsonify(result)
    if result.get("ok"):
        flash(f"ML scored {result['scored']}/{result['total']} predictions.", "success")
    else:
        flash(f"Scoring failed: {result.get('reason')}", "error")
    return redirect(url_for("main.dashboard"))


@ml_bp.route("/api/stats")
@login_required
def api_stats():
    return jsonify(get_stats())
