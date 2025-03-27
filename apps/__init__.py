import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from importlib import import_module
import mysql.connector
import logging
from apps.config import load_config

# Initialize extensions
csrf = CSRFProtect()

def get_db_connection():
    """Create and return a MySQL database connection using mysql.connector."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'pos_db')
            # Removed DB_PORT configuration
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
    """Dynamically register blueprints from the apps module."""
    modules = ['authentication', 'home', 'products', 'sales', 'customers', 'categories']
    for module_name in modules:
        module = import_module(f'apps.{module_name}.routes')
        app.register_blueprint(module.blueprint)

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
