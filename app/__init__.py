# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
import redis
import logging
from logging.handlers import RotatingFileHandler

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize logging
    if not app.debug:
        handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.info('Application startup')

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", message_queue=app.config['SOCKETIO_MESSAGE_QUEUE'])
    login_manager.init_app(app)
    limiter.init_app(app)

    # Initialize Redis client
    try:
        redis_client = redis.Redis(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            password=app.config['REDIS_PASSWORD'],
            decode_responses=True
        )
        app.logger.info('Connected to Redis')
    except redis.ConnectionError:
        app.logger.error("Could not connect to Redis")

    # Configure Flask-Limiter to use Redis
    limiter.storage_uri = f"redis://:{app.config['REDIS_PASSWORD']}@{app.config['REDIS_HOST']}:{app.config['REDIS_PORT']}/0"

    # Register Blueprints
    from .auth import auth_bp
    from .stock import stock_bp
    from .sales import sales_bp
    from .home import home_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(stock_bp, url_prefix='/stock')
    app.register_blueprint(sales_bp, url_prefix='/sales')

    # User loader for Flask-Login
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Error handling
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Server Error: {error}")
        return "Internal Server Error", 500
    @app.template_filter('number_format')
    def number_format(value, decimals=2):
        return f"{value:,.{decimals}f}"    
    return app
