import json
from datetime import datetime, timezone
from app import db


class Prediction(db.Model):
    __tablename__ = "predictions"
    id                   = db.Column(db.Integer, primary_key=True)
    session_id           = db.Column(db.Integer, db.ForeignKey("scan_sessions.id"), nullable=True)
    coin_id              = db.Column(db.Integer, db.ForeignKey("coins.id"), nullable=False)
    created_at           = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    sentiment_bullish    = db.Column(db.Float, nullable=True)
    sentiment_bearish    = db.Column(db.Float, nullable=True)
    sentiment_neutral    = db.Column(db.Float, nullable=True)
    sentiment_label      = db.Column(db.String(20), nullable=True)
    meta_score           = db.Column(db.Float, nullable=True)
    profit_potential_min = db.Column(db.Float, nullable=True)
    profit_potential_max = db.Column(db.Float, nullable=True)
    entry_low            = db.Column(db.Float, nullable=True)
    entry_high           = db.Column(db.Float, nullable=True)
    target_price         = db.Column(db.Float, nullable=True)
    stop_loss            = db.Column(db.Float, nullable=True)
    recommended_leverage = db.Column(db.String(10), nullable=True)
    leverage_note        = db.Column(db.String(200), nullable=True)
    verdict              = db.Column(db.String(20), nullable=True)
    summary              = db.Column(db.Text, nullable=True)
    ml_confidence        = db.Column(db.Float, nullable=True)
    ta_data              = db.Column(db.Text, nullable=True)   # JSON blob from ta_service

    @property
    def ta(self):
        """Parsed TA dict, or None if not available."""
        if not self.ta_data:
            return None
        try:
            return json.loads(self.ta_data)
        except Exception:
            return None
    outcome              = db.relationship("Outcome", backref="prediction", uselist=False, cascade="all, delete-orphan")
    trades               = db.relationship("Trade", backref="prediction", lazy=True)

    def to_dict(self):
        return {
            "id": self.id, "session_id": self.session_id, "coin_id": self.coin_id,
            "created_at": self.created_at.isoformat(),
            "sentiment_bullish": self.sentiment_bullish,
            "sentiment_bearish": self.sentiment_bearish,
            "sentiment_neutral": self.sentiment_neutral,
            "sentiment_label": self.sentiment_label,
            "meta_score": self.meta_score,
            "profit_potential_min": self.profit_potential_min,
            "profit_potential_max": self.profit_potential_max,
            "entry_low": self.entry_low,
            "entry_high": self.entry_high,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "recommended_leverage": self.recommended_leverage,
            "leverage_note": self.leverage_note,
            "verdict": self.verdict,
            "summary": self.summary,
            "ml_confidence": self.ml_confidence,
        }
