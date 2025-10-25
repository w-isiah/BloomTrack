from datetime import datetime
import pytz
import mysql.connector
import traceback

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app
)

# NOTE: Assuming these imports exist in your environment
from apps import get_db_connection
# Assuming a blueprint is defined elsewhere, we'll use a local one for structure
# from apps.audit import blueprint 
blueprint = Blueprint('traffic_blueprint', __name__) 

# --- Helper Functions ---

def get_kampala_time():
    """Returns the current datetime object localized to Africa/Kampala."""
    # Retaining the original helper, though not strictly needed for this report
    kampala = pytz.timezone("Africa/Kampala")
    return datetime.now(kampala)

def get_segment(request):
    """Extracts the last part of the URL to determine the current page."""
    try:
        segment = request.path.split('/')[-1]
        return segment if segment else 'traffic_report'
    except Exception:
        return None


# --- Main Reporting Route Function ---

@blueprint.route('/traffic_report', methods=['GET', 'POST'])
def traffic_report():
    """
    Handles the display and filtering for the Website Traffic Report.
    This function now contains all logic for fetching traffic data.
    """
    if 'id' not in session:
        flash('Login required to access this page.', 'error')
        return redirect(url_for('authentication_blueprint.login'))

    connection = None
    cursor = None
    traffic_logs = []
    
    # 2. Filter Setup
    today = datetime.today().strftime('%Y-%m-%d')
    start_date = end_date = today
    searched = False

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 1. Fetch current user (Mocked or actual user retrieval needed for template context)
        # Note: You'd need to adapt user retrieval based on your actual database schema
        user = {'id': session['id'], 'username': 'Current User'}
        
        if request.method == 'POST':
            start_date = request.form.get('start_date') or today
            end_date = request.form.get('end_date') or today
            
            # Merged traffic data fetching logic
            traffic_query = """
            SELECT
                id,
                page,
                ip_address,
                user_agent,
                view_time
            FROM page_views
            WHERE DATE(view_time) BETWEEN %s AND %s
            ORDER BY view_time DESC
            """
            params = [start_date, end_date]
        
            cursor.execute(traffic_query, tuple(params))
            traffic_logs = cursor.fetchall()
            
            searched = True

    except mysql.connector.Error as db_err:
        current_app.logger.error(f"Database Error in traffic_report: {db_err}")
        flash('A database error occurred while fetching traffic reports.', 'error')
    except Exception as e:
        current_app.logger.error(f"Unexpected Error in traffic_report: {e}")
        flash('An unexpected error occurred.', 'error')

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    # 5. Template Rendering
    # Renders the new traffic report template
    return render_template(
        'traffic/traffic_report.html',
        user=user,
        traffic_logs=traffic_logs, 
        start_date=start_date,
        end_date=end_date,
        searched=searched,
        segment='traffic_report'
    )
