from apps.home import blueprint
from flask import render_template, request, session, flash
from jinja2 import TemplateNotFound
from apps import get_db_connection
import logging

@blueprint.route('/index')
def index():
    """
    Renders the 'index' page of the home section.
    """
    connection = get_db_connection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT * FROM product_list WHERE reorder_level > quantity ORDER BY name')
            products = cursor.fetchall()
    finally:
        connection.close()  # Ensure the connection is closed after use

    return render_template('home/index.html', role=session['role'], products=products, segment='index')

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
