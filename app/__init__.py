from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

from app.config import get_config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login_page"

    # Import models for Migrate
    from app.models import user, api_key, trade, scan_session, coin, prediction, outcome  # noqa

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.scan import scan_bp
    from app.routes.search import search_bp
    from app.routes.predictions import predictions_bp
    from app.routes.outcomes import outcomes_bp
    from app.routes.trading import trading_bp
    from app.routes.ml import ml_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(scan_bp,         url_prefix="/scan")
    app.register_blueprint(search_bp,       url_prefix="/search")
    app.register_blueprint(predictions_bp,  url_prefix="/predictions")
    app.register_blueprint(outcomes_bp,     url_prefix="/outcomes")
    app.register_blueprint(trading_bp,      url_prefix="/trading")
    app.register_blueprint(ml_bp,           url_prefix="/ml")
    app.register_blueprint(api_bp,          url_prefix="/api")

    from app.models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Jinja2 filters ──────────────────────────────────────────
    @app.template_filter("format_price")
    def format_price_filter(val):
        if val is None: return "--"
        try: n = float(val)
        except: return str(val)
        if n >= 1000: return f"{n:,.2f}"
        if n >= 1:    return f"{n:.4f}"
        if n >= 0.01: return f"{n:.5f}"
        return f"{n:.8f}"

    @app.template_filter("pct")
    def pct_filter(val):
        if val is None: return "--"
        try: return f"{float(val):.1%}"
        except: return str(val)

    @app.template_filter("fmt_mcap")
    def fmt_mcap(val):
        if not val: return "--"
        v = float(val)
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9:  return f"${v/1e9:.2f}B"
        if v >= 1e6:  return f"${v/1e6:.1f}M"
        return f"${v:,.0f}"

    # Init scheduler
    if not app.config.get("TESTING"):
        import os
        if os.environ.get("WERKZEUG_RUN_MAIN") != "false":
            try:
                from app.scheduler import init_scheduler
                init_scheduler(app)
            except Exception as e:
                app.logger.warning(f"Scheduler init skipped: {e}")

    return app
