from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import ScanSession, Prediction, Trade

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def dashboard():
    recent_sessions = (
        ScanSession.query
        .order_by(ScanSession.created_at.desc())
        .limit(5).all()
    )
    last_session = recent_sessions[0] if recent_sessions else None
    gainers, losers, predictions = [], [], []

    if last_session:
        gainers     = [c for c in last_session.coins if c.category == "gainer"]
        losers      = [c for c in last_session.coins if c.category == "loser"]
        predictions = last_session.predictions

    recent_trades = (
        Trade.query
        .filter_by(user_id=current_user.id)
        .order_by(Trade.placed_at.desc())
        .limit(5).all()
    )

    total_predictions = Prediction.query.count()
    total_trades      = Trade.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "dashboard.html",
        last_session=last_session,
        gainers=gainers,
        losers=losers,
        predictions=predictions,
        recent_sessions=recent_sessions,
        recent_trades=recent_trades,
        total_predictions=total_predictions,
        total_trades=total_trades,
    )
