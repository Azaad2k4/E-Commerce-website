from flask import Flask, request,redirect,url_for,render_template,flash,session,jsonify
from flask_session import Session
from werkzeug.utils import secure_filename
from otp import genotp
from cmail import send_mail
from stoken import endata,dndata
import bcrypt
import os
import razorpay
client = razorpay.Client(auth=("rzp_test_SHy3zlzWZXNg3W","B67PBLrrvi1BP38vgyIEdOHg"))
from mysql.connector import (connection)
mydb = connection.MySQLConnection(user='root',password='Azaad@04',host='localhost',database='ecom')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR,'static','uploads_data')
os.makedirs(UPLOAD_FOLDER,exist_ok=True)
ALLOWED_EXTENSIONS = {'png','jpg','jpeg','webp'}
MAX_CONTENT_LENGTH = 6 * 1024*1024 

app=Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.secret_key = b'\x05\x9ed\x96V'
Session(app)
app.secret_key = 'code2018'
@app.route('/')
def index():
    return render_template('welcome.html')

@app.route('/home')
def home():
    try:
        cursor=mydb.cursor(buffered=True)       
        cursor.execute('select bin_to_uuid(itemid),item_name,item_desc,item_category,item_price,item_about,item_image,item_quantity,added_by from items ')
        all_items=cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(e)
        flash('Could not retrieve items')
        return redirect(url_for('home'))
    else:
        return render_template('index.html',all_items=all_items)
    

@app.route('/admincreate',methods=['GET','POST'])
def admincreate():
    if request.method=='POST':
        admin_username=request.form['username'].strip()
        admin_email = request.form['email'].strip()
        admin_password=request.form['password'].strip()
        admin_address=request.form['address'].strip()
        admin_agree=request.form['agree']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from admindata where admin_email=%s',[admin_email])
            count_email=cursor.fetchone()
        except Exception as e:
            flash('Could not verify email')
            return redirect(url_for('admincreate'))
        else:
            if count_email[0]==0:
                gotp=genotp()
                admin_data={'username':admin_username,'useremail':admin_email,'userpassword':admin_password,'useraddress':admin_address,'useragree':admin_agree,'admin_otp':gotp}
                subject = 'Admin email Verification for ecommerce'
                body=f'Use the given otp for email verify {gotp}'
                send_mail(to=admin_email,body=body,subject=subject)
                flash('OTP has been sent to given email')
                return redirect(url_for('otpverify',sc_data=endata(admin_data)))
            elif count_email[0]==1:
                flash('Email already exists')
                return redirect(url_for('admincreate'))
    return render_template('admincreate.html')

@app.route('/otpverify/<sc_data>',methods=['GET','POST'])
def otpverify(sc_data):
    try:
        admin_details=dndata(sc_data)
    except Exception as e:
        print(e)
        flash('Could not otp')
        return redirect(url_for('admincreate'))
    else:
        if request.method=='POST':
            user_otp=request.form['otp']
            if user_otp==admin_details['admin_otp']:
                hash_password=bcrypt.hashpw(admin_details['userpassword'].encode('utf-8'),bcrypt.gensalt())
                try:
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('insert into admindata(adminid,admin_username,admin_email,admin_password,admin_address,agree) values (uuid_to_bin(uuid()),%s,%s,%s,%s,%s)',[admin_details['username'],admin_details['useremail'],hash_password,admin_details['useraddress'],admin_details['useragree']])
                    mydb.commit()
                    cursor.close()
                except Exception as e:
                    print(e)
                    flash('could not store the Details ')
                    return redirect(url_for('admincreate'))
                else:
                    flash('registered successfully')
                    return redirect(url_for('adminlogin'))
            else:
                flash('Invalid OTP')
    return render_template('adminotp.html')

