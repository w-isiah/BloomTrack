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






@blueprint.route('/products')
def products():
    """Renders the 'products' page with stock status included."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(''' 
            SELECT 
                p.*, 
                c.name AS category_name, 
                f.name AS farm_name,        -- Farm name
                p.stock_status,             -- Stock status
                (p.quantity * p.price) AS total_price
            FROM 
                product_list p
            JOIN 
                category_list c ON p.category_id = c.CategoryID
            LEFT JOIN 
                farm_list f ON p.farm_id = f.farm_id
            ORDER BY 
                p.name
        ''')
        products = cursor.fetchall()

        # Assuming calculate_formatted_totals is defined elsewhere
        formatted_total_sum, formatted_total_price = calculate_formatted_totals(products)

    except Error as e:
        logging.error(f"Database error: {e}")
        flash("An error occurred while fetching products.", "error")
        return render_template('products/page-500.html'), 500

    finally:
        cursor.close()
        connection.close()

    return render_template(
        'products/products.html',
        products=products,
        formatted_total_price=formatted_total_price,
        formatted_total_sum=formatted_total_sum,
        segment='products'
    )



























from flask import request, jsonify, render_template, Blueprint
import uuid
import pytz
from datetime import datetime
from apps import get_db_connection


# Helper: Kampala time
def get_kampala_time():
    kampala = pytz.timezone("Africa/Kampala")
    return datetime.now(kampala)

# ------------------------
# 1️⃣ AJAX endpoint to log device info
# ------------------------














from flask import Blueprint, request, jsonify
import uuid



@blueprint.route('/api/log_device_info', methods=['GET'])
def log_device_info():
    """
    GET endpoint to log device information from front-end via query parameters.
    """
    try:
        # Extract device info from query parameters
        ip_address = request.args.get('ip_address', request.remote_addr)
        device_id = request.args.get('device_id', str(uuid.uuid4()))
        mac_address = request.args.get('mac_address', None)
        country = request.args.get('country', 'Unknown')
        state = request.args.get('state', 'Unknown')
        received_at = get_kampala_time()

        print(f"📱 GET Device data: {device_id} | {ip_address} | {country}")

        # Save to DB
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO system_info 
            (ip_address, mac_address, device_id, country, state, received_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ip_address, mac_address, device_id, country, state, received_at))
        
        conn.commit()

        return jsonify({
            "status": "success",
            "device_id": device_id,
            "method": "GET",
            "message": "Device info logged successfully via GET"
        }), 200

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

            





# ------------------------
# 2️⃣ Main products route
# ------------------------
@blueprint.route('/jacaranda_plant_nurseries_maya_bulwanyi')
def products_marketing():
    """
    Render products page. Device info will be logged via AJAX.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch products
        cursor.execute('''
            SELECT 
                p.*, 
                c.name AS category_name, 
                p.stock_status
            FROM product_list p
            JOIN category_list c ON p.category_id = c.CategoryID
            ORDER BY p.name
        ''')
        products = cursor.fetchall()

        cursor.execute('SELECT * FROM category_list')
        categories = cursor.fetchall()

        current_year = datetime.now().year

    finally:
        cursor.close()
        conn.close()

    return render_template(
        'products/products_marketing.html',
        products=products,
        categories=categories,
        current_year=current_year
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









@blueprint.route('/add_product', methods=['GET', 'POST'])
def add_product():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 1️⃣ Fetch categories and farms for dropdowns
    cursor.execute('SELECT * FROM category_list ORDER BY name')
    categories = cursor.fetchall()

    cursor.execute('SELECT farm_id, name FROM farm_list ORDER BY name')
    farm_options = cursor.fetchall()

    # 2️⃣ Generate a unique random SKU
    random_num = random.randint(1005540, 9978799)
    while True:
        cursor.execute('SELECT 1 FROM product_list WHERE sku = %s', (random_num,))
        if not cursor.fetchone():
            break
        random_num = random.randint(1005540, 9978799)

    # 3️⃣ Handle form submission
    if request.method == 'POST':
        try:
            # --- Retrieve and validate form data ---
            category_id = int(request.form.get('category_id') or 0)
            sku = request.form.get('serial_no') or random_num
            price = float(request.form.get('price') or 0)
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            reorder_level = int(request.form.get('reorder_level') or 0)
            farm_id = request.form.get('farm_id')
            farm_id = int(farm_id) if farm_id else None
            stock_status = request.form.get('stock_status', 'In Stock')
            quantity = 0  # default quantity for new products

            # --- Basic validation ---
            if not (category_id and name and price and farm_id and stock_status):
                flash("Please fill in all required fields!", "warning")
                return redirect(url_for('products_blueprint.add_product'))

            # --- Prevent duplicate: same name + category + farm ---
            cursor.execute(
                '''SELECT * FROM product_list
                   WHERE category_id = %s AND name = %s AND farm_id = %s''',
                (category_id, name, farm_id)
            )
            existing_product = cursor.fetchone()
            if existing_product:
                flash("This product already exists for the selected category and farm!", "danger")
                return redirect(url_for('products_blueprint.add_product'))

            # --- Handle image upload ---
            image_file = request.files.get('image')
            image_filename = None
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_filename = f"{random_num}_{filename}"

                image_folder = os.path.join(current_app.config['UPLOAD_FOLDER'])
                os.makedirs(image_folder, exist_ok=True)

                image_path = os.path.join(image_folder, image_filename)
                image_file.save(image_path)

            # --- Insert new product record ---
            cursor.execute('''
                INSERT INTO product_list
                (category_id, sku, price, name, description, quantity, stock_status, reorder_level, image, farm_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (category_id, sku, price, name, description, quantity, stock_status, reorder_level, image_filename, farm_id))

            connection.commit()
            flash("✅ Product successfully added!", "success")
            return redirect(url_for('products_blueprint.add_product'))

        except mysql.connector.Error as err:
            connection.rollback()
            flash(f"Database error: {err}", "danger")

        except ValueError:
            flash("Invalid input: please check your entries!", "warning")

        finally:
            cursor.close()
            connection.close()

    else:
        # GET request — render the form
        cursor.close()
        connection.close()

    return render_template(
        'products/add_product.html',
        random_num=random_num,
        categories=categories,
        farm_options=farm_options,
        segment='add_product'
    )






@blueprint.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 1️⃣ Fetch the existing product
    cursor.execute('SELECT * FROM product_list WHERE ProductID = %s', (product_id,))
    product = cursor.fetchone()
    if not product:
        flash("Product not found!", "danger")
        cursor.close()
        connection.close()
        return redirect(url_for('products_blueprint.products'))

    # 2️⃣ Fetch categories and farms for dropdowns
    cursor.execute('SELECT * FROM category_list ORDER BY name')
    categories = cursor.fetchall()

    cursor.execute('SELECT farm_id, name FROM farm_list ORDER BY name')
    farm_options = cursor.fetchall()

    # 3️⃣ Handle form submission
    if request.method == 'POST':
        try:
            # --- Retrieve and validate form data ---
            category_id = int(request.form.get('category_id') or 0)
            sku = request.form.get('serial_no', product['sku'])
            price = float(request.form.get('price') or product['price'])
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            reorder_level = int(request.form.get('reorder_level') or product['reorder_level'])
            farm_id = request.form.get('farm_id')
            farm_id = int(farm_id) if farm_id else None
            stock_status = request.form.get('stock_status', product.get('stock_status', 'In Stock'))

            # --- Basic validation ---
            if not (category_id and name and price and farm_id and stock_status):
                flash("Please fill in all required fields!", "warning")
                return redirect(url_for('products_blueprint.edit_product', product_id=product_id))

            # --- Prevent duplicate for other products ---
            cursor.execute('''
                SELECT * FROM product_list
                WHERE category_id = %s AND name = %s AND farm_id = %s AND ProductID != %s
            ''', (category_id, name, farm_id, product_id))
            if cursor.fetchone():
                flash("Another product with this name already exists for the selected category and farm!", "danger")
                return redirect(url_for('products_blueprint.edit_product', product_id=product_id))

            # --- Handle image upload ---
            image_filename = product['image']  # default to existing
            image_file = request.files.get('image')
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_filename = f"{product_id}_{filename}"

                image_folder = os.path.join(current_app.config['UPLOAD_FOLDER'])
                os.makedirs(image_folder, exist_ok=True)

                image_path = os.path.join(image_folder, image_filename)
                image_file.save(image_path)

            # --- Track price change ---
            old_price = float(product['price'])
            price_change = price - old_price if price != old_price else None

            # --- Update product record ---
            cursor.execute('''
                UPDATE product_list
                SET category_id = %s, sku = %s, price = %s, name = %s, description = %s,
                    reorder_level = %s, image = %s, farm_id = %s, stock_status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE ProductID = %s
            ''', (category_id, sku, price, name, description, reorder_level, image_filename, farm_id, stock_status, product_id))

            # --- Log price change if needed ---
            if price_change is not None:
                cursor.execute('''
                    INSERT INTO inventory_logs (product_id, quantity_change, log_date, reason, price_change, old_price)
                    VALUES (%s, 0, CURRENT_TIMESTAMP, %s, %s, %s)
                ''', (product_id, 'Price Update', price_change, old_price))

            connection.commit()
            flash("✅ Product updated successfully!", "success")
            return redirect(url_for('products_blueprint.products'))

        except mysql.connector.Error as err:
            connection.rollback()
            flash(f"Database error: {err}", "danger")

        except ValueError:
            flash("Invalid input: please check your entries!", "warning")

        finally:
            cursor.close()
            connection.close()

    else:
        # GET request — render the form
        cursor.close()
        connection.close()

    return render_template(
        'products/edit_product.html',
        product=product,
        categories=categories,
        farm_options=farm_options,
        segment='edit_product'
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
