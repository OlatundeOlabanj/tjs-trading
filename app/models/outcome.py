from datetime import datetime, timezone
from app import db

OUTCOME_RESULTS = ("hit_target", "stopped_out", "ongoing", "missed", "partial")


class Outcome(db.Model):
    __tablename__ = "outcomes"
    id                = db.Column(db.Integer, primary_key=True)
    prediction_id     = db.Column(db.Integer, db.ForeignKey("predictions.id"), nullable=False, unique=True)
    recorded_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    result            = db.Column(db.String(20), nullable=False)
    actual_profit_pct = db.Column(db.Float, nullable=True)
    exit_price        = db.Column(db.Float, nullable=True)
    hours_to_outcome  = db.Column(db.Float, nullable=True)
    notes             = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "prediction_id": self.prediction_id,
            "recorded_at": self.recorded_at.isoformat(),
            "result": self.result,
            "actual_profit_pct": self.actual_profit_pct,
            "exit_price": self.exit_price,
            "hours_to_outcome": self.hours_to_outcome,
        }
