from app import db


class Coin(db.Model):
    __tablename__ = "coins"
    id                 = db.Column(db.Integer, primary_key=True)
    session_id         = db.Column(db.Integer, db.ForeignKey("scan_sessions.id"), nullable=True)
    cmc_id             = db.Column(db.Integer, nullable=True)
    symbol             = db.Column(db.String(20), nullable=False)
    name               = db.Column(db.String(100), nullable=False)
    cmc_rank           = db.Column(db.Integer, nullable=True)
    category           = db.Column(db.String(20), nullable=True)  # gainer|loser|search|forex|commodity
    price_usd          = db.Column(db.Float, nullable=False)
    market_cap         = db.Column(db.Float, nullable=True)
    volume_24h         = db.Column(db.Float, nullable=True)
    change_1h          = db.Column(db.Float, nullable=True)
    change_24h         = db.Column(db.Float, nullable=False)
    change_7d          = db.Column(db.Float, nullable=True)
    circulating_supply = db.Column(db.Float, nullable=True)
    max_supply         = db.Column(db.Float, nullable=True)
    predictions        = db.relationship("Prediction", backref="coin", lazy=True)

    def to_dict(self):
        return {
            "id": self.id, "session_id": self.session_id,
            "cmc_id": self.cmc_id, "symbol": self.symbol, "name": self.name,
            "cmc_rank": self.cmc_rank, "category": self.category,
            "price_usd": self.price_usd, "market_cap": self.market_cap,
            "volume_24h": self.volume_24h, "change_1h": self.change_1h,
            "change_24h": self.change_24h, "change_7d": self.change_7d,
        }
