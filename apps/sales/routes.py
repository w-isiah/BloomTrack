from flask import render_template, request, jsonify, current_app
from datetime import datetime
import mysql.connector
import traceback
from apps import get_db_connection
from apps.sales import blueprint


@blueprint.route('/sales', methods=['GET'])
def sales():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch customer data
        cursor.execute('SELECT * FROM customer_list ORDER BY name')
        customers = cursor.fetchall()

        # Fetch product data with category information using a JOIN
        cursor.execute('''
            SELECT p.*, c.name AS category_name, c.description AS category_description
            FROM product_list p
            INNER JOIN category_list c ON p.category_id = c.CategoryID
            ORDER BY c.name
        ''')
        products = cursor.fetchall()

    except mysql.connector.Error as e:
        current_app.logger.error(f"Database error: {e}")
        return "Database error", 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return render_template('sales/sale.html', customers=customers, products=products, segment='sales')





@blueprint.route('/save_sale', methods=['POST'])
def save_sale():
    try:
        # Parse the JSON data from the request body
        data = request.get_json()
        customer_id = data.get('customer_id')
        items = data.get('cart_items')
        total_price = data.get('total_price')
        discounted_price = data.get('discounted_price')

        current_app.logger.debug(f"Received data: {data}")

        # Check for missing required fields
        if not customer_id or not items:
            return jsonify({'message': 'Missing customer ID or cart items.'}), 400
        if not items:  # Check if cart is empty
            return jsonify({'message': 'Cart items cannot be empty.'}), 400

        # Establish DB connection
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Start a transaction
        connection.start_transaction()

        # Insert into sales_summary
        cursor.execute(
            'INSERT INTO sales_summary (customer_id, total_price, discounted_price) VALUES (%s, %s, %s)',
            (customer_id, total_price, discounted_price)
        )
        sale_id = cursor.lastrowid  # Get the last inserted sale ID

        # Insert each item into the sales table and update inventory
        for item in items:
            product_id = item.get('product_id')
            price = item.get('price')
            quantity = item.get('quantity')
            discount = item.get('discount', 0.00)  # Set discount to 0 if not provided
            total_item_price = item.get('total_price')
            discounted_item_price = item.get('discounted_price')

            current_app.logger.debug(f"Processing item: {item}")

            # Validate item data
            if not price or not quantity or quantity <= 0:
                return jsonify({'message': f'Invalid data for product ID {product_id}. Price or quantity is missing or invalid.'}), 400
            if total_item_price is None or discounted_item_price is None:
                return jsonify({'message': f'Missing total price or discounted price for product ID {product_id}.'}), 400

            # Insert item into the sales table
            cursor.execute(
                'INSERT INTO sales (ProductID, customer_id, price, discount, qty, total_price, discounted_price) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (product_id, customer_id, price, discount, quantity, total_item_price, discounted_item_price)
            )

            # Update product stock in inventory
            cursor.execute(
                'UPDATE product_list SET quantity = quantity - %s WHERE ProductID = %s',
                (quantity, product_id)
            )

            # Log inventory change
            cursor.execute("""
                INSERT INTO inventory_logs (product_id, quantity_change, reason, log_date)
                VALUES (%s, %s, %s, NOW())
            """, (product_id, -quantity, 'sale'))

        # Commit the transaction
        connection.commit()

        return jsonify({'message': 'Sale data added and inventory updated successfully!'}), 201

    except Exception as e:
        if connection:
            connection.rollback()

        current_app.logger.error(f"Error: {e}")
        current_app.logger.error(f"Stack Trace: {traceback.format_exc()}")
        return jsonify({'message': 'Error occurred: ' + str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@blueprint.route('/sales_view', methods=['GET', 'POST'])
def sales_view():
    start_date = datetime.now().strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Queries for sales data
    query_sales_details = """
        SELECT 
            s.salesID, 
            p.name AS product_name, 
            c.name AS customer_name,  
            s.price,
            s.discount, 
            s.qty, 
            s.date_updated
        FROM 
            sales s
        INNER JOIN 
            product_list p ON s.ProductID = p.ProductID
        INNER JOIN 
            customer_list c ON s.customer_id = c.CustomerID 
        WHERE 
            DATE(s.date_updated) BETWEEN %s AND %s
    """

    query_sales_sum = """
        SELECT 
            SUM(s.price * s.qty) AS total_sales
        FROM 
            sales s
        INNER JOIN 
            product_list p ON s.ProductID = p.ProductID
        WHERE 
            DATE(s.date_updated) BETWEEN %s AND %s
    """

    query_sales_quantity = """
        SELECT 
            SUM(s.qty) AS total_quantity
        FROM 
            sales s
        INNER JOIN 
            product_list p ON s.ProductID = p.ProductID
        WHERE 
            DATE(s.date_updated) BETWEEN %s AND %s
    """

    cursor.execute(query_sales_details, (start_date, end_date))
    sales = cursor.fetchall()

    cursor.execute(query_sales_sum, (start_date, end_date))
    total_sales = cursor.fetchone()['total_sales']

    cursor.execute(query_sales_quantity, (start_date, end_date))
    total_quantity = cursor.fetchone()['total_quantity']

    formatted_total_sales = "{:,.2f}".format(total_sales) if total_sales else '0.00'
    formatted_total_quantity = "{:,}".format(total_quantity) if total_quantity else '0'

    cursor.close()
    connection.close()

    return render_template('sales/sales_view.html',
                           sales=sales, total_quantity=formatted_total_quantity,
                           total_sales=formatted_total_sales, start_date=start_date, end_date=end_date,segment='sales_view')


@blueprint.route('/discount_percentage', methods=['GET', 'POST'])
def discount_percentage():
    if request.method == 'POST':
        try:
            original_price = float(request.form['original_price'])
            discounted_price = float(request.form['discounted_price'])

            if original_price <= 0 or discounted_price < 0:
                raise ValueError("Prices must be positive numbers.")

            discount_amount = original_price - discounted_price
            discount_percentage = (discount_amount / original_price) * 100

            return render_template('sales/discount_percentage.html',
                                   original_price=original_price, 
                                   discounted_price=discounted_price,
                                   discount_amount=discount_amount,
                                   discount_percentage=discount_percentage)
        except (ValueError, TypeError):
            error = "Please enter valid numeric values."
            return render_template('sales/discount_percentage.html',  error=error)

    return render_template('sales/discount_percentage.html')


@blueprint.route('/<template>')
def route_template(template):
    """Renders a dynamic template page."""
    try:
        if not template.endswith('.html'):
            template += '.html'

        segment = get_segment(request)

        return render_template(f"home/{template}", segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except Exception as e:
        return render_template('home/page-500.html'), 500


def get_segment(request):
    """Extracts the last part of the URL to determine the current page."""
    try:
        segment = request.path.split('/')[-1]
        return segment if segment else 'sales'
    except Exception:
        return None
