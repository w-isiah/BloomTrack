import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from importlib import import_module
from apps.config import Config  # Import configuration
from apps.db import get_db_connection  # Import DB connection function

# Initialize extensions
csrf = CSRFProtect()

def register_extensions(app):
    """Register Flask extensions."""
    csrf.init_app(app)

def register_blueprints(app):
    """Dynamically register blueprints from apps folder."""
    for module_name in os.listdir('apps'):
        module_path = os.path.join('apps', module_name)
        if not os.path.isdir(module_path) or module_name in ['static', 'templates', '__pycache__']:
            continue
        try:
            # Dynamically import the blueprint from each module's routes
            module = import_module(f'apps.{module_name}.routes')
            if hasattr(module, 'blueprint'):
                app.register_blueprint(module.blueprint)
        except ImportError as e:
            # Handle ImportError gracefully
            print(f"Error importing module {module_name}: {e}")

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register extensions and blueprints
    register_extensions(app)
    register_blueprints(app)

    return app
