import os
import random
import logging
from flask import render_template, request, redirect, url_for, flash, current_app,jsonify
from werkzeug.utils import secure_filename
from mysql.connector import Error
from apps import get_db_connection
from apps.products import blueprint
import mysql.connector

from datetime import datetime
import pytz

def get_kampala_time():
    """Returns the current datetime in Kampala timezone."""
    kampala = pytz.timezone("Africa/Kampala")
    return datetime.now(kampala)



# Helper function to calculate formatted totals
def calculate_formatted_totals(products):
    total_sum = sum(product['total_price'] for product in products)
    total_price = sum(product['price'] for product in products)

    formatted_total_sum = "{:,.2f}".format(total_sum) if total_sum else '0.00'
    formatted_total_price = "{:,.2f}".format(total_price) if total_price else '0.00'

    for product in products:
        product['formatted_total_price'] = "{:,.2f}".format(product['total_price']) if product['total_price'] else '0.00'
        product['formatted_price'] = "{:,.2f}".format(product['price']) if product['price'] else '0.00'

    return formatted_total_sum, formatted_total_price


# Access the upload folder from the current Flask app configuration
def allowed_file(filename):
    """Check if the uploaded file has a valid extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']






# Route for the 'products' page
@blueprint.route('/products')
def products():
    """Renders the 'products' page."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(''' 
            SELECT 
                p.*, 
                c.name AS category_name, 
                f.name AS farm_name,  -- <-- Added farm name here
                (p.quantity * p.price) AS total_price
            FROM 
                product_list p
            JOIN 
                category_list c ON p.category_id = c.CategoryID
            LEFT JOIN -- Using LEFT JOIN ensures products without a farm_id are still shown
                farm_list f ON p.farm_id = f.farm_id -- <-- Joined farm_list table
            ORDER BY 
                p.name
        ''')
        products = cursor.fetchall()

        # Assuming calculate_formatted_totals is defined elsewhere
        # Calculate totals and format them
        formatted_total_sum, formatted_total_price = calculate_formatted_totals(products)

    except Error as e:
        logging.error(f"Database error: {e}")
        flash("An error occurred while fetching products.", "error")
        return render_template('products/page-500.html'), 500

    finally:
        cursor.close()
        connection.close()

    return render_template('products/products.html',
                            formatted_total_price=formatted_total_price,
                            products=products,
                            formatted_total_sum=formatted_total_sum,
                            segment='products')










@blueprint.route('/products_marketing')
def products_marketing():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Log page view
        cursor.execute(
            "INSERT INTO page_views (page, ip_address, user_agent, view_time) "
            "VALUES (%s, %s, %s, NOW())",
            ('products_marketing', request.remote_addr, request.headers.get('User-Agent'))
        )
        connection.commit()

        # Fetch products
        cursor.execute('''
            SELECT p.*, c.name AS category_name, (p.quantity * p.price) AS total_price
            FROM product_list p
            JOIN category_list c ON p.category_id = c.CategoryID
            ORDER BY p.name
        ''')
        products = cursor.fetchall()

        # Calculate totals
        formatted_total_sum, formatted_total_price = calculate_formatted_totals(products)

    finally:
        cursor.close()
        connection.close()

    return render_template(
        'products/products_marketing.html',
        products=products,
        formatted_total_sum=formatted_total_sum,
        formatted_total_price=formatted_total_price
    )


# Endpoint to track product clicks
@blueprint.route('/track_click', methods=['POST'])
def track_click():
    product_id = request.form.get('product_id')
    if not product_id:
        return jsonify({'status': 'error', 'message': 'Product ID missing'}), 400

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO product_clicks (product_id, ip_address, user_agent, click_time) "
            "VALUES (%s, %s, %s, NOW())",
            (product_id, request.remote_addr, request.headers.get('User-Agent'))
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    return jsonify({'status': 'success'})











@blueprint.route('/api/products', methods=['GET'])
def api_products():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute('''
            SELECT p.ProductID AS id, p.name, p.description, p.price, p.sku, p.quantity,
                   p.image, c.name AS category_name, p.updated_at
            FROM product_list p
            JOIN category_list c ON p.category_id = c.CategoryID
            ORDER BY p.name
        ''')
        products = cursor.fetchall()

        for p in products:
            if p['price'] is not None:
                p['price'] = float(p['price'])
            if p['quantity'] is not None:
                p['quantity'] = int(p['quantity'])

        return jsonify(products)

    except Error as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": "Unable to fetch products"}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()









# Route to add a new product
@blueprint.route('/add_product', methods=['GET', 'POST'])
def add_product():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 1. Fetch categories from the database
    cursor.execute('SELECT * FROM category_list ORDER BY name')
    categories = cursor.fetchall()

    # 2. Fetch farms (farm_id and name) from the database
    # Changed from hardcoded list to a database query
    cursor.execute('SELECT farm_id, name FROM farm_list ORDER BY name')
    farm_options = cursor.fetchall()

    # Generate a random SKU
    random_num = random.randint(1005540, 9978799)

    # Ensure the SKU is unique
    while True:
        cursor.execute('SELECT * FROM product_list WHERE sku = %s', (random_num,))
        if not cursor.fetchone():
            break  # Unique SKU found
        random_num = random.randint(1005540, 9978799)

    if request.method == 'POST':
        # Retrieve form data
        category_id = request.form.get('category_id')
        sku = request.form.get('serial_no') or random_num
        price = request.form.get('price')
        name = request.form.get('name')
        description = request.form.get('description')
        quantity = 0
        reorder_level = request.form.get('reorder_level')
        # IMPORTANT: This now retrieves the farm_id from the dropdown value
        farm_id = request.form.get('farm_id')

        # Check for existing product with the same name in the selected category
        cursor.execute('SELECT * FROM product_list WHERE category_id = %s AND name = %s', (category_id, name))
        existing_product = cursor.fetchone()

        if existing_product:
            flash("This product already exists in the selected category!", "danger")
        else:
            # Handle image upload (assuming 'allowed_file' and 'current_app' are defined elsewhere)
            image_file = request.files.get('image')
            image_filename = None  # Default if no image is uploaded

            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_filename = f"{random_num}_{filename}"

                # Ensure the directory exists before saving the file
                # NOTE: current_app must be imported or available in the scope (e.g., from flask import current_app)
                image_folder = os.path.join(current_app.config['UPLOAD_FOLDER'])
                if not os.path.exists(image_folder):
                    os.makedirs(image_folder)

                image_path = os.path.join(image_folder, image_filename)
                image_file.save(image_path)

            # Insert new product into the database
            # Updated to insert farm_id instead of 'farm' (which should be farm_id in product_list table)
            cursor.execute('''INSERT INTO product_list 
                (category_id, sku, price, name, description, quantity, reorder_level, image, farm_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (category_id, sku, price, name, description, quantity, reorder_level, image_filename, farm_id))
            
            connection.commit()
            flash("Product successfully added!", "success")

    cursor.close()
    connection.close()

    return render_template(
        'products/add_product.html',
        random_num=random_num,
        categories=categories,
        farm_options=farm_options,    # Pass fetched farm list
        segment='add_product'
    )



