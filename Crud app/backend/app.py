from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from datetime import datetime
from datetime import datetime, timedelta
from flask import jsonify

app = Flask(__name__)
app.secret_key = "flash message"

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234567'
app.config['MYSQL_DB'] = 'wewmydb'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '1234567'

mysql = MySQL(app)

@app.route('/')
def home():
    if 'username' in session:
        return render_template('intro.html', username=session['username'])
    else:
        return render_template('intro.html')

@app.route('/index')
def index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT  * FROM costumer")
    data = cur.fetchall()
    cur.close()

    return render_template('admin_index.html', costumer=data)


def insert_into_tables(name, monthly_payment, costumer_type, username, password):
    try:
        # Insert into costumer table
        monthly_payment = int(monthly_payment)
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO costumer (name, monthly_payment, costumer_type, date, username, password)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, monthly_payment*500, costumer_type, datetime.now(), username, password))
        mysql.connection.commit()

        # Get the last inserted ID in costumer table
        cur.execute("SELECT LAST_INSERT_ID()")
        costumer_id = cur.fetchone()[0]
        

        if costumer_type == 'member':
            
           
            cur.execute("""
                INSERT INTO member (member_id, member_name, mem_monthly_pay, mem_startingdate, mem_enddate)
                VALUES (%s, %s, %s, %s, %s)
            """, (costumer_id, name, monthly_payment*500, datetime.now(),datetime.now()+timedelta(days=30)* monthly_payment))
            mysql.connection.commit()

            # Insert into membership_plan table
            cur.execute("""
                INSERT INTO membership_plan (member_id, payment_amount, mem_startingdate, mem_enddate)
                VALUES (%s, %s, %s, %s)
            """, (costumer_id, monthly_payment*500, datetime.now(),datetime.now()+timedelta(days=30) * monthly_payment))
            mysql.connection.commit()

            # Insert into userz table
            cur.execute("""
                INSERT INTO userz (user_id, username, password)
                VALUES (%s, %s, %s)
            """, (costumer_id, username, password))
            mysql.connection.commit()

            cur.execute("""
                INSERT INTO session (member_id, session_date)
                VALUES (%s, %s)
            """, (costumer_id, datetime.now()))
            mysql.connection.commit()

       

            

    except Exception as e:
        # Handle exceptions and rollback the transaction
        flash(f"Error: {str(e)}", 'error')
        mysql.connection.rollback()

    finally:
        cur.close()

    

# Modified insert route
@app.route('/insert', methods=['POST'])
def insert():
    if request.method == "POST":
        flash("Data Inserted Successfully")

        name = request.form['name']
        monthly_payment = request.form['monthly_payment']
        costumer_type = request.form['costumer_type']
        username = request.form['username']
        password = request.form['password']

        insert_into_tables(name, monthly_payment, costumer_type, username, password)

        return redirect(url_for('index'))

@app.route('/update', methods=['POST', 'GET'])
def update():
    if request.method == 'POST':
        id_data = request.form['id']
        name = request.form['name']
        monthly_payment = request.form['monthly_payment']
        costumer_type = request.form['costumer_type']
        cur = mysql.connection.cursor()
        cur.execute("""
               UPDATE costumer
               SET name=%s, monthly_payment=%s, costumer_type=%s
               WHERE id=%s
            """, (name, monthly_payment, costumer_type, id_data))
        flash("Data Updated Successfully")
        mysql.connection.commit()
        return redirect(url_for('index'))