@app.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    if request.method == 'POST':
        login_useremail=request.form['email']
        login_password=request.form['password']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from admindata where admin_email=%s',[login_useremail])
            count_email=cursor.fetchone()
            if count_email[0]==1:
                cursor.execute('select admin_password from admindata where admin_email=%s',[login_useremail])
                stored_password=cursor.fetchone()
                if stored_password:
                    if bcrypt.checkpw(login_password.encode('utf-8'),stored_password[0]):
                        session['admin']=login_useremail
                        return redirect(url_for('admindashboard'))
                        
                    else:
                        flash('Invalid password')
                        return redirect(url_for('adminlogin'))
                else:
                    flash('password not found')
                    return redirect(url_for('adminlogin'))
            else:
                flash('email not found')
                return redirect(url_for('adminlogin'))
        except Exception as e:
             print(e)
             flash('could not verify login  Details ')
             return redirect(url_for('adminlogin'))
        
    return render_template('adminlogin.html')
@app.route('/admindashboard')
def admindashboard():
    if session.get('admin'):
        return render_template('adminpanel.html')
    else:
        flash('Please login first to access dashboard')
        return redirect(url_for('adminlogin'))

def allowed_file(filename:str)->bool:
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/additem',methods=['GET','POST'])
def additem():
    if session.get('admin'):
        if request.method=='POST':
            item_name=request.form['title']
            item_description=request.form['Description']
            item_category=request.form['category']
            item_about=request.form['About_item']
            item_quantity=request.form['quantity']
            item_price=request.form['price']
            item_filedata=request.files['file']
            print(item_filedata)
            item_filename=item_filedata.filename
            
            if item_filedata and item_filename:
                if not allowed_file(item_filename):
                    flash('File type not allowed: png,jpg,jpeg,gif,webp')
                    return redirect(url_for('additem'))
                orig_secure=secure_filename(item_filename)
                ext=os.path.splitext(orig_secure)[1]
                filename=genotp()+ext
                save_path=os.path.join(app.config['UPLOAD_FOLDER'],filename)
                try:
                    item_filedata.save(save_path)
                    
                except Exception as e:
                    print(e)
                    flash('Could not save the file')
                    return redirect(url_for('additem'))
            else: 
                flash('Invalid data file')
                return redirect(url_for('additem'))  
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select adminid from admindata where admin_email=%s',[session['admin']])
                adminid=cursor.fetchone()[0]
                
                cursor.execute('insert into items(itemid,item_name,item_desc,item_category,item_price,item_about,item_image,item_quantity,added_by) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s,%s)',[item_name,item_description,item_category,item_price,item_about,filename,item_quantity,adminid])
                mydb.commit()
                cursor.close()  
            except Exception as e:
                print(e)
                flash('Could not store the item details')
                if filename:
                    try:
                        os.remove(save_path)
                    except Exception as e:
                        print(e)
                        flash('Could not remove the uploaded file')
                return redirect(url_for('additem'))
            else:
                flash('Item added successfully')
                return redirect(url_for('additem'))
        return render_template('additem.html')
    else:     
        flash('Please login first to access dashboard')
        return redirect(url_for('adminlogin'))

@app.route('/view_allitems',methods=['GET'])
def view_allitems():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
            adminid=cursor.fetchone()[0]
                
            cursor.execute('select bin_to_uuid(itemid),item_name,item_desc,item_category,item_price,item_about,item_image,item_quantity,added_by from items where added_by=%s',[adminid])
            items=cursor.fetchall()
            cursor.close()
        except Exception as e:
            print(e)
            flash('Could not retrieve items')
            return redirect(url_for('admindashboard'))
        else:
            return render_template('viewall_items.html',allitems_data=items)
    else:
        flash('Please login first to access dashboard')
        return redirect(url_for('adminlogin'))

@app.route('/viewitem/<itemid>',methods=['GET'])
def viewitem(itemid):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
            adminid=cursor.fetchone()[0]
                
            cursor.execute('select bin_to_uuid(itemid),item_name,item_desc,item_category,item_price,item_about,item_image,item_quantity,added_by from items where added_by=%s and itemid=uuid_to_bin(%s)',[adminid,itemid])
            item_details=cursor.fetchone()
            cursor.close()
        except Exception as e:
            print(e)
            flash('Could not retrieve item details')
            return redirect(url_for('admindashboard'))
        else:
            return render_template('view_item.html',item_data=item_details)
    else:
        flash('Please login first to access dashboard')
        return redirect(url_for('adminlogin'))

