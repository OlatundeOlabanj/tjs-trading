from app.routes.auth import auth_bp
from app.routes.main import main_bp
from app.routes.scan import scan_bp
from app.routes.search import search_bp
from app.routes.predictions import predictions_bp
from app.routes.outcomes import outcomes_bp
from app.routes.trading import trading_bp
from app.routes.ml import ml_bp
from app.routes.api import api_bp

__all__ = [
    "auth_bp", "main_bp", "scan_bp", "search_bp",
    "predictions_bp", "outcomes_bp", "trading_bp", "ml_bp", "api_bp",
]
