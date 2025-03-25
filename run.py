import os
import mysql.connector
from flask import Flask
from flask_migrate import Migrate
from flask_minify import Minify
from sys import exit

from apps.config import config_dict
from apps import create_app

# WARNING: Don't run with debug turned on in production!
DEBUG = (os.getenv('DEBUG', 'False') == 'True')

# Determine the configuration mode based on the DEBUG flag
get_config_mode = 'Debug' if DEBUG else 'Production'

try:
    # Load the appropriate configuration class based on the mode (Debug or Production)
    app_config = config_dict[get_config_mode.capitalize()]

except KeyError:
    # If the configuration mode is invalid, exit with an error message
    exit('Error: Invalid <config_mode>. Expected values [Debug, Production] ')

# Initialize the application with the selected configuration
app = create_app(app_config)

# Initialize Flask-Migrate to handle database migrations (this is still useful for migrations)
Migrate(app, None)  # Passing None because we're handling the DB connection manually

# Create a MySQL connection using mysql.connector
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=app_config.MYSQL_HOST,
            user=app_config.MYSQL_USER,
            password=app_config.MYSQL_PASSWORD,
            database=app_config.MYSQL_DATABASE
        )
        print("Successfully connected to the MySQL database")
        return connection
    except mysql.connector.Error as err:
        app.logger.error(f"Error: {err}")
        exit("Database connection failed.")

# If not in DEBUG mode, apply Minification for faster page loading
if not DEBUG:
    # Minify HTML, but not JS or CSS files
    Minify(app=app, html=True, js=False, cssless=False)

# If in DEBUG mode, log configuration details for debugging purposes
if DEBUG:
    app.logger.info('DEBUG            = ' + str(DEBUG))
    app.logger.info('Page Compression = ' + 'FALSE' if DEBUG else 'TRUE')
    app.logger.info('DBMS             = MySQL')  # Mentioning MySQL as the DBMS
    app.logger.info('ASSETS_ROOT      = ' + app_config.ASSETS_ROOT)

# Run the Flask application
if __name__ == "__main__":
    app.run()