@app.route('/delete/<string:id_data>', methods=['GET'])
def delete(id_data):
    try:
        flash("Record Has Been Deleted Successfully")

        # Start a transaction
        cur = mysql.connection.cursor()

        # Delete associated records in the session table
        cur.execute("""
            DELETE FROM session
            WHERE member_id IN (
                SELECT id
                FROM costumer
                WHERE id=%s
            )
        """, (id_data,))

        # Delete associated records in the membership_plan table
        cur.execute("""
            DELETE FROM membership_plan
            WHERE member_id IN (
                SELECT id
                FROM costumer
                WHERE id=%s
            )
        """, (id_data,))

        # Delete associated records in the userz table
        cur.execute("""
            DELETE FROM userz
            WHERE user_id IN (
                SELECT id
                FROM costumer
                WHERE id=%s
            )
        """, (id_data,))

        # Delete associated records in the member table
        cur.execute("""
            DELETE FROM member
            WHERE member_id IN (
                SELECT id
                FROM costumer
                WHERE id=%s
            )
        """, (id_data,))

        # Now, delete the costumer record
        cur.execute("DELETE FROM costumer WHERE id=%s", (id_data,))

        # Commit the transaction
        mysql.connection.commit()

        return redirect(url_for('index'))

    except Exception as e:
        # Handle exceptions if any and rollback the transaction
        flash(f"Error: {str(e)}", 'error')
        mysql.connection.rollback()

    finally:
        # Close the cursor
        cur.close()

    return redirect(url_for('index'))


@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if it's the admin account
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['username'] = username
            session['is_admin'] = True
            flash("Welcome, Admin!")
            return redirect(url_for('dashboard'))

        # Check for regular user login using username and password
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM costumer WHERE username = %s AND password = %s", (username, password))
        user_data = cur.fetchone()
        cur.close()

        if user_data:
            session['username'] = username
            flash("Login Successful!")

            # Store user_id in the session
            session['user_id'] = user_data[0]

            return redirect(url_for('member_home'))

        # If not admin and not a regular user, show an error
        flash("Invalid credentials. Please try again.", 'error')

    return redirect(url_for('home'))

@app.route('/admin/index')
def admin_index():
    if 'username' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM costumer")
        data = cur.fetchall()
        cur.close()
        return render_template('admin_index.html', costumer=data)
    else:
        flash("You need to log in as an admin first.")
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('is_admin', None)
    flash("You have been logged out successfully.", 'success')
    return redirect(url_for('home'))


@app.route('/member_home')
def member_home():
    if 'username' in session:
        user_id = session.get('user_id')
        if user_id is not None:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM costumer WHERE id = %s", [user_id])
            user_data = cur.fetchone()
            cur.close()

            cur = mysql.connection.cursor()
            cur.execute("SELECT mem_enddate FROM membership_plan WHERE member_id = %s", [user_id])
            membership_plan_data = cur.fetchone()
            cur.close()

            if user_data:
                return render_template('member.html', costumer_name=user_data[3],  # Change index to the correct one
                                       costumer_monthly_payment=user_data[2], costumer_costumer_type=user_data[1],membership_plan_mem_enddate=membership_plan_data[0])  # Adjust indices accordingly
            else:
                flash("User data not found. Please log in again.", 'error')
                return redirect(url_for('home'))
        else:
            flash("User data not found. Please log in again.", 'error')
            return redirect(url_for('home'))

    flash("You need to log in first.", 'error')
    return redirect(url_for('intro'))

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/admin/member_list')
def admin_member_list():
    if 'username' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM member")
        data = cur.fetchall()
        cur.close()
        return render_template('member_list.html', member=data)
    else:
        flash("You need to log in as an admin first.")
        return redirect(url_for('home'))

@app.route('/sales')
def sales():
    if 'username' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM session")
        data = cur.fetchall()
        cur.close()
        return render_template('sales.html', session=data)
    else:
        flash("You need to log in as an admin first.")
        return redirect(url_for('home'))

@app.route('/equipments')
def equipments():
    if 'username' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM session")
        data = cur.fetchall()
        cur.close()
        return render_template('equipments.html', session=data)
    else:
        flash("You need to log in as an admin first.")
        return redirect(url_for('home')) 
    
@app.route('/accounts')
def accounts():
    if 'username' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM userz")
        data = cur.fetchall()
        cur.close()
        return render_template('accounts.html', userz=data)
    else:
        flash("You need to log in as an admin first.")
        return redirect(url_for('home'))
      

