from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from collections import defaultdict
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

from apps import get_db_connection
from apps.sales import blueprint


# Keep only one definition of get_kampala_time
def get_kampala_time():
    kampala = pytz.timezone("Africa/Kampala")
    return datetime.now(kampala)

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
            ORDER BY name
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
    connection = None
    cursor = None
    try:
        if 'id' not in session:
            return jsonify({'message': 'You must be logged in to make a sale.'}), 401

        user_id = session['id']
        data = request.get_json()
        customer_id = data.get('customer_id')
        items = data.get('cart_items')
        total_price = data.get('total_price')
        discounted_price = data.get('discounted_price')

        current_app.logger.debug(f"Received data: {data}")

        # Validate required fields
        if not customer_id or not items:
            return jsonify({'message': 'Missing customer ID or cart items.'}), 400
        if len(items) == 0:
            return jsonify({'message': 'Cart items cannot be empty.'}), 400
        if not total_price or discounted_price is None:
            return jsonify({'message': 'Total price or discounted price missing.'}), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()

        # Insert into sales_summary
        cursor.execute("""
            INSERT INTO sales_summary (customer_id, total_price, discounted_price)
            VALUES (%s, %s, %s)
        """, (customer_id, total_price, discounted_price))
        sale_id = cursor.lastrowid

        for item in items:
            product_id = item.get('product_id')
            price = item.get('price')
            quantity = item.get('quantity')
            discount = item.get('discount', 0.00)
            total_item_price = item.get('total_price')
            discounted_item_price = item.get('discounted_price')

            current_app.logger.debug(f"Processing item: {item}")

            if not price or not quantity or quantity <= 0:
                return jsonify({'message': f'Invalid data for product ID {product_id}.'}), 400
            if total_item_price is None or discounted_item_price is None:
                return jsonify({'message': f'Missing price data for product ID {product_id}.'}), 400

            # Insert sale item with date_updated and type='sales'
            log_time = get_kampala_time()
            cursor.execute("""
                INSERT INTO sales (
                    ProductID, customer_id, price, discount, qty, total_price,
                    discounted_price, date_updated, type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                product_id, customer_id, price, discount, quantity,
                total_item_price, discounted_item_price, log_time, 'sales'
            ))

            # Update inventory
            cursor.execute("""
                UPDATE product_list SET quantity = quantity - %s WHERE ProductID = %s
            """, (quantity, product_id))

            # Log inventory change with Kampala time
            cursor.execute("""
                INSERT INTO inventory_logs (product_id, quantity_change, reason, log_date, user_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (product_id, -quantity, 'sale', log_time, user_id))

        connection.commit()
        return jsonify({'message': 'Sale data added and inventory updated successfully!'}), 201

    except Exception as e:
        if connection:
            connection.rollback()
        current_app.logger.error(f"Error: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'message': 'Error occurred: ' + str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()



@blueprint.route('/sales_view', methods=['GET', 'POST'])
def sales_view():
    if 'id' not in session:
        flash('Login required to access this page.', 'error')
        return redirect(url_for('authentication_blueprint.login'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Fetch current user
        cursor.execute("SELECT * FROM users WHERE id = %s", (session['id'],))
        user = cursor.fetchone()
        if not user:
            flash('User not found. Please log in again.', 'error')
            return redirect(url_for('authentication_blueprint.login'))

        # Default dates
        today = datetime.today().strftime('%Y-%m-%d')
        start_date = end_date = today
        searched = False

        # Handle filter form
        if request.method == 'POST':
            start_date = request.form.get('start_date') or today
            end_date = request.form.get('end_date') or today
            searched = True

        # Fetch sales ordered by date_updated DESC
        cursor.execute("""
            SELECT 
                s.salesID,
                p.name AS product_name,
                c.name AS customer_name,
                p.price AS current_price,
                s.discount,
                s.qty,
                s.date_updated
            FROM sales s
            JOIN product_list p ON s.ProductID = p.ProductID
            JOIN customer_list c ON s.customer_id = c.CustomerID
            WHERE s.type = 'sales' AND DATE(s.date_updated) BETWEEN %s AND %s
            ORDER BY s.date_updated DESC
        """, (start_date, end_date))
        sales_raw = cursor.fetchall()

        sales = []
        total_sales = Decimal("0.00")
        total_before_discount = Decimal("0.00")
        total_quantity = 0

        for row in sales_raw:
            try:
                unit_price = row['current_price'] or Decimal("0.00")
                discount = Decimal(row['discount']) if row['discount'] is not None else Decimal("0.00")
                qty = row['qty'] or 0

                discounted_unit_price = unit_price * (Decimal("1.00") - discount / Decimal("100"))
                line_total = discounted_unit_price * qty

                row['discounted_price'] = round(discounted_unit_price, 2)
                row['line_total'] = round(line_total, 2)

                total_sales += line_total
                total_before_discount += unit_price * qty
                total_quantity += qty

                sales.append(row)
            except (InvalidOperation, TypeError) as e:
                print(f"Skipping invalid sales record: {row} - {e}")
                continue

        total_discount_given = total_before_discount - total_sales

        # Fetch expenses with category info
        cursor.execute("""
            SELECT 
                s.salesID,
                s.ProductID AS expense_code,
                s.expense_name,
                c.name AS customer_name,
                cat.name AS category_name,
                s.price AS amount,
                s.description,
                s.date_updated
            FROM sales s
            JOIN customer_list c ON s.customer_id = c.CustomerID
            LEFT JOIN category_list cat ON s.category_id = cat.CategoryID
            WHERE s.type = 'expense' AND DATE(s.date_updated) BETWEEN %s AND %s
            ORDER BY s.date_updated DESC
        """, (start_date, end_date))
        expenses = cursor.fetchall()

        # Total expenses
        cursor.execute("""
            SELECT SUM(s.price) AS total_expenses
            FROM sales s
            WHERE s.type = 'expense' AND DATE(s.date_updated) BETWEEN %s AND %s
        """, (start_date, end_date))
        expense_total = cursor.fetchone()
        total_expenses = expense_total['total_expenses'] or Decimal("0.00")

    finally:
        cursor.close()
        connection.close()

    return render_template(
        'sales/sales_view.html',
        user=user,
        sales=sales,
        expenses=expenses,
        total_sales=f"{total_sales:,.2f}",
        total_quantity=f"{total_quantity:,}",
        total_before_discount=f"{total_before_discount:,.2f}",
        total_discount_given=f"{total_discount_given:,.2f}",
        total_expenses=f"{Decimal(total_expenses):,.2f}",
        start_date=start_date,
        end_date=end_date,
        searched=searched,
        segment='sales_view'
    )













@blueprint.route('/dashboard_view', methods=['GET', 'POST'])
def dashboard_view():
    # Default date range: last 30 days
    end_date = datetime.today()
    start_date = end_date - timedelta(days=30)

    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            pass

    # Format strings for SQL
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Fetch sales
        cursor.execute("""
            SELECT 
                s.salesID,
                p.name AS product_name,
                c.name AS customer_name,
                p.price AS current_price,
                s.discount,
                s.qty,
                s.date_updated
            FROM sales s
            JOIN product_list p ON s.ProductID = p.ProductID
            JOIN customer_list c ON s.customer_id = c.CustomerID
            WHERE s.type = 'sales' AND DATE(s.date_updated) BETWEEN %s AND %s
        """, (start_date_str, end_date_str))
        sales = cursor.fetchall()

        # Fetch expenses
        cursor.execute("""
            SELECT 
                s.salesID,
                s.ProductID AS expense_code,
                s.expense_name,
                c.name AS customer_name,
                s.price AS amount,
                s.description,
                s.date_updated
            FROM sales s
            JOIN customer_list c ON s.customer_id = c.CustomerID
            WHERE s.type = 'expense' AND DATE(s.date_updated) BETWEEN %s AND %s
        """, (start_date_str, end_date_str))
        expenses = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    # Initialize totals
    total_sales_discounted = Decimal('0.00')
    total_before_discount = Decimal('0.00')
    total_discount_given = Decimal('0.00')
    total_expenses = Decimal('0.00')
    total_quantity = 0
    customers_set = set()

    sales_time_series = defaultdict(Decimal)
    expenses_time_series = defaultdict(Decimal)
    discount_time_series = defaultdict(list)

    sales_by_product = defaultdict(Decimal)
    sales_qty_by_product = defaultdict(int)
    sales_by_customer = defaultdict(Decimal)

    discount_brackets = {
        '0%': 0,
        '1-10%': 0,
        '11-20%': 0,
        '>20%': 0
    }

    # Process sales
    for s in sales:
        unit_price = s['current_price'] or Decimal('0.00')
        discount = Decimal(s['discount']) if s['discount'] is not None else Decimal('0.00')
        qty = s['qty'] or 0

        discounted_price = unit_price * (Decimal('1') - discount / Decimal('100'))
        line_total_discounted = discounted_price * qty
        line_total_before = unit_price * qty
        line_discount = (unit_price - discounted_price) * qty

        total_sales_discounted += line_total_discounted
        total_before_discount += line_total_before
        total_discount_given += line_discount
        total_quantity += qty
        customers_set.add(s['customer_name'])

        date_key = s['date_updated'].strftime('%Y-%m-%d')
        sales_time_series[date_key] += line_total_discounted
        discount_time_series[date_key].append(float(discount))

        sales_by_product[s['product_name']] += line_total_discounted
        sales_qty_by_product[s['product_name']] += qty
        sales_by_customer[s['customer_name']] += line_total_discounted

        # Discount brackets
        if discount == 0:
            discount_brackets['0%'] += 1
        elif 1 <= discount <= 10:
            discount_brackets['1-10%'] += 1
        elif 11 <= discount <= 20:
            discount_brackets['11-20%'] += 1
        else:
            discount_brackets['>20%'] += 1

    # Process expenses
    for e in expenses:
        amount = Decimal(e['amount']) if e['amount'] else Decimal('0.00')
        total_expenses += amount
        date_key = e['date_updated'].strftime('%Y-%m-%d')
        expenses_time_series[date_key] += amount

    # Average discount per day
    avg_discount_time_series = {}
    for date_key, discounts in discount_time_series.items():
        avg_discount_time_series[date_key] = round(sum(discounts) / len(discounts), 2) if discounts else 0

    # Sort time series
    def sort_dict(d):
        return dict(sorted(d.items()))

    sales_time_series = sort_dict(sales_time_series)
    expenses_time_series = sort_dict(expenses_time_series)
    avg_discount_time_series = sort_dict(avg_discount_time_series)

    # Convert Decimals to float for JSON-safe rendering
    def dec_to_float(d):
        return float(d.quantize(Decimal('0.01')))

    context = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'searched': request.method == 'POST',
        'total_sales': dec_to_float(total_sales_discounted),
        'total_before_discount': dec_to_float(total_before_discount),
        'total_discount_given': dec_to_float(total_discount_given),
        'total_expenses': dec_to_float(total_expenses),
        'total_quantity': total_quantity,
        'num_customers': len(customers_set),
        'sales_time_series': {k: dec_to_float(v) for k, v in sales_time_series.items()},
        'expenses_time_series': {k: dec_to_float(v) for k, v in expenses_time_series.items()},
        'avg_discount_time_series': avg_discount_time_series,
        'sales_by_product': {k: dec_to_float(v) for k, v in sales_by_product.items()},
        'sales_qty_by_product': dict(sales_qty_by_product),
        'sales_by_customer': {k: dec_to_float(v) for k, v in sales_by_customer.items()},
        'discount_brackets': dict(discount_brackets),
    }

    return render_template('sales/dashboard.html', **context)


@blueprint.route('/edit_sale/<int:salesID>', methods=['GET', 'POST'])
def edit_sale(salesID):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Fetch the sale record
        cursor.execute('SELECT * FROM sales WHERE salesID = %s', (salesID,))
        sale = cursor.fetchone()

        if not sale:
            flash("Sale record not found!", "warning")
            return redirect(url_for('sales_blueprint.sales_view'))

        # Get customers list
        cursor.execute('SELECT CustomerID, name FROM customer_list')
        customers = cursor.fetchall()

        if request.method == 'POST':
            # Get form data
            customer_id = request.form.get('customer_id')
            price = request.form.get('price')
            discount = request.form.get('discount') or 0
            qty = request.form.get('qty')
            date_updated_str = request.form.get('date_updated')

            # Validate and parse date_updated
            try:
                # Convert string to datetime object (local time)
                date_updated = datetime.strptime(date_updated_str, '%Y-%m-%dT%H:%M')
                # Convert to Kampala timezone aware datetime
                kampala_tz = pytz.timezone("Africa/Kampala")
                date_updated = kampala_tz.localize(date_updated)
                # Format for SQL
                date_updated_formatted = date_updated.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                flash("Invalid date format.", "danger")
                return redirect(request.url)

            # Update the sale record
            update_query = '''
                UPDATE sales 
                SET customer_id = %s,
                    price = %s,
                    discount = %s,
                    qty = %s,
                    date_updated = %s
                WHERE salesID = %s
            '''
            cursor.execute(update_query, (
                customer_id,
                price,
                discount,
                qty,
                date_updated_formatted,
                salesID
            ))
            connection.commit()

            flash("Sale updated successfully!", "success")
            return redirect(url_for('sales_blueprint.sales_view'))

        # GET request — render template with sale and customers
        return render_template('sales/edit_sale.html', sale=sale, customers=customers)

    finally:
        cursor.close()
        connection.close()


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



@blueprint.route('/delete_sale/<int:sales_id>',methods=['GET', 'POST'])
def delete_sale(sales_id):
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # 1. Fetch the sale record
                cursor.execute("""
                    SELECT qty, ProductID, price 
                    FROM sales 
                    WHERE salesID = %s AND type = 'sales'
                """, (sales_id,))
                sale = cursor.fetchone()

                if not sale:
                    flash("Sale record not found or is not of type 'sales'.", "warning")
                    return redirect(url_for('sales_blueprint.sales_view'))

                product_id = sale['ProductID']
                restored_qty = sale['qty']
                sale_price = sale['price']

                # 2. Restore product quantity
                cursor.execute("""
                    UPDATE product_list 
                    SET quantity = quantity + %s 
                    WHERE ProductID = %s
                """, (restored_qty, product_id))

                # 3. Log inventory change
                cursor.execute("""
                    INSERT INTO inventory_logs (
                        product_id, quantity_change, log_date, reason, user_id, old_price
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    product_id,
                    restored_qty,
                    get_kampala_time(),  # Using Kampala local time
                    "Sale deleted, stock restored",
                    session.get('id'),
                    sale_price
                ))

                # 4. Delete the sale
                cursor.execute("DELETE FROM sales WHERE salesID = %s", (sales_id,))
                connection.commit()

                flash("Sale deleted and inventory log updated.", "success")

    except Exception as e:
        flash(f"Error deleting sale: {str(e)}", "danger")

    return redirect(url_for('sales_blueprint.sales_view'))




@blueprint.route('/<template>')
def route_template(template):
    """Renders a dynamic template page."""
    try:
        if not template.endswith('.html'):
            template += '.html'

        segment = get_segment(request)

        return render_template(f"sales/{template}", segment=segment)

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