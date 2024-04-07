from flask import Flask,flash,redirect,render_template,url_for,request,jsonify,session,abort
from flask_mysqldb import MySQL
from flask_session import Session
from datetime import date
from datetime import datetime
from sdmail import sendmail
from tokenreset import token
from itsdangerous import URLSafeTimedSerializer
from key import *
import os
from stoken1 import token1

#os.chdir('/home/triveni05/vehicle')
app=Flask(__name__)
app.secret_key='hello'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['MYSQL_HOST'] ='localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='vehicle'
mysql=MySQL(app)
Session(app)
@app.route('/')
def welcome():
    return render_template('welcome.html')
#=========================================customer login and register
@app.route('/clogin',methods=['GET','POST'])
def clogin():
    if session.get('admin'):
        return redirect(url_for('home'))
    if request.method=='POST':
        username=request.form['id1']
        password=request.form['password']
        cursor=mysql.connection.cursor()
        cursor.execute('SELECT count(*) from customers where username=%s and password=%s',[username,password])
        count=cursor.fetchone()[0]
        if count==1:
            session['customers']=username
            return redirect(url_for("customer_dashboard"))
        else:
            flash('Invalid username or password')
            return render_template('login.html')
    return render_template('login.html')
@app.route('/homepage')
def home():
    if session.get('customers'):
        return "customer login"
    else:
        return redirect(url_for('clogin'))
@app.route('/cregistration',methods=['GET','POST'])
def cregistration():
    if request.method=='POST':
        id1=request.form['username']
        email=request.form['email']
        phnumber=request.form['phone_number']
        password=request.form['password']
        address=request.form['address']
        #ccode=request.form['ccode']
        # code="codegnan@9"
        cursor=mysql.connection.cursor()
        cursor.execute('select count(*) from customers where username=%s',[id1])
        count=cursor.fetchone()[0]
        cursor.execute('select count(*) from customers where email=%s',[email])
        count1=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            flash('username already in use')
            return render_template('registration.html')
        elif count1==1:
            flash('Email already in use')
            return render_template('registration.html')

        data={'username':id1,'password':password,'email':email,'phone_number':phnumber,'address':address}
        subject='Email Confirmation'
        body=f"Thanks for signing up\n\nfollow this link for further steps-{url_for('aconfirm',token=token(data,salt),_external=True)}"
        sendmail(to=email,subject=subject,body=body)
        flash('Confirmation link sent to mail')
        return redirect(url_for('clogin'))

    return render_template('registration.html')

@app.route('/aconfirm/<token>')
def aconfirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt,max_age=180)
    except Exception as e:

        return 'Link Expired register again'
    else:
        cursor=mysql.connection.cursor()
        id1=data['username']
        cursor.execute('select count(*) from customers where username=%s',[id1])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.close()
            flash('You are already registerterd!')
            return redirect(url_for('clogin'))
        else:
            cursor.execute('INSERT INTO customers (username, password, email, phone_number, address) VALUES (%s, %s, %s, %s, %s)',[data['username'], data['password'], data['email'], data['phone_number'], data['address']])

            mysql.connection.commit()
            cursor.close()
            flash('Details registered!')
            return redirect(url_for('clogin'))


@app.route('/uforgot',methods=['GET','POST'])
def uforgot():
    if request.method=='POST':
        id1=request.form['username']
        cursor=mysql.connection.cursor()
        cursor.execute('select count(*),email from customers where username=%s',[id1])
        count,email=cursor.fetchone()
        cursor.close()
        data={'username':id1,"email":email}
        if count==1:
            subject='Change your password using below link'
            body=f"Change your password using below link\n\nfollow this link for further steps-{url_for('uconfirm',token=token(data,salt2),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('Confirmation link sent to mail')
            return redirect(url_for('clogin'))
        else:
            flash("No Details Found")
            return redirect(url_for('uforgot'))

    return render_template('forgot.html')