# Route to edit an existing product
@blueprint.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    # Connect to the database
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 1. Fetch the product data from the database
    # Fetching all details is fine, including the existing farm_id
    cursor.execute('SELECT * FROM product_list WHERE ProductID = %s', (product_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!")
        return redirect(url_for('products_blueprint.products'))  # Redirect to products list

    # 2. Fetch categories for dropdown
    cursor.execute('SELECT * FROM category_list ORDER BY name')
    categories = cursor.fetchall()

    # 3. Fetch farms (farm_id and name) from the database
    # Changed from hardcoded list to a database query
    cursor.execute('SELECT farm_id, name FROM farm_list ORDER BY name')
    farm_options = cursor.fetchall()

    if request.method == 'POST':
        # Get form data
        category_id = request.form.get('category_id')
        sku = request.form.get('serial_no')
        price = request.form.get('price')
        name = request.form.get('name')
        description = request.form.get('description')
        reorder_level = request.form.get('reorder_level')
        # IMPORTANT: Retrieve the farm_id from the dropdown value
        farm_id = request.form.get('farm_id') 

        # Handle image upload (assuming 'allowed_file' and 'current_app' are defined elsewhere)
        image_filename = product['image']  # Keep old image unless new uploaded
        image_file = request.files.get('image')

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_filename = f"{product_id}_{filename}"  # Rename with product ID
            
            # Ensure directory exists
            image_folder = os.path.join(current_app.config['UPLOAD_FOLDER'])
            if not os.path.exists(image_folder):
                os.makedirs(image_folder)

            image_path = os.path.join(image_folder, image_filename)
            image_file.save(image_path)

        # Track price change
        old_price = product['price']
        price_change = None
        if price != old_price:
            # Safely compare and calculate change, ensuring types are floats/decimals
            try:
                price_change = float(price) - float(old_price)
            except (ValueError, TypeError):
                # Handle case where price conversion fails
                price_change = None 


        # Update product
        # IMPORTANT: Updated farm parameter to use farm_id and the corresponding database column
        cursor.execute(''' 
            UPDATE product_list
            SET category_id = %s, sku = %s, price = %s, name = %s, description = %s,
                reorder_level = %s, image = %s, farm_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE ProductID = %s
        ''', (category_id, sku, price, name, description, reorder_level, image_filename, farm_id, product_id))

        # Log price change
        if price_change is not None:
            cursor.execute('''
                INSERT INTO inventory_logs (product_id, quantity_change, log_date, reason, price_change, old_price)
                VALUES (%s, 0, CURRENT_TIMESTAMP, %s, %s, %s)
            ''', (product_id, 'Price Update', price_change, old_price))

        connection.commit()
        flash("Product updated successfully!", "success")
        
        # Close connection before redirect
        cursor.close()
        connection.close()
        return redirect(url_for('products_blueprint.products'))

    # GET request returns render_template
    cursor.close()
    connection.close()

    return render_template(
        'products/edit_product.html',
        product=product,
        categories=categories,
        farm_options=farm_options
    )




@blueprint.route('/delete_product/<string:get_id>')
def delete_product(get_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('DELETE FROM product_list WHERE ProductID = %s', (get_id,))
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('products_blueprint.products'))


@blueprint.route('/<template>')
def route_template(template):
    try:
        # Ensure the template ends with '.html' for correct render
        if not template.endswith('.html'):
            template += '.html'

        segment = get_segment(request)

        return render_template("products/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('products/page-404.html'), 404

    except Exception as e:
        return render_template('products/page-500.html'), 500


def get_segment(request):
    """Extracts the last part of the URL path to identify the current page."""
    try:
        segment = request.path.split('/')[-1]
        if segment == '':
            segment = 'products'
        return segment

    except Exception as e:
        return None
