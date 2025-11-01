import os
import random
import logging
from flask import render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from mysql.connector import Error
from apps import get_db_connection
from apps.expenses import blueprint
import mysql.connector
from datetime import datetime
import pytz

# Function to get current time in Kampala timezone
def get_kampala_time():
    kampala = pytz.timezone("Africa/Kampala")
    return datetime.now(kampala)





@blueprint.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch categories for dropdown
    cursor.execute('SELECT * FROM category_list ORDER BY name')
    categories = cursor.fetchall()

    # Fetch customers for dropdown
    cursor.execute('SELECT CustomerID, name FROM customer_list ORDER BY name')
    customers = cursor.fetchall()

    # --- NEW: Fetch farms for dropdown ---
    cursor.execute('SELECT farm_id, name FROM farm_list ORDER BY name')
    farms = cursor.fetchall()
    # -------------------------------------

    if request.method == 'POST':
        # Get form data
        expense_name = request.form.get('expense_name', '').strip()
        price = request.form.get('price', '').strip()
        customer_id = request.form.get('customer_id')
        category_id = request.form.get('category_id')
        farm_id = request.form.get('farm_id')  # <-- NEW: Get Farm ID
        description = request.form.get('description', '').strip()

        # Basic validation (Updated to include farm_id)
        print('1',expense_name,'2',price,'3',customer_id,'4',category_id,'5',farm_id)
        if not expense_name or not price or not customer_id or not category_id or not farm_id:
            flash("Please fill in all required fields", "danger")
            return redirect(request.url)

        try:
            price = float(price)
            if price <= 0:
                raise ValueError("Price must be positive")
        except ValueError:
            flash("Price must be a valid positive number.", "danger")
            return redirect(request.url)

        # Auto-generated/static fields
        product_id = f'EXP-{int(price * 100)}'  # Example unique ID
        expense_type = 'expense'
        qty = 1
        discount = 0.0
        discounted_price = price
        total_price = price
        date_added = get_kampala_time()  # Kampala timezone

        # Insert into sales table including category_id and farm_id
        try:
            cursor.execute('''
                INSERT INTO sales
                    (ProductID, customer_id, category_id, type, price, discount, qty, discounted_price, total_price, description, expense_name, date_updated, farm_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                product_id, customer_id, category_id, expense_type, price,
                discount, qty, discounted_price, total_price,
                description, expense_name, date_added, farm_id  # <-- NEW: Pass Farm ID
            ))

            connection.commit()
            flash("Expense saved successfully!", "success")
            return redirect(url_for('expenses_blueprint.add_expense'))

        except Exception as e:
            connection.rollback()
            flash(f"Error saving expense: {e}", "danger")

    cursor.close()
    connection.close()

    return render_template(
        'expenses/add_expense.html',
        categories=categories,
        customers=customers,
        farms=farms  # <-- NEW: Pass farms to template
    )




from datetime import datetime

@blueprint.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Fetch the existing expense
        cursor.execute('SELECT * FROM sales WHERE salesID = %s', (expense_id,))
        expense = cursor.fetchone()

        if not expense:
            flash("Expense not found!", "warning")
            return redirect(url_for('expenses_blueprint.list_expenses'))

        # Fetch customers, categories, and farms for dropdowns
        cursor.execute('SELECT CustomerID, name FROM customer_list ORDER BY name')
        customers = cursor.fetchall()

        cursor.execute('SELECT * FROM category_list ORDER BY name')
        categories = cursor.fetchall()
        
        # NEW: Fetch farms list
        cursor.execute('SELECT farm_id, name FROM farm_list ORDER BY name')
        farms = cursor.fetchall()

        if request.method == 'POST':
            # Get form data
            customer_id = request.form.get('customer_id')
            category_id = request.form.get('category_id')
            farm_id = request.form.get('farm_id')  # NEW: Get Farm ID from form
            expense_name = request.form.get('expense_name', '').strip()
            description = request.form.get('description', '').strip()
            amount = request.form.get('amount', '').strip()
            date_updated_str = request.form.get('date_updated')

            # Validation
            # NEW: Included farm_id in validation
            if not customer_id or not category_id or not farm_id or not expense_name or not amount or not date_updated_str:
                flash("Please fill in all required fields", "danger")
                return redirect(request.url)

            try:
                amount = float(amount)
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                flash("Amount must be a valid positive number.", "danger")
                return redirect(request.url)

            try:
                # Convert datetime-local string to datetime object
                date_updated = datetime.strptime(date_updated_str, "%Y-%m-%dT%H:%M")
            except ValueError:
                flash("Invalid date/time format.", "danger")
                return redirect(request.url)

            # Update the expense record including farm_id
            update_query = '''
                UPDATE sales
                SET customer_id = %s,
                    category_id = %s,
                    farm_id = %s,  -- ADDED farm_id to the query
                    expense_name = %s,
                    description = %s,
                    price = %s,
                    discounted_price = %s,
                    total_price = %s,
                    date_updated = %s
                WHERE salesID = %s
            '''
            cursor.execute(update_query, (
                customer_id,
                category_id,
                farm_id,  # ADDED farm_id parameter
                expense_name,
                description,
                amount,
                amount,  # discounted_price same as amount for expense
                amount,  # total_price same as amount for expense
                date_updated,
                expense_id
            ))

            connection.commit()
            flash("Expense updated successfully!", "success")
            # Assuming you want to redirect to the sales view or expense list after update
            return redirect(url_for('sales_blueprint.sales_view')) 

        # If GET request, render the template
        return render_template(
            'expenses/edit_expenses.html',
            categories=categories,
            expense=expense,
            customers=customers,
            farms=farms  # NEW: Pass farms list to the template
        )

    finally:
        cursor.close()
        connection.close()

@blueprint.route('/delete_expense/<string:get_id>')
def delete_expense(get_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('DELETE FROM sales WHERE salesID = %s', (get_id,))
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('sales_blueprint.sales_view'))

    
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
