from datetime import datetime
import pytz
import mysql.connector
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, current_app
)
from apps import get_db_connection

from apps.traffic import blueprint
# Helper function
def get_kampala_time():
    kampala = pytz.timezone("Africa/Kampala")
    return datetime.now(kampala)

@blueprint.route('/system_info_report', methods=['GET', 'POST'])
def system_info_report():
    """
    Displays system device info with filtering by date range.
    Defaults to current date if no filter is selected.
    """
    # (Optional) Session login check
    if 'id' not in session:
        flash('Login required to access this page.', 'error')
        return redirect(url_for('authentication_blueprint.login'))

    connection = None
    cursor = None
    system_data = []

    today = datetime.today().strftime('%Y-%m-%d')
    start_date = end_date = today
    searched = False

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Default query for today's records
        query = """
            SELECT id, ip_address, mac_address, device_id, country, state, received_at
            FROM system_info
            WHERE DATE(received_at) = %s
            ORDER BY received_at DESC
        """
        params = [today]

        # If form submitted, adjust query for range
        if request.method == 'POST':
            start_date = request.form.get('start_date') or today
            end_date = request.form.get('end_date') or today
            query = """
                SELECT id, ip_address, mac_address, device_id, country, state, received_at
                FROM system_info
                WHERE DATE(received_at) BETWEEN %s AND %s
                ORDER BY received_at DESC
            """
            params = [start_date, end_date]
            searched = True
        else:
            searched = True  # also show today's records by default

        cursor.execute(query, tuple(params))
        system_data = cursor.fetchall()

    except mysql.connector.Error as db_err:
        current_app.logger.error(f"Database Error in system_info_report: {db_err}")
        flash('A database error occurred while fetching system info.', 'error')
    except Exception as e:
        current_app.logger.error(f"Unexpected Error in system_info_report: {e}")
        flash('An unexpected error occurred.', 'error')
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    # Render to the new front-end page
    return render_template(
        'traffic/system_info_report.html',
        system_data=system_data,
        start_date=start_date,
        end_date=end_date,
        searched=searched,
        segment='system_info_report'
    )
