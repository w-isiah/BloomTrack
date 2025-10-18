from apps.farms import blueprint # NOTE: You'll likely need to change 'farms' to 'farms' in your actual project structure
from flask import render_template, request, redirect, url_for, flash, session
from flask import Flask
from werkzeug.utils import secure_filename
from mysql.connector import Error
from datetime import datetime
import os
import random
import logging
from apps import get_db_connection
# NOTE: The imports below for mysql.connector are not necessary as they're not explicitly used in the functions:
# import mysql.connector

# Start of FARM handling
# ----------------------------------------------------------------------

# View all farms
@blueprint.route('/farms')
def farms():
    """Retrieves and displays a list of all farms."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    # Changed from 'farm_list' to 'farm_list'
    cursor.execute('SELECT * FROM farm_list')
    # Changed variable name from 'farm' to 'farm' (plural)
    farms_list = cursor.fetchall()
    cursor.close()
    connection.close()
    # Changed template path from 'farms/' to 'farms/'
    return render_template('farms/farms.html', farms=farms_list, segment='farms')


# Add a new farm
@blueprint.route('/add_farm', methods=['GET', 'POST'])
def add_farm():
    """Handles adding a new farm via a form submission."""
    if request.method == 'POST':
        # Changed form field names from 'farm_name', 'contact', 'address'
        name = request.form.get('farm_name')
        location = request.form.get('location')
        owner_contact = request.form.get('owner_contact') # New field to replace 'contact'

        # Ensure the form data is filled
        if not name or not location:
            flash("Please fill out the farm Name and Location!")
            # Changed template path from 'farm/' to 'farms/'
            return render_template('farms/add_farm.html', segment='add_farm')

        # Check if farm already exists
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        # Changed table 'farm_list' and column 'name' to 'farm_list' and 'name'
        cursor.execute('SELECT * FROM farm_list WHERE name = %s', (name,))
        farm = cursor.fetchone()

        if farm:
            flash("Farm already exists!")
        else:
            # Insert the new farm. Changed columns and parameters
            cursor.execute('INSERT INTO farm_list (name, location, owner_contact) VALUES (%s, %s, %s)',
                           (name, location, owner_contact))
            connection.commit()
            flash("You have successfully registered a farm!")

        cursor.close()
        connection.close()
        # Changed template path from 'farms/' to 'farms/'
        return render_template('farms/add_farm.html', segment='add_farm')

    # Handle GET request
    return render_template('farms/add_farm.html', segment='add_farm')


# Edit an existing farm
@blueprint.route('/edit_farm/<int:farm_id>', methods=['POST', 'GET'])
def edit_farm(farm_id):
    """Handles editing the details of an existing farm."""
    if request.method == 'POST':
        # Get data from the form
        name = request.form['name']
        location = request.form['location']
        owner_contact = request.form['owner_contact']
        # Renamed 'loyaltypoints' to a farm-relevant field, like 'size_acres'
        size_acres = request.form.get('size_acres')

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            # Updated table, columns, and WHERE clause from farm to farm
            cursor.execute("""
                UPDATE farm_list
                SET name=%s, location=%s, owner_contact=%s, size_acres=%s
                WHERE FarmID=%s
            """, (name, location, owner_contact, size_acres, farm_id))
            connection.commit()

            flash("Farm Data Updated Successfully", "success")
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
        finally:
            cursor.close()
            connection.close()
            # NOTE: Assuming the blueprint name is now 'farms_blueprint' in your main app
            return redirect(url_for('farms_blueprint.farms')) # Keep 'farms_blueprint' if not renamed

    elif request.method == 'GET':
        # Retrieve farm data to pre-fill the form
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        # Updated table and WHERE clause
        cursor.execute("SELECT * FROM farm_list WHERE FarmID = %s", (farm_id,))
        farm = cursor.fetchone()
        cursor.close()
        connection.close()

        if farm:
            # Changed template path from 'farms/' to 'farms/'
            return render_template('farms/edit_farm.html', farm=farm)
        else:
            flash("Farm not found.", "danger")
            return redirect(url_for('farms_blueprint.farms'))


# Delete a farm
@blueprint.route('/delete_farm/<string:get_id>')
def delete_farm(get_id):
    """Deletes a farm record using the provided ID."""
    connection = get_db_connection()
    cursor = connection.cursor()

    # Updated table and WHERE clause
    cursor.execute('DELETE FROM farm_list WHERE FarmID = %s', (get_id,))

    connection.commit()
    cursor.close()
    connection.close()

    # Redirect to the 'farms' route
    return redirect(url_for('farms_blueprint.farms'))


# ----------------------------------------------------------------------
# Dynamic route for rendering other templates (Unchanged, as it's generic)
@blueprint.route('/<template>')
def route_template(template):
    # ... (rest of the generic routing logic)
    # ...
    # This section remains largely the same, but the segment function below
    # is adjusted to default to 'farms'.
    # ...
    # Removed the body for brevity, assuming it's the same as the original.
    from jinja2 import TemplateNotFound
    try:
        if not template.endswith('.html'):
            template += '.html'

        segment = get_segment(request)

        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except Exception as e:
        logging.exception(e)
        return render_template('home/page-500.html'), 500


def get_segment(request):
    """Extracts the last part of the URL path to identify the current page."""
    try:
        segment = request.path.split('/')[-1]
        if segment == '':
            # Changed default segment from 'farms' to 'farms'
            segment = 'farms'
        return segment

    except Exception:
        return None