import os
import mysql.connector
from flask import Flask
from flask_minify import Minify
from sys import exit

from apps.config import config_dict
from apps import create_app

# WARNING: Don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Determine the configuration mode based on the DEBUG flag
config_mode = 'Debug' if DEBUG else 'Production'

# Load the appropriate configuration class based on the mode (Debug or Production)
try:
    app_config = config_dict[config_mode.capitalize()]
except KeyError:
    exit(f'Error: Invalid config_mode "{config_mode}". Expected values [Debug, Production]')

# Initialize the application with the selected configuration
app = create_app(app_config)

# Create a MySQL connection using mysql.connector
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=app_config.MYSQL_HOST,
            user=app_config.MYSQL_USER,
            password=app_config.MYSQL_PASSWORD,
            database=app_config.MYSQL_DATABASE
        )
        app.logger.info("Successfully connected to the MySQL database.")
        return connection
    except mysql.connector.Error as err:
        app.logger.error(f"Database connection error: {err}")
        exit("Database connection failed.")

# If not in DEBUG mode, apply Minification for faster page loading
if not DEBUG:
    Minify(app=app, html=True, js=False, cssless=False)

# If in DEBUG mode, log configuration details for debugging purposes
if DEBUG:
    app.logger.info(f'DEBUG            = {DEBUG}')
    app.logger.info(f'Page Compression = {"FALSE" if DEBUG else "TRUE"}')
    app.logger.info('DBMS             = MySQL')  # Mentioning MySQL as the DBMS
    app.logger.info(f'ASSETS_ROOT      = {app_config.ASSETS_ROOT}')

# Run the Flask application
if __name__ == "__main__":
    app.run(debug=DEBUG)