@app.route('/uconfirm/<token>',methods=['GET','POST'])
def uconfirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt2,max_age=3600)
        if data:
            if request.method=='POST':
                newpass = request.form['npassword']
                cpass = request.form['cpassword']
                if newpass==cpass:
                    cursor = mysql.connection.cursor()
                    cursor.execute('Update customers set password=%s where email=%s and username=%s',(newpass,data['email'],data['username']))
                    mysql.connection.commit()
                    cursor.close()
                    flash('Password reset success.')
                    return redirect(url_for('clogin'))
                else:
                    flash('password Not matched')
                    return render_template('newpassword.html',token=token)
            else:
                return render_template('newpassword.html',token=token)
        else:
            flash('Link Expired!')
            return redirect(url_for('uforget'))
    except Exception as e:
        print(e)
        return 'Link Expired register again'
        
#=============================== customer service request
@app.route('/service_request', methods=['GET', 'POST'])
def service_request():
    if session.get('customers'):
        if request.method == 'POST':
            vehicle_category = request.form['vehicle_category']
            vehicle_number = request.form['vehicle_number']
            vehicle_model = request.form['vehicle_model']
            problem_description = request.form['problem_description']
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT customer_id FROM customers WHERE username=%s', (session['customers'],))
            result = cursor.fetchone()
            if result:
                cust_id = result[0]
                cursor.execute("INSERT INTO service_requests (customer_id, vehicle_category, vehicle_number, vehicle_model, problem_description, status) VALUES (%s,%s, %s, %s, %s, %s)",
                               (cust_id, vehicle_category, vehicle_number, vehicle_model, problem_description, 'Pending'))
                mysql.connection.commit()
                cursor.close()
                flash('Service request submitted successfully.')
                return redirect(url_for('customer_dashboard'))
            else:
                flash('Customer not found.')
                return redirect(url_for("clogin"))
        return render_template('customer_service_request.html')
    else:
        return redirect(url_for("clogin"))

#============================== customer dashboard
@app.route('/customer_dashboard')
def customer_dashboard():
    return render_template('customer_dashboard.html')
#===========customer view his requests
@app.route('/view_requests')
def view_requests():
    if session.get('customers'):
        cursor=mysql.connection.cursor()
        cursor.execute('select customer_id from customers where username=%s',(session['customers'],))
        customerid = cursor.fetchone()[0]
        cursor.execute("SELECT sr.request_id, c.customer_id, c.username,c.email,c.phone_number, sr.vehicle_number, sr.vehicle_model, sr.vehicle_category, sr.problem_description, sr.status, sr.cost, sr.date_requested, c.date_registered FROM service_requests sr JOIN customers c ON sr.customer_id = c.customer_id WHERE sr.customer_id = %s",(customerid,))
        view = cursor.fetchall()
        return render_template('view_requests.html',view=view)
    return redirect(url_for('clogin'))
#===================================mechanic dasboard
#=======================mechani signup and applying for a job
@app.route('/mlogin',methods=['GET','POST'])
def mlogin():
    if session.get('mechanic'):
        return redirect(url_for('mechanic_dashboard'))
    if request.method=='POST':
        username=request.form['id1']
        password=request.form['password']
        cursor=mysql.connection.cursor()
        cursor.execute('SELECT count(*) from mechanics where username=%s and password=%s',[username,password])
        count=cursor.fetchone()[0]
        if count==1:
            session['mechanic']=username
            return redirect(url_for("mechanic_dashboard"))
        else:
            flash('Invalid username or password')
            return render_template('mechanic_login.html')
    return render_template('mechanic_login.html')
@app.route('/mlogout')
def mlogout():
    if session.get('mechanic'):
        session.pop('mechanic')
        flash('Successfully loged out')
        return redirect(url_for('mlogin'))
    else:
        return redirect(url_for('mlogin'))

@app.route('/mregistration',methods=['GET','POST'])
def mregistration():
    if request.method=='POST':
        id1=request.form['username']
        email=request.form['email']
        phnumber=request.form['phone_number']
        password=request.form['password']
        address=request.form['address']
        skills=request.form['skills']
        #ccode=request.form['ccode']
        # code="codegnan@9"
        cursor=mysql.connection.cursor()
        cursor.execute('select count(*) from mechanics where username=%s',[id1])
        count=cursor.fetchone()[0]
        cursor.execute('select count(*) from mechanics where email=%s',[email])
        count1=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            flash('username already in use')
            return render_template('mechanic_application.html')
        elif count1==1:
            flash('Email already in use')
            return render_template('mechanic_application.html')

        data1={'username':id1,'password':password,'email':email,'phone_number':phnumber,'address':address,'skills':skills}
        subject='Email Confirmation'
        body=f"Thanks for signing up\n\nfollow this link for further steps-{url_for('mconfirm',token=token1(data1,salt),_external=True)}"
        sendmail(to=email,subject=subject,body=body)
        flash('Confirmation link sent to mail')
        return redirect(url_for('mlogin'))

    return render_template('mechanic_application.html')
