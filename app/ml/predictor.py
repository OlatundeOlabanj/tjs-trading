import logging
import numpy as np
from typing import Optional
from app.ml.features import extract_features
from app.ml.trainer import load_model, load_meta, model_exists

logger = logging.getLogger(__name__)


def predict_confidence(prediction, coin) -> Optional[float]:
    if not model_exists(): return None
    clf = load_model()
    if clf is None: return None
    feat = extract_features(prediction, coin)
    if feat is None: return None
    try:
        proba = clf.predict_proba(feat.reshape(1, -1))[0]
        return round(float(proba[1]), 4)
    except Exception as e:
        logger.error(f"Scoring error: {e}"); return None


def score_session_predictions(session_id: int) -> dict:
    from app import db
    from app.models import Prediction, Coin
    if not model_exists():
        return {"ok": False, "reason": "No trained model. Mark some outcomes first."}
    preds = Prediction.query.filter_by(session_id=session_id).all()
    if not preds: return {"ok": False, "reason": "No predictions for this session."}
    scored = 0
    for pred in preds:
        coin = Coin.query.get(pred.coin_id)
        conf = predict_confidence(pred, coin)
        if conf is not None:
            pred.ml_confidence = conf
            scored += 1
    db.session.commit()
    return {"ok": True, "scored": scored, "total": len(preds)}


def get_model_info() -> dict:
    if not model_exists(): return {"ready": False}
    meta = load_meta()
    return {
        "ready": True,
        "trained_at":          meta.get("trained_at"),
        "n_samples":           meta.get("n_samples", 0),
        "n_positive":          meta.get("n_positive", 0),
        "n_negative":          meta.get("n_negative", 0),
        "train_accuracy":      meta.get("train_accuracy"),
        "cv_mean":             meta.get("cv_mean"),
        "cv_std":              meta.get("cv_std"),
        "cv_scores":           meta.get("cv_scores", []),
        "confusion_matrix":    meta.get("confusion_matrix"),
        "feature_importances": meta.get("feature_importances", []),
    }