@app.route('/deleteitem/<itemid>')
def deleteitem(itemid):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
            adminid=cursor.fetchone()[0]
            cursor.execute('select bin_to_uuid(itemid),item_name,item_desc,item_category,item_price,item_about,item_image,item_quantity,added_by from items where added_by=%s and itemid=uuid_to_bin(%s)',[adminid,itemid])
            item_details=cursor.fetchone()
            remove_path=os.path.join(app.config['UPLOAD_FOLDER'],item_details[6])
            print(remove_path)
            try:
                os.remove(remove_path)
            except Exception as e:
                print(e)
                flash(f'could not remove the file data')
                return redirect(url_for('view_allitems'))
            try:
                cursor.execute('delete from items where added_by=%s and itemid=uuid_to_bin(%s)',[adminid,itemid])
                mydb.commit()
                cursor.close()
                flash('Item deleted successfully')
                return redirect(url_for('view_allitems'))
            except Exception as e:
                print(e)
                flash('Could not delete the item details')
                return redirect(url_for('view_allitems'))
            else:
                flash('Item deleted successfully')
                return redirect(url_for('view_allitems'))
              
        except Exception as e:
            print(e)
            flash('Could not retrieve item details')
            return redirect(url_for('admindashboard'))  

    else:
        flash(f'Please login first')
        return redirect(url_for('adminlogin'))           
             
@app.route('/updateitem/<itemid>',methods=['GET','POST'])
def updateitem(itemid):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
            adminid=cursor.fetchone()[0]
                
            cursor.execute('select bin_to_uuid(itemid),item_name,item_desc,item_category,item_price,item_about,item_image,item_quantity,added_by from items where added_by=%s and itemid=uuid_to_bin(%s)',[adminid,itemid])
            item_details=cursor.fetchone()
            cursor.close()
        except Exception as e:
            print(e)
            flash('Could not retrieve item details')
            return redirect(url_for('view_allitems'))
        else:
            if request.method == 'POST':
                # print(request.form)
                updateditem_name=request.form['title']
                updateditem_description=request.form['Description']
                updateditem_category=request.form['category']
                updateditem_about=request.form['About_item']
                updateditem_quantity=request.form['quantity']
                updateditem_price=request.form['price']
                updateditem_filedata=request.files['file']
                # print(updateditem_filedata)
                updateditem_filename=updateditem_filedata.filename
                if updateditem_filename=='':
                    filename=item_details[6]
                else:
                    if updateditem_filedata and updateditem_filename:
                        if not allowed_file(updateditem_filename):
                            flash('File type not allowed: png,jpg,jpeg,gif,webp')
                            return redirect(url_for('updateitem',itemid=itemid))
                        orig_secure=secure_filename(updateditem_filename)
                        ext=os.path.splitext(orig_secure)[1]
                        # print(ext)
                        filename=genotp()+ext
                        save_path=os.path.join(app.config['UPLOAD_FOLDER'],filename)
                    try:
                        updateditem_filedata.save(save_path)
                    except Exception as e:
                        print(e)
                        flash('Could not save the file')
                        return redirect(url_for('updateitem',itemid=itemid))  
    
                print('final filename:',filename)
                try:
                    cursor = mydb.cursor(buffered=True)

                    cursor.execute(
                        '''update items set
                            item_name=%s,
                            item_desc=%s,
                            item_category=%s,
                            item_price=%s,
                            item_about=%s,
                            item_image=%s,
                            item_quantity=%s
                        where added_by=%s
                        and itemid=uuid_to_bin(%s)''',
                        [
                            updateditem_name,
                            updateditem_description,
                            updateditem_category,
                            updateditem_price,
                            updateditem_about,
                            filename,
                            updateditem_quantity,
                            adminid,     # ✅ binary admin id
                            itemid       # ✅ string UUID converted here
                        ]
                    )

                    mydb.commit()
                    cursor.close()

                    flash('Item updated successfully')
                    return redirect(url_for('view_allitems'))

                except Exception as e:
                    print(e)
                    flash('Could not update item details')
                    return redirect(url_for('updateitem', itemid=itemid))

                # try:
                #     cursor=mydb.cursor(buffered=True)
                #     cursor.execute('select item_image from items where itemid=uuid_to_bin(%s)',[session.get('admin')])
                #     admin_id=cursor.fetchone()[0]
                #     print('admin id:',admin_id)
                #     cursor.execute('update items set item_name=%s,item_desc=%s,item_category=%s,item_price=%s,item_about=%s,item_image=%s,item_quantity=%s where added_by=%s and itemid=bin_to_uuid(%s)',[updateditem_name,updateditem_description,updateditem_category,updateditem_price,updateditem_about,filename,updateditem_quantity,admin_id,itemid])
                #     mydb.commit()
                #     cursor.close()
                #     flash('Item updated successfully')
                           
                # except Exception as e:
                #     print(e)
                #     flash('Could not update item details')
                #     return redirect(url_for('updateitem',itemid=itemid))
                # else:                             
                #     flash('Item updated successfully')
                #     return redirect(url_for('view_allitems'))

                

            return render_template('updateitem.html',storeditem_data=item_details)
        
    else:
        flash(f'Please login first')
        return redirect(url_for('adminlogin'))




