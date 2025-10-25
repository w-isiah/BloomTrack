from datetime import datetime
from decimal import Decimal, InvalidOperation
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
    jsonify,
    current_app
)
from jinja2 import TemplateNotFound

# NOTE: Assuming these imports exist in your environment
from apps import get_db_connection
from apps.audit import blueprint # Assuming the Blueprint is initialized here

# --- Helper Functions ---

def get_kampala_time():
    """Returns the current datetime object localized to Africa/Kampala."""
    kampala = pytz.timezone("Africa/Kampala")
    return datetime.now(kampala)

def get_segment(request):
    """Extracts the last part of the URL to determine the current page."""
    try:
        # Check if the path is a file name like /sales/inventory_view
        segment = request.path.split('/')[-1]
        # Return segment, or 'sales' if it's empty (e.g., /sales/)
        return segment if segment else 'sales'
    except Exception:
        return None

def _fetch_inventory_movements(cursor, start_date, end_date, selected_farm_id, selected_product_id):
    """
    Fetches all inventory log movements using the updated 'inventory_logs' schema.
    Applies filters for date range, farm, and product.
    Returns: A list of dictionaries representing inventory log entries.
    """
    inventory_query = """
    SELECT
        i.inventory_log_id,
        p.name AS product_name,
        i.reason,
        i.quantity_change,
        i.price_change,      -- This is the NEW price/cost
        i.old_price,         -- This is the OLD price/cost
        i.log_date,
        f.name AS farm_name,
        u.username           -- User who made the change
    FROM inventory_logs i
    JOIN product_list p ON i.product_id = p.ProductID
    LEFT JOIN farm_list f ON p.farm_id = f.farm_id -- Link via product_list
    LEFT JOIN users u ON i.user_id = u.id          -- Get the username
    WHERE DATE(i.log_date) BETWEEN %s AND %s
    """
    params = [start_date, end_date]

    if selected_farm_id:
        inventory_query += " AND f.farm_id = %s"
        params.append(selected_farm_id)
    
    # NEW: Apply product filter
    if selected_product_id:
        inventory_query += " AND p.ProductID = %s"
        params.append(selected_product_id)

    inventory_query += " ORDER BY i.log_date DESC"
    cursor.execute(inventory_query, tuple(params))
    logs = cursor.fetchall()

    return logs


# --- Main Reporting Route Function ---

@blueprint.route('/inventory_view', methods=['GET', 'POST'])
def inventory_view():
    """Handles the display and filtering for the Inventory Movement Report."""
    if 'id' not in session:
        flash('Login required to access this page.', 'error')
        return redirect(url_for('authentication_blueprint.login'))

    connection = None
    cursor = None
    logs = []
    farms = []
    products = [] # NEW: Initialize products list
    
    # 2. Filter Setup
    today = datetime.today().strftime('%Y-%m-%d')
    start_date = end_date = today
    selected_farm_id = ''
    selected_product_id = '' # NEW: Initialize selected product ID
    searched = False

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 1. Fetch current user
        cursor.execute("SELECT * FROM users WHERE id = %s", (session['id'],))
        user = cursor.fetchone()
        if not user:
            flash('User not found. Please log in again.', 'error')
            return redirect(url_for('authentication_blueprint.login'))

        if request.method == 'POST':
            start_date = request.form.get('start_date') or today
            end_date = request.form.get('end_date') or today
            selected_farm_id = request.form.get('farm_id') or ''
            selected_product_id = request.form.get('product_id') or '' # NEW: Get product filter value
            searched = True

        # 3. Get all farms AND products for filter dropdowns (Always fetch for the filters)
        cursor.execute("SELECT farm_id AS FarmID, name FROM farm_list ORDER BY name")
        farms = cursor.fetchall()
        
        cursor.execute("SELECT ProductID, name FROM product_list ORDER BY name")
        products = cursor.fetchall()
        
        # 4. Fetch Inventory Data (Only on POST)
        if request.method == 'POST':
            logs = _fetch_inventory_movements(
                cursor, 
                start_date, 
                end_date, 
                selected_farm_id,
                selected_product_id # NEW: Pass product ID filter
            )
            searched = True

    except mysql.connector.Error as db_err:
        current_app.logger.error(f"Database Error in inventory_view: {db_err}")
        flash('A database error occurred while fetching inventory reports.', 'error')
    except Exception as e:
        current_app.logger.error(f"Unexpected Error in inventory_view: {e}")
        flash('An unexpected error occurred.', 'error')

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    # 5. Template Rendering
    return render_template(
        'audit/inventory_movement_report.html',
        user=user,
        logs=logs, # Changed to 'logs' to match template usage
        farms=farms,
        products=products, # NEW: Pass products list
        selected_farm_id=selected_farm_id,
        selected_product_id=selected_product_id, # NEW: Pass selected product ID
        start_date=start_date,
        end_date=end_date,
        searched=searched,
        segment='inventory_view'
    )

@blueprint.route('/<template>')
def route_template(template):
    """Renders a dynamic template page."""
    try:
        if not template.endswith('.html'):
            template += '.html'

        segment = get_segment(request)

        # Assuming templates for this blueprint are under 'sales/' or 'audit/'
        # Use 'audit/' for consistency with the inventory_view route.
        return render_template(f"audit/{template}", segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except Exception as e:
        current_app.logger.error(f"Error rendering template {template}: {e}")
        return render_template('home/page-500.html'), 500
