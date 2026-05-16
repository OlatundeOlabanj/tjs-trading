import logging
from app import db

logger = logging.getLogger(__name__)


def run_training(force: bool = False) -> dict:
    from app.ml.trainer import train
    try: return train(force=force)
    except Exception as e:
        logger.exception("Training failed")
        return {"ok": False, "reason": str(e)}


def run_maybe_retrain() -> dict:
    from app.ml.trainer import maybe_retrain
    try: return maybe_retrain()
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def score_session(session_id: int) -> dict:
    from app.ml.predictor import score_session_predictions
    try: return score_session_predictions(session_id)
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def get_stats() -> dict:
    from app.ml.predictor import get_model_info
    from app.models import Outcome
    from sqlalchemy import func
    from app.ml.trainer import MIN_SAMPLES, RETRAIN_THRESHOLD, should_retrain

    info     = get_model_info()
    total    = Outcome.query.count()
    hits     = Outcome.query.filter_by(result="hit_target").count()
    partials = Outcome.query.filter_by(result="partial").count()
    stops    = Outcome.query.filter_by(result="stopped_out").count()
    missed   = Outcome.query.filter_by(result="missed").count()
    ongoing  = Outcome.query.filter_by(result="ongoing").count()
    avg_p    = db.session.query(func.avg(Outcome.actual_profit_pct)).scalar()
    wins     = hits + partials
    resolved = hits + partials + stops + missed

    info["outcome_stats"] = {
        "total": total, "resolved": resolved, "ongoing": ongoing,
        "hit_target": hits, "partial": partials,
        "stopped_out": stops, "missed": missed,
        "win_rate": round(wins / resolved * 100, 1) if resolved else 0,
        "avg_profit_pct": round(float(avg_p), 2) if avg_p else None,
    }
    info["min_samples"]       = MIN_SAMPLES
    info["retrain_threshold"] = RETRAIN_THRESHOLD
    info["needs_retrain"]     = should_retrain()
    return info