@app.route('/adminlogout')
def adminlogout():
    if  session.get('admin'):

        session.pop('admin',None)
        return redirect(url_for('adminlogin'))
    else:
        flash('pls login first')
        return redirect(url_for('adminlogin'))

@app.route('/adminforgotpwd',methods=['GET','POST'])
def adminforgotpwd():
    if request.method=='POST':
        forgot_email=request.form['forgot_email']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from admindata where admin_email=%s',[forgot_email])
            count_email=cursor.fetchone()[0]
        except Exception as e:
            print(e)
            flash('could not verify email')
            return redirect(url_for('adminforgotpwd'))
        else:
            if count_email==1:
                subject='Reset link for admin account'
                body=f'use the given link :{url_for("adminpassword",data=endata(forgot_email),_external=True)} '
                send_mail(to=forgot_email, body=body, subject=subject)
                flash('Reset link sent to your email')
                return redirect(url_for('adminforgotpwd'))
            elif count_email==0:
                flash('email not found')
                return redirect(url_for('adminforgotpwd'))
    return render_template('adminforgotpassword.html')

@app.route('/adminpassword/<data>',methods=['GET','PUT'])
def adminpassword(data):
    if request.method=='PUT':
        newpassword=request.get_json()['newpassword']
        try:
            user_email=dndata(data)
            
        except Exception as e:
            print(e)
            flash('could not verify data')
            return redirect(url_for('adminpassword',data=data))
        else:
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select count(*) from admindata where admin_email=%s',[user_email])
                count_email=cursor.fetchone()[0]
            except Exception as e:
                print(e)
                flash('could not verify email')
                return redirect(url_for('adminpassword',data=data))
            else:
                if count_email==1:
                    hash_password=bcrypt.hashpw(newpassword.encode('utf-8'),bcrypt.gensalt())
                    cursor.execute('update admindata set admin_password=%s where admin_email=%s',[hash_password,user_email])
                    mydb.commit()
                    cursor.close()
                    flash('Password updated successfully')
                    return jsonify({'message':'ok'})
                elif count_email==0:
                    flash(' admin email invalid')
                    return redirect(url_for('adminpassword',data=data))
    return render_template('newpassword.html',data=data)



#user routes and functionalities
@app.route('/usercreate', methods=['GET','POST'])
def usercreate():
    if request.method == 'POST':

        username = request.form['name'].strip()
        useremail = request.form['email'].strip()
        useraddress = request.form['address'].strip()
        user_phno = request.form['phone_no'].strip()
        userpassword = request.form['password'].strip()
        usergender = request.form['usergender'].strip()

        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute(
                'select count(*) from userdata where useremail=%s',
                [useremail]
            )
            count_email = cursor.fetchone()

        except Exception as e:
            print(e)
            flash('Could not verify email')
            return redirect(url_for('usercreate'))

        else:
            if count_email[0] == 0:

                gotp = genotp()

                user_data = {
                    'username': username,
                    'useremail': useremail,
                    'useraddress': useraddress,
                    'userphno': user_phno,
                    'userpassword': userpassword,
                    'usergender': usergender,
                    'user_otp': gotp
                }

                subject = 'User Email Verification for BUYROUTE'
                body = f'Use the given OTP to verify your account: {gotp}'

                send_mail(to=useremail, body=body, subject=subject)

                flash('OTP has been sent to your email')
                return redirect(url_for('userotpverify', sc_data=endata(user_data)))

            else:
                flash('Email already exists')
                return redirect(url_for('usercreate'))

    return render_template('usersignup.html')



