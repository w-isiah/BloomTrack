import os
import random
import string
import logging



# Set up logging configuration for production and development
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Config:
    """Base configuration class."""
    basedir = os.path.abspath(os.path.dirname(__file__))

    # Asset management configuration
    ASSETS_ROOT = os.getenv('ASSETS_ROOT', '/static/assets')

    # Upload configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads')  # Path to the upload folder
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # Default secret key for Flask, falls back to a generated key if not set
    SECRET_KEY = os.getenv('SECRET_KEY') or ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))

    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'pos_db')
    DB_PORT = int(os.getenv('DB_PORT', 3306))  # Default to 3306 if not provided

    @staticmethod
    def init_app(app):
        """Initialize the app with the configuration."""
        app.config.from_object(Config)

        # Ensure the upload folder exists
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])


class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600  # 1 hour duration for "remember me" cookies

class DebugConfig(Config):
    """Debug-specific configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Log SQL queries during development

config_dict = {
    'Production': ProductionConfig,
    'Debug': DebugConfig
}

def load_config(env='Debug'):
    """Load the appropriate configuration based on the environment."""
    return config_dict.get(env, DebugConfig)()
