from flask import render_template, redirect, request, url_for, flash, session
from apps import get_db_connection
from apps.authentication import blueprint
from datetime import datetime

@blueprint.route('/', methods=['GET', 'POST'])
def route_default():
    return redirect(url_for('authentication_blueprint.login'))


@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            # Get DB connection using context manager
            with get_db_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                    user = cursor.fetchone()

                    if user and user['password'] == password:  # Direct password comparison
                        # Insert a new login record in the user_activity table
                        cursor.execute("INSERT INTO user_activity (user_id, login_time) VALUES (%s, %s)", 
                                       (user['id'], datetime.utcnow()))
                        connection.commit()  # Commit the changes to the database

                        # Storing the user session data directly in the session dictionary
                        session.update({
                            'loggedin': True,
                            'id': user['id'],
                            'username': user['username'],
                            'role': user['role'],
                            'last_activity': datetime.utcnow()
                        })
                        session.permanent = True  # Make session permanent
                        flash('Login successful!', 'success')

                        # Redirect to the home page after successful login
                        return redirect(url_for('home_blueprint.index'))
                    else:
                        flash('Incorrect username or password.', 'danger')
                        return redirect(url_for('authentication_blueprint.login'))

        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')

    return render_template('accounts/login.html')


@blueprint.route('/logout')
def logout():
    # Before logging out, set the logout time in the user_activity table
    if 'username' in session:
        username = session['username']

        try:
            with get_db_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    # Update the logout time for the current active session
                    cursor.execute("UPDATE user_activity SET logout_time = %s WHERE user_id = %s AND logout_time IS NULL", 
                                   (datetime.utcnow(), session['id']))
                    connection.commit()  # Commit the changes to the database
        except Exception as e:
            flash(f"An error occurred while updating the logout status: {str(e)}", 'danger')

    # Log out the user by clearing the session
    session.clear()  # Remove session data
    flash('You have been logged out.', 'success')
    return redirect(url_for('authentication_blueprint.login'))


# Error Handlers
@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('home/page-403.html'), 403

@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('home/page-404.html'), 404

@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('home/page-500.html'), 500
