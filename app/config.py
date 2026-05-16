import os
from dotenv import load_dotenv
load_dotenv()

class BaseConfig:
    SECRET_KEY               = os.environ.get("SECRET_KEY", "dev-secret")
    MASTER_KEY               = os.environ.get("MASTER_KEY", "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CMC_API_KEY              = os.environ.get("CMC_API_KEY", "")
    CMC_CACHE_SECONDS        = int(os.environ.get("CMC_CACHE_SECONDS", 120))
    SCAN_LIMIT               = int(os.environ.get("SCAN_LIMIT", 10))
    MARKET_CAP_MIN           = int(os.environ.get("MARKET_CAP_MIN", 50_000_000))
    GROQ_API_KEY             = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL               = "llama-3.3-70b-versatile"
    AUTO_SCAN_ENABLED        = os.environ.get("AUTO_SCAN_ENABLED", "true").lower() == "true"
    AUTO_SCAN_INTERVAL_HOURS = int(os.environ.get("AUTO_SCAN_INTERVAL_HOURS", 6))

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tjs_trading_dev.db")

class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tjs_trading.db")

config_map = {"development": DevelopmentConfig, "production": ProductionConfig}

def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
