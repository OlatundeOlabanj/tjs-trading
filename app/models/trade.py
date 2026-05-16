from datetime import datetime, timezone
from app import db


class Trade(db.Model):
    __tablename__ = "trades"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    api_key_id    = db.Column(db.Integer, db.ForeignKey("api_keys.id"), nullable=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id"), nullable=True)
    symbol        = db.Column(db.String(30), nullable=False)
    side          = db.Column(db.String(10), nullable=False)    # Buy | Sell
    order_type    = db.Column(db.String(20), default="Market")
    qty           = db.Column(db.Float, nullable=False)
    entry_price   = db.Column(db.Float, nullable=True)
    stop_loss     = db.Column(db.Float, nullable=True)
    take_profit   = db.Column(db.Float, nullable=True)
    leverage      = db.Column(db.String(10), nullable=True)
    order_id      = db.Column(db.String(100), nullable=True)
    status        = db.Column(db.String(30), default="PLACED")
    is_live       = db.Column(db.Boolean, default=False)
    exchange      = db.Column(db.String(30), default="bybit")
    close_price   = db.Column(db.Float, nullable=True)
    pnl           = db.Column(db.Float, nullable=True)
    pnl_pct       = db.Column(db.Float, nullable=True)
    asset_type    = db.Column(db.String(20), default="crypto")  # crypto|forex|commodity
    notes         = db.Column(db.Text, nullable=True)
    placed_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id, "symbol": self.symbol, "side": self.side,
            "order_type": self.order_type, "qty": self.qty,
            "entry_price": self.entry_price, "stop_loss": self.stop_loss,
            "take_profit": self.take_profit, "leverage": self.leverage,
            "order_id": self.order_id, "status": self.status,
            "is_live": self.is_live, "exchange": self.exchange,
            "close_price": self.close_price, "pnl": self.pnl,
            "pnl_pct": self.pnl_pct, "asset_type": self.asset_type,
            "prediction_id": self.prediction_id, "notes": self.notes,
            "placed_at": self.placed_at.isoformat() if self.placed_at else None,
        }
