import os
import random
import string
import logging

def setup_logging():
    """Set up logging configuration based on the environment."""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    log_level = logging.DEBUG if os.getenv('FLASK_ENV') == 'development' else logging.INFO
    logging.basicConfig(level=log_level, format=log_format)

# Call logging setup on import
setup_logging()

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

    # Database configuration - loaded from environment variables
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'pos_db')

    @staticmethod
    def init_app(app):
        """Initialize the app with the configuration."""
        app.config.from_object(Config)
        # Ensure the upload folder exists
        create_folder_if_not_exists(app.config['UPLOAD_FOLDER'])

def create_folder_if_not_exists(folder_path):
    """Ensure the folder exists or create it."""
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
            logging.info(f"Created folder: {folder_path}")
        except Exception as e:
            logging.error(f"Failed to create folder {folder_path}: {e}")

class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600  # 1 hour duration for "remember me" cookies
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_SAMESITE = 'Strict'  # Prevent CSRF attacks

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
