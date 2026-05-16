from datetime import datetime, timezone
from app import db


class ApiKey(db.Model):
    __tablename__ = "api_keys"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    exchange   = db.Column(db.String(50), default="bybit")
    label      = db.Column(db.String(100), default="My Key")
    api_key    = db.Column(db.Text, nullable=False)    # Fernet encrypted
    api_secret = db.Column(db.Text, nullable=False)    # Fernet encrypted
    is_live    = db.Column(db.Boolean, default=False)
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_used  = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<ApiKey {self.exchange} live={self.is_live}>"
