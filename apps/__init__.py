import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from importlib import import_module
import mysql.connector  # Ensure mysql.connector is imported
import logging
from apps.config import load_config

# Initialize extensions
csrf = CSRFProtect()

def get_db_connection():
    """Create and return a MySQL database connection using mysql.connector."""
    try:
        # Fetch DB configuration from app.config
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'pos_db')
        )
        if connection.is_connected():
            logging.info("Database connection successful.")
            return connection
    except mysql.connector.Error as err:
        logging.error(f"Error while connecting to MySQL: {err}")
        return None

def register_extensions(app):
    """Register Flask extensions."""
    csrf.init_app(app)

def register_blueprints(app):
    """Dynamically register blueprints from all modules in the apps directory."""
    for module_name in os.listdir('apps'):
        module_path = os.path.join('apps', module_name)

        # Skip non-Python files and directories like 'static', 'templates', '__pycache__', and 'config.py'
        if not os.path.isdir(module_path) or module_name in ['static', 'templates', '__pycache__', 'config.py']:
            continue
        
        try:
            # Try to dynamically import the module
            module = import_module(f'apps.{module_name}.routes')
            if hasattr(module, 'blueprint'):
                app.register_blueprint(module.blueprint)
        except ImportError as e:
            logging.warning(f"Could not register blueprint for module {module_name}: {e}")

def create_app(config_class='Debug'):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    config = load_config(config_class)
    app.config.from_object(config)

    # Register extensions and blueprints
    register_extensions(app)
    register_blueprints(app)

    # Ensure the app has a secret key
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')

    logging.info(f"App initialized with {config.__class__.__name__} configuration.")
    
    return app
