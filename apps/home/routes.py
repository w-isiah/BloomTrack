from apps.home import blueprint
from flask import render_template, request
from jinja2 import TemplateNotFound

from flask import render_template, request, jsonify, current_app
from datetime import datetime
import mysql.connector
import traceback
from apps import get_db_connection






# Route for the 'index' page of the home blueprint
@blueprint.route('/index')
def index():
    """
    Renders the 'index' page of the home section.
    The segment variable is passed to the template to identify the current page.

    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM product_list WHERE reorder_level > quantity ORDER BY name')
    products = cursor.fetchall()

    return render_template('home/index.html',products=products, segment='index')


# Dynamic route to handle other templates in the 'home' folder
@blueprint.route('/<template>')
def route_template(template):
    """
    This route renders dynamic templates from the 'home' folder.
    If the template exists, it renders it; otherwise, it returns a 404 error page.
    """
    try:
        # Ensure the template ends with '.html' for correct rendering
        if not template.endswith('.html'):
            template += '.html'

        # Extract the current page's segment (name) from the URL path
        segment = get_segment(request)

        # Render the specific template, passing the segment to it
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        # If the template is not found, return a 404 error page
        return render_template('home/page-404.html'), 404

    except Exception as e:
        # Catch any other exceptions and return a 500 error page
        return render_template('home/page-500.html'), 500


# Helper function to extract the current page segment (name) from the request URL
def get_segment(request):
    """
    Extracts the last part of the URL path to identify the current page.
    If the path ends with a '/', it returns 'index' by default.
    """
    try:
        # Get the last part of the URL path
        segment = request.path.split('/')[-1]

        # If the path ends with '/', default to 'index'
        if segment == '':
            segment = 'index'

        return segment

    except Exception as e:
        # If there's an error, return None
        return None
