import mysql.connector
from app import app  # Import the app here to avoid circular import

def get_db_connection():
    connection = mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    
    # Return the connection along with the host, user, password, and database from app.config
    return connection