@app.route('/mconfirm/<token>')
def mconfirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt,max_age=180)
    except Exception as e:

        return 'Link Expired register again'
    else:
        cursor=mysql.connection.cursor()
        id1=data['username']
        cursor.execute('select count(*) from mechanics where username=%s',[id1])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.close()
            flash('You are already registerterd!')
            return redirect(url_for('mlogin'))
        else:
            cursor.execute('INSERT INTO mechanics (username, password, email, phone_number, address,skills,status) VALUES (%s, %s, %s, %s, %s,%s,%s)',[data['username'], data['password'], data['email'], data['phone_number'], data['address'],data['skills'],'pending'])

            mysql.connection.commit()
            cursor.close()
            flash('Details registered!')
            return redirect(url_for('mlogin'))
        
@app.route('/mforgot',methods=['GET','POST'])
def mforgot():
    if request.method=='POST':
        id1=request.form['username']
        cursor=mysql.connection.cursor()
        cursor.execute('select count(*),email from customers where username=%s',[id1])
        count,email=cursor.fetchone()
        cursor.close()
        data={'username':id1,"email":email}
        if count==1:
            subject='Change your password using below link'
            body=f"Change your password using below link\n\nfollow this link for further steps-{url_for('mfconfirm',token=token(data,salt2),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('Confirmation link sent to mail')
            return redirect(url_for('clogin'))
        else:
            flash("No Details Found")
            return redirect(url_for('uforgot'))

    return render_template('forgot.html')

@app.route('/mfconfirm/<token>',methods=['GET','POST'])
def mfconfirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt2,max_age=3600)
        if data:
            if request.method=='POST':
                newpass = request.form['npassword']
                cpass = request.form['cpassword']
                if newpass==cpass:
                    cursor = mysql.connection.cursor()
                    cursor.execute('Update mechanics set password=%s where email=%s and username=%s',(newpass,data['email'],data['username']))
                    mysql.connection.commit()
                    cursor.close()
                    flash('Password reset success.')
                    return redirect(url_for('clogin'))
                else:
                    flash('password Not matched')
                    return render_template('newpassword.html',token=token)
            else:
                return render_template('newpassword.html',token=token)
        else:
            flash('Link Expired!')
            return redirect(url_for('uforget'))
    except Exception as e:
        print(e)
        return 'Link Expired register again'

#==============mechanic dashboard
@app.route('/mechanic_dashboard')
def mechanic_dashboard():
    if session.get('mechanic'):
        cursor=mysql.connection.cursor()
        cursor.execute('select mechanic_id from mechanics where username=%s',(session['mechanic'],))
        mechanicid = cursor.fetchone()[0]
        cursor.execute("select * from mechanics WHERE mechanic_id = %s",(mechanicid,))
        view = cursor.fetchall()
        return render_template('mechanic_dashboard.html',view=view)
    return redirect(url_for('mlogin'))


