import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env file
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # Secret key for security
    SECRET_KEY = os.getenv('SECRET_KEY', 'you-will-never-guess')

    # Database configuration
    SQLALCHEMY_DATABASE_URI ='sqlite:///sale.db' #'postgresql://postgres:WakpFCEZjrKOmisavwiSjjbVLSuqqjQB@junction.proxy.rlwy.net:40841/railway'  # Replace this with os.getenv for flexibility if needed
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-SocketIO configurations (removed Redis-related message queue)
    SOCKETIO_MESSAGE_QUEUE = None