#userotp
@app.route('/userotpverify/<sc_data>', methods=['GET','POST'])
def userotpverify(sc_data):
    try:
        user_details = dndata(sc_data)
    except Exception as e:
        print(e)
        flash('Could not verify OTP')
        return redirect(url_for('usercreate'))

    if request.method == 'POST':
        user_otp = request.form['otp']

        if user_otp == user_details['user_otp']:

            hash_password = bcrypt.hashpw(
                user_details['userpassword'].encode('utf-8'),
                bcrypt.gensalt()
            )

            try:
                cursor = mydb.cursor(buffered=True)

                cursor.execute(
                    '''insert into userdata(
                        userid,
                        username,
                        useremail,
                        user_phno,
                        user_password,
                        useraddress,
                        user_gender
                    )
                    values (
                        uuid_to_bin(uuid()),
                        %s,%s,%s,%s,%s,%s
                    )''',
                    [
                        user_details['username'],
                        user_details['useremail'],
                        user_details['userphno'],
                        hash_password,
                        user_details['useraddress'],
                        user_details['usergender']
                    ]
                )

                mydb.commit()
                cursor.close()

            except Exception as e:
                print(e)
                flash('Could not store user details')
                return redirect(url_for('usercreate'))

            flash('User registered successfully')
            return redirect(url_for('userlogin'))

        else:
            flash('Invalid OTP')

    return render_template('userotp.html')


@app.route('/userlogin', methods=['GET','POST'])
def userlogin():
    if request.method == 'POST':
        login_useremail = request.form['email']
        login_password = request.form['password']

        try:
            cursor = mydb.cursor(buffered=True)

            cursor.execute(
                'select count(*) from userdata where useremail=%s',
                [login_useremail]
            )
            count_email = cursor.fetchone()

            if count_email[0] == 1:
                cursor.execute(
                    'select user_password from userdata where useremail=%s',
                    [login_useremail]
                )
                stored_password = cursor.fetchone()

                if stored_password:
                    if bcrypt.checkpw(
                        login_password.encode('utf-8'),
                        stored_password[0]
                    ):
                        session['user'] = login_useremail
                        if not session.get(login_useremail):
                            session[login_useremail] = {}
                        
                        return redirect(url_for('home'))
                    else:
                        flash('Invalid password')
                else:
                    flash('Password not found')
            else:
                flash('Email not found')

        except Exception as e:
            print(e)
            flash('Could not verify login details')

        return redirect(url_for('userlogin'))

    return render_template('userlogin.html')

#userforgot password
@app.route('/userforgotpwd', methods=['GET','POST'])
def userforgotpwd():

    if request.method == 'POST':

        forgot_email = request.form['email']   # ✅ matches HTML

        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute(
                'select count(*) from userdata where useremail=%s',
                [forgot_email]
            )
            count_email = cursor.fetchone()[0]

        except Exception as e:
            print(e)
            flash('Could not verify email')
            return redirect(url_for('userforgotpwd'))

        if count_email == 1:

            subject = 'Reset link for BUYROUTE account'
            body = f'Use this link to reset your password:\n{url_for("userpassword", data=endata(forgot_email), _external=True)}'

            send_mail(to=forgot_email, body=body, subject=subject)

            flash('Reset link sent to your email')
            return redirect(url_for('userforgotpwd'))

        else:
            flash('Email not found')
            return redirect(url_for('userforgotpwd'))

    return render_template('userforgot.html')

#reset user password
@app.route('/userpassword/<data>',methods=['GET','PUT'])
def userpassword(data):
    if request.method=='PUT':
        newpassword=request.get_json()['newpassword']
        try:
            user_email=dndata(data)
            
        except Exception as e:
            print(e)
            flash('could not verify data')
            return redirect(url_for('userpassword',data=data))
        else:
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select count(*) from userdata where useremail=%s',[user_email])
                count_email=cursor.fetchone()[0]
            except Exception as e:
                print(e)
                flash('could not verify email')
                return redirect(url_for('userpassword',data=data))
            else:
                if count_email==1:
                    hash_password=bcrypt.hashpw(newpassword.encode('utf-8'),bcrypt.gensalt())
                    cursor.execute('update userdata set user_password=%s where useremail=%s',[hash_password,user_email])
                    mydb.commit()
                    cursor.close()
                    flash('Password updated successfully')
                    return jsonify({'message':'ok'})
                elif count_email==0:
                    flash('user email invalid')
                    return redirect(url_for('userpassword',data=data))
    return render_template('usernewpassword.html',data=data)


