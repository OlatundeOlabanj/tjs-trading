import os
import logging
import joblib
import numpy as np
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix
from app.ml.features import build_dataset, FEATURE_NAMES

logger = logging.getLogger(__name__)
MODEL_DIR  = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "rf_model.pkl")
META_PATH  = os.path.join(MODEL_DIR, "rf_meta.pkl")
MIN_SAMPLES       = 10
RETRAIN_THRESHOLD = 10


def model_exists() -> bool:
    return os.path.exists(MODEL_PATH)


def load_model():
    if not model_exists(): return None
    try: return joblib.load(MODEL_PATH)
    except Exception as e:
        logger.error(f"Load model error: {e}"); return None


def load_meta() -> dict:
    if not os.path.exists(META_PATH): return {}
    try: return joblib.load(META_PATH)
    except: return {}


def _save(model, meta):
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(meta, META_PATH)


def _fetch_training_rows():
    from app.models import Prediction, Coin, Outcome
    rows = (Prediction.query.join(Outcome, Outcome.prediction_id == Prediction.id)
            .filter(Outcome.result.in_(["hit_target","partial","stopped_out","missed"])).all())
    return [(p, Coin.query.get(p.coin_id), p.outcome) for p in rows]


def train(force: bool = False) -> dict:
    rows = _fetch_training_rows()
    if not rows: return {"ok": False, "reason": "No resolved outcomes yet."}
    X, y, used_ids = build_dataset(rows)
    if X is None: return {"ok": False, "reason": "Could not build feature vectors."}
    n, n_pos, n_neg = len(X), int(y.sum()), len(X) - int(y.sum())
    if n < MIN_SAMPLES and not force:
        return {"ok": False, "reason": f"Need {MIN_SAMPLES} samples. Have {n}.", "n_samples": n}
    if n_pos == 0 or n_neg == 0:
        return {"ok": False, "reason": "Need both wins and losses to train.", "n_samples": n}

    clf = RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=2,
                                  class_weight="balanced", random_state=42, n_jobs=-1)
    cv_scores = []
    if n >= 15:
        try:
            cv = StratifiedKFold(n_splits=min(5, n_pos, n_neg), shuffle=True, random_state=42)
            cv_scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy").tolist()
        except Exception as e:
            logger.warning(f"CV failed: {e}")

    clf.fit(X, y)
    y_pred = clf.predict(X)
    report = classification_report(y, y_pred, output_dict=True, zero_division=0)
    cm     = confusion_matrix(y, y_pred).tolist()
    fi     = sorted(zip(FEATURE_NAMES, clf.feature_importances_.tolist()), key=lambda x: x[1], reverse=True)

    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": n, "n_positive": n_pos, "n_negative": n_neg,
        "used_prediction_ids": used_ids,
        "train_accuracy": round(report.get("accuracy", 0.0), 4),
        "cv_scores": [round(s, 4) for s in cv_scores],
        "cv_mean": round(float(np.mean(cv_scores)), 4) if cv_scores else None,
        "cv_std":  round(float(np.std(cv_scores)),  4) if cv_scores else None,
        "confusion_matrix": cm,
        "classification_report": report,
        "feature_importances": fi,
    }
    _save(clf, meta)
    return {"ok": True, **meta}


def should_retrain() -> bool:
    meta = load_meta()
    if not meta: return True
    last_ids = set(meta.get("used_prediction_ids", []))
    from app.models import Outcome
    current = {o.prediction_id for o in Outcome.query.filter(
        Outcome.result.in_(["hit_target","partial","stopped_out","missed"])).all()}
    return len(current - last_ids) >= RETRAIN_THRESHOLD


def maybe_retrain() -> dict:
    if should_retrain():
        return train()
    return {"ok": False, "reason": "Retrain threshold not reached."}
