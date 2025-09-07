from apps.home import blueprint
from flask import render_template, request, session, flash, redirect, url_for
from flask_login import login_required, current_user
from jinja2 import TemplateNotFound
from apps import get_db_connection
import logging

from flask import render_template, redirect, url_for, flash
from apps import get_db_connection

from datetime import datetime, timedelta
import pytz
from decimal import Decimal, InvalidOperation

def get_kampala_time():
    kampala = pytz.timezone("Africa/Kampala")
    return datetime.now(kampala)

def get_sales_summary(cursor, start_date, end_date):
    """Calculate total sales, total quantity sold, and total discount for given date range."""
    cursor.execute("""
        SELECT s.qty, s.discount, p.price AS current_price
        FROM sales s
        JOIN product_list p ON s.ProductID = p.ProductID
        WHERE s.type = 'sales' AND DATE(s.date_updated) BETWEEN %s AND %s
    """, (start_date, end_date))
    sales_raw = cursor.fetchall()

    total_sales = Decimal("0.00")
    total_quantity = 0
    total_before_discount = Decimal("0.00")

    for row in sales_raw:
        try:
            unit_price = row['current_price'] or Decimal("0.00")
            discount = Decimal(row['discount']) if row['discount'] is not None else Decimal("0.00")
            qty = row['qty'] or 0

            discounted_unit_price = unit_price * (Decimal("1.00") - discount / Decimal("100"))
            line_total = discounted_unit_price * qty

            total_sales += line_total
            total_before_discount += unit_price * qty
            total_quantity += qty
        except (InvalidOperation, TypeError):
            continue

    return total_sales, total_quantity

@blueprint.route('/index')
def index():
    if 'id' not in session:
        flash('Login required to access this page.', 'error')
        return redirect(url_for('authentication_blueprint.login'))

    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Fetch user info
                cursor.execute("SELECT * FROM users WHERE id = %s", (session['id'],))
                user = cursor.fetchone()
                if not user:
                    flash('User not found. Please log in again.', 'error')
                    return redirect(url_for('authentication_blueprint.login'))

                # Dates in Kampala timezone
                kampala_now = get_kampala_time()
                today = kampala_now.strftime('%Y-%m-%d')
                yesterday = (kampala_now - timedelta(days=1)).strftime('%Y-%m-%d')

                # Sales summaries
                total_sales_today, total_items_sold_today = get_sales_summary(cursor, today, today)
                total_sales_yesterday, _ = get_sales_summary(cursor, yesterday, yesterday)

                # Expenses today
                cursor.execute("""
                    SELECT SUM(s.price) AS total_expenses_today
                    FROM sales s
                    WHERE s.type = 'expense' AND DATE(s.date_updated) = %s
                """, (today,))
                expense_result = cursor.fetchone()
                total_expenses_today = expense_result['total_expenses_today'] or Decimal("0.00")

                # Products to reorder
                cursor.execute("""
                    SELECT * FROM product_list
                    WHERE reorder_level > quantity
                    ORDER BY name
                """)
                products_to_reorder = cursor.fetchall()

                # Formatting helper
                def format_to_ugx(amount):
                    return f"UGX {amount:,.2f}" if amount else "UGX 0"

                context = {
                    'total_sales_today': format_to_ugx(total_sales_today),
                    'total_sales_yesterday': format_to_ugx(total_sales_yesterday),
                    'total_expenses_today': format_to_ugx(total_expenses_today),
                    'total_items_sold_today': total_items_sold_today,
                    'products_to_reorder': products_to_reorder,
                    'segment': 'index'
                }

                if user['role'] in ['admin', 'super_admin']:
                    return render_template('home/index.html', **context)
                elif user['role'] == 'class_teacher':
                    return render_template('home/user_index.html', **context)

                flash('Unauthorized role. Please log in again.', 'error')
                return redirect(url_for('authentication_blueprint.login'))

    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'danger')
        return redirect(url_for('authentication_blueprint.login'))






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
