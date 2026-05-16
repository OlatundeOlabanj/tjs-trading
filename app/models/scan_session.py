from datetime import datetime, timezone
from app import db


class ScanSession(db.Model):
    __tablename__ = "scan_sessions"
    id               = db.Column(db.Integer, primary_key=True)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status           = db.Column(db.String(20), default="pending")
    error_message    = db.Column(db.Text, nullable=True)
    btc_dominance    = db.Column(db.Float, nullable=True)
    total_market_cap = db.Column(db.Float, nullable=True)
    total_volume_24h = db.Column(db.Float, nullable=True)
    coins            = db.relationship("Coin", backref="session", lazy=True, cascade="all, delete-orphan")
    predictions      = db.relationship("Prediction", backref="session", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "btc_dominance": self.btc_dominance,
            "total_market_cap": self.total_market_cap,
            "total_volume_24h": self.total_volume_24h,
            "coin_count": len(self.coins),
        }
