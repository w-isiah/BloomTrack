To record the login and logout details for **every day** (i.e., creating a history of login and logout events for each user), you should store these events in a **separate table** rather than updating the `users` table every time a user logs in or out. This allows you to keep track of each day's login and logout for the user over time.

### Step 1: Create a `user_activity` Table

First, you need to create a new table called `user_activity` in your database to track each login and logout event with timestamps for every day.

```sql
CREATE TABLE user_activity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    login_time DATETIME,
    logout_time DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Explanation of Columns:
- **`id`**: A unique identifier for each login/logout record.
- **`user_id`**: The `id` of the user (foreign key referencing the `users` table).
- **`login_time`**: The timestamp of when the user logs in.
- **`logout_time`**: The timestamp of when the user logs out (this will be `NULL` when the user is still logged in).

### Step 2: Modify the Flask Code

You will need to modify the login and logout functionality so that every time a user logs in or logs out, a new record is added to the `user_activity` table. When the user logs out, we will also update the `logout_time` for their record.

#### Modified Code to Track Login and Logout Events Per Day

```python
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
```

### Explanation of Changes:

1. **`user_activity` Table**:
   - A new row is inserted in the `user_activity` table every time a user logs in. The `login_time` is set to the current timestamp (`datetime.utcnow()`).
   - When the user logs out, we update the `logout_time` for the record where `logout_time` is `NULL` (the latest login for that user).

2. **Login Route** (`/login`):
   - On login, after successfully authenticating the user, a new record is inserted into the `user_activity` table with the `user_id` and `login_time`.

3. **Logout Route** (`/logout`):
   - When the user logs out, the `logout_time` is updated for the most recent record where the `logout_time` is still `NULL` (indicating that the user was still logged in at that time).

### Step 3: Usage of the `user_activity` Table

Now, every time a user logs in and logs out, you will have a historical record of these events in the `user_activity` table. For example, you can use the following SQL queries to:

1. **Get All Login and Logout Events for a Specific User**:
   ```sql
   SELECT login_time, logout_time
   FROM user_activity
   WHERE user_id = 1
   ORDER BY login_time DESC;
   ```

2. **Get All Active Sessions (i.e., users who are currently logged in)**:
   ```sql
   SELECT u.username, ua.login_time
   FROM user_activity ua
   JOIN users u ON ua.user_id = u.id
   WHERE ua.logout_time IS NULL;
   ```

3. **Get a User's Total Login Duration** (if you want to calculate the time between `login_time` and `logout_time`):
   ```sql
   SELECT user_id, login_time, logout_time, TIMESTAMPDIFF(SECOND, login_time, logout_time) AS session_duration_seconds
   FROM user_activity
   WHERE user_id = 1;
   ```

### Optional: Display Login/Logout History in the Template

You can also display the user's login and logout history in their profile or an activity log page by querying the `user_activity` table and passing the data to the template.

#### Example View for User Activity:

```python
@blueprint.route('/activity_log')
def activity_log():
    if 'username' in session:
        user_id = session['id']
        
        try:
            with get_db_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute("SELECT login_time, logout_time FROM user_activity WHERE user_id = %s ORDER BY login_time DESC", (user_id,))
                    activities = cursor.fetchall()
                    
                    return render_template('activity_log.html', activities=activities)
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(url_for('authentication_blueprint.login'))
    else:
        return redirect(url_for('authentication_blueprint.login'))
```

In the corresponding template (`activity_log.html`), you can display the user's login/logout history like this:

```html
<h2>User Activity Log</h2>
<table>
    <tr>
        <th>Login Time</th>
        <th>Logout Time</th>
    </tr>
    {% for activity in activities %}
    <tr>
        <td>{{ activity.login_time }}</td>
        <td>{{ activity.logout_time if activity.logout_time else 'Still Logged In' }}</td>
    </tr>
    {% endfor %}
</table>
```

### Conclusion:
This setup allows you to track the user's login and logout history on a daily basis. Each time a user logs in or logs out, a new record is created in the `user_activity` table with the respective login and logout timestamps. You can query this table to get a detailed log of the user's activity over time.