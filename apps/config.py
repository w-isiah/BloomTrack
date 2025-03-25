import os
import random
import string
import mysql.connector
import logging

# Set up basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration class for the application
class Config(object):
    # The base directory is the absolute path of the folder where this file is located
    basedir = os.path.abspath(os.path.dirname(__file__))

    # Asset management configuration: the root folder for static assets
    ASSETS_ROOT = os.getenv('ASSETS_ROOT', '/static/assets')

    # Set up the App SECRET_KEY. If it's not set in environment variables, generate a random 32-character key.
    SECRET_KEY = os.getenv('SECRET_KEY', None)
    if not SECRET_KEY:
        SECRET_KEY = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))

    # Database connection parameters, fetched from environment variables
    DB_USERNAME = os.getenv('DB_USERNAME', "root")
    DB_PASS = os.getenv('DB_PASS', "")
    DB_HOST = os.getenv('DB_HOST', "localhost")
    DB_PORT = os.getenv('DB_PORT', 3306)  # Default MySQL port is 3306
    DB_NAME = os.getenv('DB_NAME', 'pos_db')  # Default to 'pos_db' if DB_NAME isn't set

    # Ensure the connection is made to MySQL
    def test_db_connection(self):
        """Test connection to MySQL database."""
        try:
            # Attempt to connect to the MySQL database using mysql.connector
            connection = mysql.connector.connect(
                host=self.DB_HOST,
                user=self.DB_USERNAME,
                password=self.DB_PASS,
                database=self.DB_NAME,
                port=self.DB_PORT
            )
            connection.close()  # Close connection after testing
            logging.info("Database connection successful.")
        except mysql.connector.Error as err:
            logging.error(f"MySQL connection failed: {err}")
            raise Exception("MySQL connection failed. Please check the connection settings.")
        except Exception as e:
            logging.error(f"Unexpected error occurred: {e}")
            raise Exception("Database connection failed due to an unexpected error.")

# Production-specific configuration class
class ProductionConfig(Config):
    DEBUG = False  # In production, debugging is disabled

    # Security settings for production
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript from accessing the session cookie
    REMEMBER_COOKIE_HTTPONLY = True  # Prevent JavaScript from accessing the remember me cookie
    REMEMBER_COOKIE_DURATION = 3600  # Duration for the remember me cookie (1 hour)

# Debug-specific configuration class
class DebugConfig(Config):
    DEBUG = True  # Enable debugging for development

# Dictionary to load different configurations based on environment
config_dict = {
    'Production': ProductionConfig,  # Production environment configuration
    'Debug': DebugConfig  # Debug environment configuration
}

# Example of how you could use the configuration:
def load_config(env='Debug'):
    """Load the appropriate config class based on environment."""
    config_class = config_dict.get(env, DebugConfig)
    config = config_class()
    
    # Test the DB connection on config load
    try:
        config.test_db_connection()
    except Exception as e:
        logging.error(f"Error during DB connection test: {e}")
        raise

    return config

if __name__ == "__main__":
    # For example, load configuration in Debug mode
    config = load_config('Debug')
    logging.info(f"Using config: {config.__class__.__name__}")