@app.route('/addcart/<itemid>',methods=['GET','POST'])
def addcart(itemid):
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)   
            cursor.execute('select bin_to_uuid(itemid),item_name,item_desc,item_category,item_price,item_about,item_image,item_quantity,added_by from items where itemid=uuid_to_bin(%s)',[itemid])
            item_details=cursor.fetchone()
            cursor.close()
        except Exception as e:
            print(e)
            flash('Could not retrieve item details')
            return redirect(url_for('home'))
        else:
            if itemid not in session[session.get('user')]:
                session[session.get('user')][itemid]=[item_details[1],item_details[4],item_details[7],item_details[6],item_details[3]]
                session.modified=True
                print(session)
                flash('Item added to cart')
                return redirect(url_for('home'))
            else:
                flash('Item already in cart')
                return redirect(url_for('home'))

    else:
        flash('Please login first to add items to cart')
        return redirect(url_for('userlogin'))
    

@app.route('/viewcart')
def viewcart():
    if session.get('user'):
        items=session[session.get('user')]
        print(items)
        sub_total=0
        for i,j in items.items():
            print(i,j)
            price=j[1]
            quantity=j[2]
            total=price*quantity
            sub_total=sub_total+total
        delivery=40
        tax=round(sub_total*0.05,2)
        grand_total=sub_total+delivery+tax
        return render_template('cart.html',items=items,sub_total=sub_total,delivery=delivery,tax=tax,grand_total=grand_total)
    else:
        flash('Please login first to view cart')
        return redirect(url_for('userlogin'))

@app.route('/updatecart/<itemid>',methods=['POST'])
def updatecart(itemid):
    if session.get('user'):
        item_quantity=int(request.form['quantity'])
        if itemid in session[session.get('user')]:
            session[session.get('user')][itemid][2]=item_quantity
            session.modified=True
            print(session)
            flash('Cart updated successfully')
            return redirect(url_for('viewcart'))
        else:
            flash('Item not in cart')
           
            return redirect(url_for('home'))
    else:
        flash('Please login first to update cart')
        return redirect(url_for('userlogin'))

@app.route('/removecart/<itemid>',methods=['GET','POST'])
def removecart(itemid):
    if session.get('user'):
       if itemid in session[session.get('user')]:
            session[session.get('user')].pop(itemid)
            session.modified=True
            print(session)
            flash('Item removed from cart')
            return redirect(url_for('viewcart'))
       else:
            flash('Item not in cart')
            return redirect(url_for('home'))
    else:
        flash('Please login first to remove item from cart')
        return redirect(url_for('userlogin'))

@app.route('/userlogout')
def userlogout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/category/<ctype>',methods=['GET'])
def category(ctype):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(itemid),item_name,item_desc,item_category,item_price,item_about,item_image,item_quantity from items where item_category=%s',[ctype])
        items=cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(e)
        flash('Could not retrieve category items')
        return redirect(url_for('home'))
    else:
        return render_template('dashboard.html',storeditem_data=items)

@app.route('/pay_cart',methods=['GET','POST'])
def pay_cart():
    if not session.get('user'):
        flash('pls login first to buy item')
        return redirect(url_for('userlogin'))
    try:
        # Fetch all items from cart
        cart=session.get(session.get('user'))
        if not cart:
            flash('No items in cart')
            return redirect(url_for('viewcart'))
        subtotal=0
        cart_items=[]
        for i,j in cart.items():
            item_name = j[0]
            item_price = j[1]
            item_quantity = j[2]
            item_image = j[3]
            item_category = j[4]
            amount=int(item_price)*int(item_quantity)
            subtotal=subtotal+amount
            cart_items.append({'id':i,
                               'name':item_name,
                               'price':item_price,
                               'quantity':item_quantity,
                               'item_img':item_image,
                               'item_category':item_category,
                               'subtotal':subtotal})
        delivery=40
        tax=round(subtotal*0.05,2)
        grand_total=subtotal+tax+delivery
        razorpay_amount=int(grand_total*100) #convert the gt into paise 
        #create razorpay order
        order=client.order.create({
            "amount":razorpay_amount,
            "currency":"INR",
            "receipt" : f"{session.get('user')}",
            "payment_capture":"1"
        })  
        print('order created')
        return render_template('pay.html',grand_total=grand_total,order=order,subtotal=subtotal,tax=tax,delivery=delivery,cart_items=cart_items)
    except Exception as e:
        print(e)
        flash('could not create an order now')
        return redirect(url_for('viewcart'))

