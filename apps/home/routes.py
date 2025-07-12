from apps.home import blueprint
from flask import render_template, request, session, flash
from jinja2 import TemplateNotFound
from apps import get_db_connection
import logging

from flask import redirect, url_for






@blueprint.route('/index')
def index():
    """
    Renders the 'index' page of the home section only for admin or director.
    """
    if 'id' not in session:
        flash('Login required to access this page.', 'error')
        return redirect(url_for('authentication_blueprint.login'))

    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Retrieve user from session ID
                cursor.execute("SELECT * FROM users WHERE id = %s", (session['id'],))
                user = cursor.fetchone()

                if not user:
                    flash('User not found. Please log in again.', 'error')
                    return redirect(url_for('authentication_blueprint.login'))

                if user['role'] not in ['admin', 'user', 'super_admin']:
                    flash('You do not have permission to access this page.', 'warning')
                    return redirect(url_for('some_other_blueprint.some_view'))  # Adjust as needed

                # Total sales today
                cursor.execute('''
                    SELECT SUM(total_price) AS total_sales_today
                    FROM sales
                    WHERE DATE(date_updated) = CURDATE() AND type = 'sales';
                ''')
                total_sales_today = cursor.fetchone()

                # Total quantity sold today
                cursor.execute('''
                    SELECT SUM(qty) AS total_items_sold_today
                    FROM sales
                    WHERE DATE(date_updated) = CURDATE() AND type = 'sales';
                ''')
                total_items_sold_today = cursor.fetchone()

                # Total sales yesterday
                cursor.execute('''
                    SELECT SUM(total_price) AS total_sales_yesterday
                    FROM sales
                    WHERE DATE(date_updated) = CURDATE() - INTERVAL 1 DAY AND type = 'sales';
                ''')
                total_sales_yesterday = cursor.fetchone()

                # Total expenses today
                cursor.execute('''
                    SELECT SUM(total_price) AS total_expenses_today
                    FROM sales
                    WHERE DATE(date_updated) = CURDATE() AND type = 'expense';
                ''')
                total_expenses_today = cursor.fetchone()

                # Products to reorder
                cursor.execute('''
                    SELECT * FROM product_list
                    WHERE reorder_level > quantity
                    ORDER BY name
                ''')
                products_to_reorder = cursor.fetchall()

    except Exception as e:
        flash(f"An error occurred while fetching data: {str(e)}", "danger")
        return redirect(url_for('authentication_blueprint.login'))

    # Formatting helpers
    def format_to_ugx(amount):
        if not amount:
            return "UGX 0"
        return f"UGX {amount:,.2f}"

    formatted_sales_today = format_to_ugx(total_sales_today.get('total_sales_today'))
    formatted_sales_yesterday = format_to_ugx(total_sales_yesterday.get('total_sales_yesterday'))
    formatted_expenses_today = format_to_ugx(total_expenses_today.get('total_expenses_today'))
    total_items_sold_today_value = total_items_sold_today.get('total_items_sold_today') or 0

    return render_template(
        'home/index.html',
        total_sales_today=formatted_sales_today,
        total_sales_yesterday=formatted_sales_yesterday,
        total_expenses_today=formatted_expenses_today,
        total_items_sold_today=total_items_sold_today_value,
        products_to_reorder=products_to_reorder,
        segment='index'
    )











@blueprint.route('/<template>')
def route_template(template):
    """
    Renders dynamic templates from the 'home' folder.
    """
    try:
        if not template.endswith('.html'):
            template += '.html'
        
        segment = get_segment(request)
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        logging.error(f"Template {template} not found")
        return render_template('home/page-404.html', segment=segment), 404

    except Exception as e:
        logging.error(f"Error rendering template {template}: {str(e)}")
        return render_template('home/page-500.html', segment=segment), 500

def get_segment(request):
    """
    Extracts the last part of the URL path to identify the current page.
    """
    segment = request.path.strip('/').split('/')[-1]
    if not segment:
        segment = 'index'
    return segment
