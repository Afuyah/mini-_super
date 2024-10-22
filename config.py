# config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env file
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # Secret key for security
    SECRET_KEY = os.getenv('SECRET_KEY', 'you-will-never-guess')

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///mini_supermarket.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis configuration
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

    # Flask-SocketIO configurations
    SOCKETIO_MESSAGE_QUEUE = os.getenv('REDIS_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}')

