import os
from dotenv import load_dotenv

load_dotenv()

_db_url = os.environ.get("DATABASE_URL", "sqlite:///shop.db")
# Strip ?ssl-mode=REQUIRED if copied directly from Aiven Service URI
if "?" in _db_url and "ssl-mode=" in _db_url:
    _db_url = _db_url.split("?")[0]
# Ensure SQLAlchemy uses PyMySQL driver
if _db_url.startswith("mysql://"):
    _db_url = _db_url.replace("mysql://", "mysql+pymysql://", 1)

_engine_options = {"pool_pre_ping": True}
if "aivencloud.com" in _db_url:
    _engine_options["connect_args"] = {"ssl": {"ssl_mode": "REQUIRED"}}

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///shop.db")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
    BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "")
    BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "The Style Club")
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")