@app.route('/dashboard')
def dashboard():
    if 'username' in session and session.get('is_admin'):
        flash("Welcome, Admin!")
        # Get the counts from your database tables
        cur = mysql.connection.cursor()
        
        # Count of visitors
        cur.execute("SELECT COUNT(*) FROM visitor")
        visitors_count = cur.fetchone()[0]

        # Count of members
        cur.execute("SELECT COUNT(*) FROM member")
        members_count = cur.fetchone()[0]

        # Count of costumers
        cur.execute("SELECT COUNT(*) FROM costumer")
        costumers_count = cur.fetchone()[0]

         # Calculate the total monthly payment
        cur.execute("SELECT SUM(monthly_payment) FROM costumer")
        total_monthly_payment = cur.fetchone()[0] or 0

        cur.close()

        return render_template('dashboard.html', visitors_count=visitors_count, members_count=members_count,
                               costumers_count=costumers_count, sales_count=total_monthly_payment)
    else:
        flash("You need to log in as an admin first.")
        return redirect(url_for('home'))
    
@app.route('/member_shop')
def member_shop():
    if 'username' in session:
        return render_template('member_shop.html')
    else:
        flash("You need to log in first.", 'error')
        return redirect(url_for('home'))



@app.route('/record_purchase', methods=['POST'])
def record_purchase():
    try:
        total_amount = request.json['totalAmount']

        # Assuming member_id is available in the session, update the session_purchase column
        member_id = session.get('user_id')
        cur = mysql.connection.cursor()
        cur.execute("UPDATE session SET session_purchase = %s WHERE member_id = %s", (total_amount, member_id))
        mysql.connection.commit()

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    
@app.route('/member_equipment')
def member_equipment():
    if 'username' in session:
        return render_template('member_equipment.html')
    else:
        flash("You need to log in first.", 'error')
        return redirect(url_for('home'))
    
@app.route('/record_used', methods=['POST'])
def record_used():
    try:
        total_amount = request.json['totalAmount']

        # Assuming member_id is available in the session, update the session_purchase column
        member_id = session.get('user_id')
        cur = mysql.connection.cursor()
        cur.execute("UPDATE session SET session_equipments_use = %s WHERE member_id = %s", (total_amount, member_id))
        mysql.connection.commit()

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/visitor')
def visitor():
    # Your logic for the 'visitor' route goes here
    return render_template('visitor.html')
@app.route('/intro')
def intro():
    # Your logic for the 'visitor' route goes here
    return render_template('intro.html')

    
@app.route('/record_purchase1', methods=['POST'])
def record_purchase1():
    try:
        total_amount = request.json['totalAmount']
        data = request.json
        name = data.get('name')
        costumer_type = data.get('costumer_type')
        cus_type='visitor'
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO costumer (name, monthly_payment, costumer_type, date)
            VALUES (%s, %s, %s, %s)
        """, (name,  total_amount, cus_type, datetime.now()))
        mysql.connection.commit()

        # Get the last inserted ID in the costumer table
        cur.execute("SELECT LAST_INSERT_ID()")
        costumer_id = cur.fetchone()[0]

        print(f"Costumer ID: {costumer_id}, Costumer Type: {costumer_type}")
        costumer_type='visitor'
        # Check if costumer_type is 'visitor' and insert into the visitor table
        if costumer_type == 'visitor':
            # Insert into the visitor table
            cur.execute("""
                INSERT INTO visitor (visitor_id, visitor_name,visitor_payment,visitor_date)
                VALUES (%s, %s,%s, %s)
            """, (costumer_id,name,total_amount,datetime.now()))
            mysql.connection.commit()
            
            cur.execute("""
                INSERT INTO vsession (visitor_id, session_date,vsession_purchase)
                VALUES (%s, %s,%s)
            """, (costumer_id, datetime.now(),total_amount))
            mysql.connection.commit()
        return jsonify({'status': 'success'})

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})


if __name__ == '__main__':
    app.run(debug=True)