@app.route('/success_cart',methods=['POST'])
def success_cart():
    try:
        payment_id=request.form['razorpay_payment_id']
        order_id=request.form['razorpay_order_id']
        signature=request.form['razorpay_signature']
        amount=float(request.form['grand_total'])
        # verify payment Signature
        param_dict={
            'razorpay_order_id':order_id,
            'razorpay_payment_id':payment_id,
            'razorpay_signature':signature
        }
        try:
            client.utility.verify_payment_signature(param_dict)
        except Exception as e:
            print(e)
            flash('payment verification failed')
            return redirect(url_for('home'))
        cart=session.get(session.get('user'),{})
        if not cart:
            flash('your cart is empty')
            return redirect(url_for('viewcart'))
        item_total=sum(float(v[1])*int(v[2]) for v in cart.values())
        #delivery+tax 
        delivery=40
        tax=round(item_total*0.05,2)
        grand_total=delivery+tax+item_total
        print(grand_total,amount)
        if grand_total==amount:
            #save the order details in database
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
                user=cursor.fetchone()[0]
                cursor.execute('insert into orders(razorpay_ordid,razorpay_paymentid,userid,total_amount,delivery,tax,grand_total) values(%s,%s,%s,%s,%s,%s,%s)',[order_id,payment_id,user,item_total,delivery,tax,grand_total])
                order_table_id=cursor.lastrowid
                insert_item='''insert into order_items(order_id,itemid,item_name,item_price,item_quantity,item_category,subtotal,item_filename) values(%s,uuid_to_bin(%s),%s,%s,%s,%s,%s,%s)'''
                for itemid,data in cart.items():
                    name=data[0]
                    price=float(data[1])
                    qyt=int(data[2])
                    img=data[3]
                    category=data[4]
                    subtotal=price*qyt
                    cursor.execute(insert_item,[order_table_id,itemid,name,price,qyt,category,subtotal,img])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('could not store order details')
                return redirect(url_for('pay_cart'))
            #clear cart after successfull payment
            session[session.get('user')]={}
            flash('Payment successfull')
            return redirect(url_for('home'))
    except Exception as e:
        app.logger.exception(f"Payment verification failed {e}")
        flash('Payment Failed')
        return redirect(url_for('home'))

@app.route('/myorders')
def myorders():
    if not session.get('user'):
        flash('pls login to fetch orders')
        return redirect(url_for('userlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user=cursor.fetchone()[0]
        cursor.execute('select * from orders where userid=%s',[user])
        myorders_data=cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(e)
        flash('DB error Could not fetch orders')
        return redirect(url_for('home'))
    else:
        return render_template('myorders.html',myorders_data=myorders_data)
@app.route('/myorder_details/<ordid>')
def myorder_details(ordid):
    if not session.get('user'):
        flash('pls login to fetch orders')
        return redirect(url_for('userlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user=cursor.fetchone()[0]
        cursor.execute('select * from orders where userid=%s and orderid=%s',[user,ordid])
        myorders_data=cursor.fetchone()
        cursor.execute('select order_detailsid,order_id,bin_to_uuid(itemid),item_name,item_price,item_quantity,subtotal,item_category,item_filename from order_items where order_id=%s',[ordid])
        order_details=cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(e)
        flash('could not fetch order details')
        return redirect(url_for('myorders'))
    else:
        return render_template('order_details.html',order_details=order_details,order_data=myorders_data)


if __name__=='__main__':
    app.run(debug=True,use_reloader=True)