import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from importlib import import_module
from dotenv import load_dotenv
import mysql.connector

# Initialize extensions
csrf = CSRFProtect()

# Load environment variables from .env
load_dotenv()

# Database connection config
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'pos_db')
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except mysql.connector.Error as e:
        print("Error while connecting to MySQL", e)
    return None

def register_extensions(app):
    """Initialize and register Flask extensions"""
    csrf.init_app(app)

def register_blueprints(app):
    """Dynamically register blueprints from the apps module."""
    for module_name in ('authentication', 'home','products','sales','customers','categories'):
        module = import_module(f'apps.{module_name}.routes')
        app.register_blueprint(module.blueprint)

def create_app(config):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)
    
    # Ensure the app has a secret key for sessions
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
    
    return app
