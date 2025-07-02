import os
import random
import logging
from flask import render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from mysql.connector import Error
from apps import get_db_connection
from apps.expenses import blueprint
import mysql.connector



# Route to add a new expense


@blueprint.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Get customers for dropdown
    cursor.execute('SELECT CustomerID, name FROM customer_list ORDER BY name')
    customers = cursor.fetchall()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '').strip()
        customer_id = request.form.get('customer_id')
        description = request.form.get('description', '').strip()  # New description field

        # Basic validation
        if not name or not price or not customer_id:
            flash("Please fill in all required fields", "danger")
            return redirect(request.url)

        try:
            price = float(price)
            if price <= 0:
                raise ValueError
        except ValueError:
            flash("Price must be a positive number.", "danger")
            return redirect(request.url)

        # Static or derived fields
        product_id = f'EXP-{int(float(price) * 100)}'  # Optional logic to make it unique
        expense_type = 'expense'
        qty = 1
        discount = 0
        discounted_price = price
        total_price = price

        try:
            cursor.execute('''
                INSERT INTO sales 
                    (ProductID, customer_id, type, price, discount, qty, discounted_price, total_price, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                product_id, customer_id, expense_type, price,
                discount, qty, discounted_price, total_price, description
            ))

            connection.commit()
            flash("Expense saved successfully in sales table!", "success")
            return redirect(url_for('expenses_blueprint.add_expense'))
        except Exception as e:
            connection.rollback()
            flash(f"Error saving expense: {e}", "danger")

    cursor.close()
    connection.close()

    return render_template('expenses/add_expense.html', customers=customers)











# Route to edit an existing expense
@blueprint.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    # Connect to the database
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch the expense data from the database
    cursor.execute('SELECT * FROM expense_list WHERE expenseID = %s', (expense_id,))
    expense = cursor.fetchone()

    if not expense:
        flash("expense not found!")
        return redirect(url_for('expenses_blueprint.expenses'))  # Redirect to a expenses list page or home

    # Fetch categories from the database for the dropdown
    cursor.execute('SELECT * FROM category_list')
    categories = cursor.fetchall()

    if request.method == 'POST':
        # Get the form data
        category_id = request.form.get('category_id')
        sku = request.form.get('serial_no')
        price = request.form.get('price')
        name = request.form.get('name')
        description = request.form.get('description')
        reorder_level = request.form.get('reorder_level')

        # Handle image upload
        image_filename = expense['image']  # Default to existing image if no new one is uploaded
        image_file = request.files.get('image')

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_filename = f"{expense_id}_{filename}"  # Rename with expense ID to avoid conflicts
            
            # Ensure the directory exists before saving the file
            image_folder = os.path.join(current_app.config['UPLOAD_FOLDER'])
            if not os.path.exists(image_folder):
                os.makedirs(image_folder)  # Create the folder if it doesn't exist

            image_path = os.path.join(image_folder, image_filename)
            image_file.save(image_path)  # Save new image

        # Calculate the price change if the price has been updated
        old_price = expense['price']
        price_change = None

        if price != old_price:
            price_change = float(price) - float(old_price)  # Calculate the price change

        # Update the expense data in the database
        cursor.execute(''' 
            UPDATE expense_list
            SET category_id = %s, sku = %s, price = %s, name = %s, description = %s,
                 reorder_level = %s, image = %s, updated_at = CURRENT_TIMESTAMP
            WHERE expenseID = %s
        ''', (category_id, sku, price, name, description, reorder_level, image_filename, expense_id))

        # If there's a price change, insert it into the inventory_logs table
        if price_change is not None:
            cursor.execute('''
                INSERT INTO inventory_logs (expense_id, quantity_change, log_date, reason, price_change, old_price)
                VALUES (%s, 0, CURRENT_TIMESTAMP, %s, %s, %s)
            ''', (expense_id, 'Price Update', price_change, old_price))

        # Commit the transaction
        connection.commit()

        flash("expense updated successfully!")
        return redirect(url_for('expenses_blueprint.expenses'))

 

    cursor.close()
    connection.close()

    return render_template('expenses/edit_expense.html', expense=expense, categories=categories)




@blueprint.route('/delete_expense/<string:get_id>')
def delete_expense(get_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('DELETE FROM expense_list WHERE expenseID = %s', (get_id,))
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('expenses_blueprint.expenses'))


@blueprint.route('/<template>')
def route_template(template):
    try:
        # Ensure the template ends with '.html' for correct render
        if not template.endswith('.html'):
            template += '.html'

        segment = get_segment(request)

        return render_template("expenses/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('expenses/page-404.html'), 404

    except Exception as e:
        return render_template('expenses/page-500.html'), 500


def get_segment(request):
    """Extracts the last part of the URL path to identify the current page."""
    try:
        segment = request.path.split('/')[-1]
        if segment == '':
            segment = 'expenses'
        return segment

    except Exception as e:
        return None