#======================================Admin dashboard
#=================admin login
@app.route('/admin_login',methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        email=request.form['email']
        code = request.form['code']
        email='admin@codegnan.com'
        code='admin@123'
        if email == email and code == code:
            return redirect(url_for('admin_dashboard'))
        else:
            flash("unauthorized access")
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

#==================admin view the requested customer services pending
@app.route('/cust_pending_req',methods=['GET','POST'])
def customer_pending():

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT sr.request_id, c.customer_id, c.username,c.email,c.phone_number, sr.vehicle_number, sr.vehicle_model, sr.vehicle_category, sr.problem_description, sr.status, sr.cost, sr.date_requested, c.date_registered FROM service_requests sr JOIN customers c ON sr.customer_id = c.customer_id WHERE sr.status = 'Pending'")
    pending_requests = cursor.fetchall()
    cursor.close()

    return render_template('cust_pending_req.html', requests=pending_requests)
#============================update request
@app.route('/update_status/<int:request_id>', methods=['POST'])
def update_status(request_id):
    new_status = request.form['status']
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE service_requests SET status = %s WHERE request_id = %s", (new_status, request_id))
    mysql.connection.commit()
    cursor.close()
    flash('Status updated successfully.')
    return redirect(url_for('admin_dashboard'))
#=================== admin view accepted service requests
@app.route('/cust_accepted_req',methods=['GET','POST'])
def customer_accepted():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT sr.request_id, c.customer_id, c.username,c.email,c.phone_number, sr.vehicle_number, sr.vehicle_model, sr.vehicle_category, sr.problem_description, sr.status, sr.cost, sr.date_requested, c.date_registered FROM service_requests sr JOIN customers c ON sr.customer_id = c.customer_id WHERE sr.status = 'Accept'")
    accept_requests = cursor.fetchall()
    cursor.close()

    return render_template('cust_accepted_req.html',requests=accept_requests)
#=================== admin rejected service requests
@app.route('/cust_reject_req',methods=['GET','POST'])
def customer_rejected():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT sr.request_id, c.customer_id, c.username,c.email,c.phone_number, sr.vehicle_number, sr.vehicle_model, sr.vehicle_category, sr.problem_description, sr.status, sr.cost, sr.date_requested, c.date_registered FROM service_requests sr JOIN customers c ON sr.customer_id = c.customer_id WHERE sr.status = 'Reject'")
    reject_requests = cursor.fetchall()
    cursor.close()

    return render_template('cust_rejected_req.html',requests=reject_requests)
#================== update cost
@app.route('/update_cost/<int:request_id>', methods=['POST'])
def update_cost(request_id):
    new_cost = request.form['cost']
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE service_requests SET cost = %s WHERE request_id = %s", (new_cost, request_id))
    mysql.connection.commit()
    cursor.close()
    flash('Cost updated successfully.')
    return redirect(url_for('customer_accepted'))

#==================admin view the requested mechanic applications pending
@app.route('/mech_pending',methods=['GET','POST'])
def mechanic_pending():

    cursor = mysql.connection.cursor()
    cursor.execute("select * from mechanics where status='pending'")
    pending_requests = cursor.fetchall()
    cursor.close()

    return render_template('mechanic_pending.html', requests=pending_requests)
#============================update mechanic job request
@app.route('/update_job/<int:request_id>', methods=['GET','POST'])
def update_job(request_id):
    new_status = request.form['status']
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE mechanics SET status = %s WHERE mechanic_id = %s", (new_status, request_id))
    mysql.connection.commit()
    cursor.close()
    flash('Status updated successfully.')
    return redirect(url_for('admin_dashboard'))
#=============================accepted mechanic job
@app.route('/mech_accepted',methods=['GET','POST'])
def mechanic_accepted():

    cursor = mysql.connection.cursor()
    cursor.execute("select * from mechanics where status='approved'")
    accept_requests = cursor.fetchall()
    cursor.close()

    return render_template('mechanic_accept.html', requests=accept_requests)
#=============================== rejected mechanic job
@app.route('/mech_reject',methods=['GET','POST'])
def mechanic_rejected():

    cursor = mysql.connection.cursor()
    cursor.execute("select * from mechanics where status='rejected'")
    reject_requests = cursor.fetchall()
    cursor.close()

    return render_template('mechanic_rejected.html', requests=reject_requests)
#customer logout
@app.route('/clogout')
def clogout():
    if session.get('customers'):
        session.pop('customers')
        flash('Successfully loged out')
        return redirect(url_for('clogin'))
    else:
        return redirect(url_for('clogin'))
#============================ contact us
@app.route('/contact_us',methods=['GET','POST'])
def contact_us():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']

        # Insert the contact message into the database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO contact_us (name, email, subject, message) VALUES (%s, %s, %s, %s)", (name, email, subject, message))
        mysql.connection.commit()
        cur.close()

        flash('Your message has been sent successfully!', 'success')
        return redirect('/contact_us')

    return render_template('contact_us.html')
#======================read conmtact us
@app.route('/view_contact_messages')
def view_contact_messages():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM contact_us")
    messages = cursor.fetchall()
    cursor.close()
    return render_template('view_contactus_messages.html',messages=messages)
if __name__ == "__main__":
    app.run()