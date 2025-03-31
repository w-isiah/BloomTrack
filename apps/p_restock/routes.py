from apps.p_restock import blueprint
from flask import render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.utils import secure_filename
from mysql.connector import Error
from datetime import datetime
import os
import random
import logging
import re  # <-- Add this line
from apps import get_db_connection
from jinja2 import TemplateNotFound



# Route for the 'products' page
@blueprint.route('/p_restock')
def p_restock():
    """Renders the 'products' page."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(''' 
            SELECT *
            FROM product_list
            ORDER BY name
        ''')
        products = cursor.fetchall()

        # Calculate totals and format them
        
    except Error as e:
        logging.error(f"Database error: {e}")
        flash("An error occurred while fetching products.", "error")
        return render_template('products/page-500.html'), 500

    finally:
        cursor.close()
        connection.close()

    return render_template('p_restock/p_restock.html',
                           
                           products=products,
                           
                           segment='restock')








# Route to restock product
@blueprint.route('/restock_item', methods=['GET', 'POST'])
def restock_item():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        # Check if user is logged in (i.e., user_id exists in session)
        if 'id' not in session:
            flash("You must be logged in to restock products.", "danger")
            return redirect(url_for('auth.login'))  # Redirect to login page if not logged in

        # Retrieve form data
        sku = request.form.get('sku')
        restock_quantity = int(request.form.get('restock_quantity'))
        user_id = session['id']  # Get user_id from session

        # Check if the product exists
        cursor.execute('SELECT * FROM product_list WHERE sku = %s', (sku,))
        product = cursor.fetchone()

        if product:
            # Calculate new quantity
            new_quantity = product['quantity'] + restock_quantity

            # Update the product's quantity in the database
            cursor.execute('UPDATE product_list SET quantity = %s WHERE sku = %s', (new_quantity, sku))
            connection.commit()

            # Log the inventory change (restock) with user_id
            cursor.execute("""
                INSERT INTO inventory_logs (product_id, quantity_change, reason, log_date, user_id)
                VALUES (%s, %s, %s, NOW(), %s)
            """, (product['ProductID'], restock_quantity, 'restock', user_id))
            connection.commit()

            # Flash a success message to the user
            flash(f"Product with SKU {sku} has been restocked successfully. New quantity: {new_quantity}.")
        else:
            # Flash an error message if the product does not exist
            flash(f"Product with SKU {sku} does not exist!")

    # Fetch the list of products to display in the template
    cursor.execute('SELECT * FROM product_list')
    products = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('p_restock/p_restock.html', segment='p_restock', products=products)






@blueprint.route('/<template>')
def route_template(template):

    try:

        if not template.endswith('.html'):
            template += '.html'

        # Detect the current page
        segment = get_segment(request)

        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except:
        return render_template('home/page-500.html'), 500


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'p_restock'

        return segment

    except:
        return None
