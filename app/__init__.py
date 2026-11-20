from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to access your bag and wishlist."
login_manager.login_message_category = "error"

csrf = CSRFProtect()
migrate = Migrate()
oauth = OAuth()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    oauth.init_app(app)

    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    @app.template_filter("peso")
    def peso(cents):
        return f"₱{(cents or 0) / 100:,.0f}"

    from app import models
    from app.routes.auth import auth
    from app.routes.shop import shop
    from app.routes.cart import cart
    from app.routes.wishlist import wishlist
    from app.routes.checkout import checkout

    app.register_blueprint(auth)
    app.register_blueprint(shop)
    app.register_blueprint(cart)
    app.register_blueprint(wishlist)
    app.register_blueprint(checkout)

    return app