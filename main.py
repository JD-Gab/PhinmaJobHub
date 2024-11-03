from flask import Flask, render_template, request, redirect, url_for, abort, session, flash, jsonify, send_from_directory
#from flask_mysqldb import MySQL
from flaskext.mysql import MySQL
from flask_mail import Mail, Message
from passlib.hash import sha256_crypt
from flask_socketio import SocketIO
import os
from werkzeug.utils import secure_filename
import datetime
import time
import re
from oauthlib.oauth2 import WebApplicationClient
import requests
import json
import random

app = Flask(__name__)
socketio = SocketIO(app)

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'sampledatabase'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
#app.config['MYSQL_PORT'] = 3306
#app.config['MYSQL_SSL'] = False

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'sample@gmail.com'
app.config['MAIL_PASSWORD'] = 'sample'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail= Mail(app)

app.secret_key = 'samplekey'

UPLOAD_FOLDER = 'static/assets/userfiles/resume'
PROFILEIMAGE_FOLDER = "static/assets/img"
profile_image_extensions = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['FILES_FOLDER'] = "files"
app.config['PROFILEIMAGE_FOLDER'] = PROFILEIMAGE_FOLDER

#mysql = MySQL(app)
mysql = MySQL()
mysql.init_app(app)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", '')
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", '')
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

client = WebApplicationClient(GOOGLE_CLIENT_ID)

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

def user_in_session():
    cursor = mysql.connect().cursor()
    

    try:
        if session:
            email = [session['email']]
            
            validate = cursor.execute('SELECT alumniid, emailaddress FROM alumniapplicants WHERE emailaddress = %s AND accountstatus = %s', (email,1))
            cursor.connection.commit()
            result = cursor.fetchall()
            
            if validate: 
                if session['userid'] == result[0][0] and session['email'] == result[0][1]:
                    
                    return True
                else:
                    pass
            else:
                pass
            
        else:
            pass
    except:
        return ''
    
def employer_in_session():
    cursor = mysql.connect().cursor()
    try:
        if session:
            email = session['email']
            companyid = session.get('userid')
            validate = cursor.execute('SELECT companyid, emailaddress FROM employeraccount WHERE emailaddress = %s', (email,))
            result = cursor.fetchall()
            
            if validate: 
                if companyid == result[0][0]:
                    return True
                else:
                    pass
            else:
                pass
        
        else:
            pass
    
    except:
        return ''
    
def admin_in_session():
    if 'loggedin' in session:
        email = session.get('email')
        adminid = session.get('userid')
        cursor = mysql.connect().cursor()

        verify = cursor.execute('SELECT * FROM adminaccount WHERE email = %s AND adminid = %s',(email,adminid))
        
        if verify:
            return True
        else:
            pass
    else:
        pass


#Returns category jobs
def catjobs():
    cursor = mysql.connect().cursor()
    cursor.execute('SELECT * FROM alumnijobs INNER JOIN employeraccount ON alumnijobs.companyid = employeraccount.companyid WHERE alumnijobs.jobstatus = %s',(1,))
    jobs = cursor.fetchall()
    cursor.connection.commit()
    cursor.close()

    return jobs

#Returns category names
def categorylist():
    cursor = mysql.connect().cursor()
    cursor.execute('SELECT category, categoryid, imagename FROM tblcategory')
    categories = cursor.fetchall()
    cursor.connection.commit()
    cursor.close()
    
    return categories

#Returns the total number of jobs within certain category
def categoryjobcount(field):

    cursor = mysql.connect().cursor()
    cursor.execute('SELECT COUNT(jobid) FROM alumnijobs WHERE category = %s AND jobstatus = %s',(field,1))
    result = cursor.fetchone()[0]
    
    return result

#Returns the location names 
def locationlist():
    cursor = mysql.connect().cursor()
    cursor.execute('SELECT location, locationid FROM joblocation')
    location = cursor.fetchall()
    cursor.connection.commit()
    cursor.close()

    return location

#Returns the total number of jobs in certain locations
def locationjobcount(field):
    field1 = field[0]
    cursor = mysql.connect().cursor()
    cursor.execute("SELECT COUNT(jobid) FROM alumnijobs WHERE joblocation LIKE '%{0}%' AND jobstatus = {1}".format(field1,1))
    result = cursor.fetchone()[0]
    
    return result

#Search function for both What and Where of Search Function input box
def search_function():
    searchlist = []
    searchindex = []

    cursor = mysql.connect().cursor()
    what = request.form['whattoinput']
    where = request.form['loctoinput']
    
    cursor.execute('SELECT * FROM alumnijobs aj INNER JOIN employeraccount ec ON aj.companyid = ec.companyid WHERE aj.jobstatus = %s',(1,))
    searchresult = cursor.fetchall()

    for i, tup in enumerate(searchresult):
        
        stringword = ' '.join(str(x) for x in tup)
        stringloc = ''.join(x for x in tup[12])
        whatmatches = re.findall(what.lower(),stringword.lower())
        locmatches = re.findall(where.lower(),stringloc.lower())
        if whatmatches and locmatches:
            searchindex.append(i)

    for num in searchindex:
        searchlist.append(searchresult[num])

    return searchlist

#Returns the jobs when either category lists or location lists were clicked
def indexcategories(category):
    cursor = mysql.connect().cursor()
    indexcat = cursor.execute('SELECT * FROM alumnijobs aj INNER JOIN employeraccount ea ON aj.companyid = ea.companyid WHERE category = %s AND aj.jobstatus = %s', [category,1])
    result = cursor.fetchall()

    validloc = cursor.execute("SELECT * FROM alumnijobs aj INNER JOIN employeraccount ea ON aj.companyid = ea.companyid WHERE aj.joblocation LIKE '%{0}%' AND aj.jobstatus = {1}".format(category,1))
    result3 = cursor.fetchall()

    if indexcat:
        return result
    elif validloc:
        return result3
    else:
        return '' 

#Returns the top rated jobs shown at the right side of the user homepage
def topratedjobs():
    cursor = mysql.connect().cursor()
    cursor.execute('SELECT aj.jobid, aj.jobtitle, ea.companyname, aj.jobdescription, aj.jobtype, aj.joblocation, aj.minsal, aj.maxsal, ea.companyid, ea.profileimage FROM alumnijobs aj INNER JOIN employeraccount ea ON aj.companyid = ea.companyid WHERE aj.jobstatus = %s ORDER BY jobid DESC LIMIT 3',(1,))
    result = cursor.fetchall()
    
    return result

#Returns the job IDs of jobs that are marked as 1 (aka saved) in the alumnisavedjobs table in the database
def returnsavedjobs():
    try:
        cursor = mysql.connect().cursor()
        cursor.execute('SELECT jobid FROM alumnisavedjobs WHERE alumniid = %s AND saved = %s AND savedjobstatus = %s',(str(session['userid']),1,1))
        result = cursor.fetchall()
        return result
    except:
        pass

#Function for checking if the resumes submitted from file input is valid or not
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Function for checking if the pictures submitted from profile is valid or not
def allowed_image(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in profile_image_extensions
    
#Returns the jobs that are considered -applied-. It is considered applied if the job ID is retrieved from the alumniapplicants table with the same alumni ID
#There can only be one job ID for every jobs that the user applied in, within their own user ID. 
def returnappliedjobs(userid):
    cursor = mysql.connect().cursor()
    cursor.execute('SELECT jobid FROM alumniapplication WHERE alumniid = %s AND applicationstatus = %s',(str(userid),1))
    result = cursor.fetchall()
    
    applied = [x[0] for x in result]

    return applied
    

def getEmployer():
    userid = session.get('userid')
    cursor = mysql.connect().cursor()
    cursor.execute('SELECT * FROM employeraccount WHERE companyid = %s AND accountstatus = %s',(str(userid),1))
    result = cursor.fetchall()
    return result

def getApplicants():
    cursor = mysql.connect().cursor()
    companyid = session.get('userid')
    applicantsdata_in_list = []
    jobtitles = []

    cursor.execute('SELECT aa.alumniid, aa.jobid, aa.dateapplied, aa.resumename, aa.remark, aa.application_ID, aa.Email, aa.Career_history, aa.Skills, aa.First_name, aa.Last_name, aa.Contact_no, aa.Address, aj.category FROM alumniapplication aa LEFT JOIN alumnijobs aj ON aa.jobid = aj.jobid WHERE aa.companyid = %s AND aa.applicationstatus = %s',(str(companyid),1))
    applicationdata = cursor.fetchall()

    cursor.execute('SELECT up.fullname, aa.address, aa.alumniid, aa.profileimage FROM alumniapplicants AS aa INNER JOIN userprofile AS up ON aa.alumniid = up.alumniid WHERE accountstatus = %s',(1,))
    applicantdata = cursor.fetchall()

    cursor.execute('SELECT * FROM alumnijobs WHERE companyid = %s AND jobstatus = %s',(str(companyid),1))
    jobs = cursor.fetchall()

    try:
        jobtitles = [j[3] for i in applicationdata for j in jobs if i[1] == j[0]]
    except:
        pass

    counter = 0
    try:
        for i in applicationdata:
            for j in applicantdata:
                if i[0] == j[2]:
                    convertedlist = list(j)
                    convertedlist.pop()
                    convertedlist.append(jobtitles[counter])
                    convertedlist.append(i[2])
                    convertedlist.append(i[1])
                    convertedlist.append(i[3])
                    convertedlist.append(j[3])
                    convertedlist.append(i[4])
                    convertedlist.append(i[5])
                    convertedlist.append(i[6::])
                    counter = counter + 1
                    applicantsdata_in_list.append(convertedlist)
    except:
        pass

    return applicantsdata_in_list

def get_employer_job_search_function():
    companyid = session.get('userid')
    
    cursor = mysql.connect().cursor()
    searchword = request.form.get('searchword')
    query = "SELECT * FROM alumnijobs WHERE companyid = {0} AND (jobtitle LIKE '%{1}%' OR category LIKE '%{2}%') AND jobstatus = {3} "
    cursor.execute(query.format(str(companyid),searchword,searchword,1))
    result = cursor.fetchall()
    return result

def get_applicants_from_jobid(id,title):
    cursor = mysql.connect().cursor()
    companyid = session.get('userid')
    alumni_IDs = []
    combined_data_per_applicant = []

    cursor.execute('SELECT alumniid, dateapplied, resumename, application_ID, remark, Email, Career_history, Skills, First_name, Last_name, Contact_no, Address FROM alumniapplication WHERE jobid = %s AND companyid = %s AND applicationstatus = %s',(id,companyid,1))
    result = cursor.fetchall()

    alumni_IDs = [x[0] for x in result]

    print(alumni_IDs)

    cursor.execute('SELECT up.fullname, aa.address, aa.alumniid, aa.profileimage FROM alumniapplicants aa INNER JOIN userprofile up ON aa.alumniid = up.alumniid WHERE accountstatus = %s',(1,))
    applicantdata = cursor.fetchall()
    

    for i in result:
        for j in applicantdata:
            if i[0] == j[2]:
                applicantdataconvertedtolist = list(j)
                applicantdataconvertedtolist.pop()
                applicantdataconvertedtolist.append(i[1])
                applicantdataconvertedtolist.append(i[2])
                applicantdataconvertedtolist.append(title)
                applicantdataconvertedtolist.append(j[3])
                applicantdataconvertedtolist.append(i[3])
                applicantdataconvertedtolist.append(i[4])
                applicantdataconvertedtolist.append(i[5::])

                combined_data_per_applicant.append(applicantdataconvertedtolist)

    return combined_data_per_applicant

def applicants_by_notif(alumniid):

    cursor = mysql.connect().cursor()

    cursor.execute('SELECT * FROM alumniapplication aap INNER JOIN alumniapplicants aa ON aap.alumniid = aa.alumniid INNER JOIN userprofile up ON aap.alumniid = up.alumniid WHERE aap.alumniid = %s AND aap.applicationstatus = %s',(alumniid,1))
    result = cursor.fetchall()

    return result

def usernotification():
    cursor = mysql.connect().cursor()
    alumniid = session.get('userid')

    cursor.execute('SELECT ea.companyname, aa.dateapplied, aa.approveddate, ea.profileimage FROM alumniapplication aa INNER JOIN employeraccount ea ON aa.companyid = ea.companyid WHERE aa.alumniid = %s ORDER BY aa.dateapplied OR aa.approveddate DESC',(alumniid,))
    result = cursor.fetchall()

    notification_data = result[::-1]

    return notification_data

def employernotification():

    userid = session.get('userid')
    cursor = mysql.connect().cursor()

    info = []
        
    cursor.execute('SELECT aa.alumniid, aa.jobid, aa.dateapplied, up.fullname, aj.jobtitle, aa.application_ID FROM alumniapplication aa INNER JOIN userprofile up ON aa.alumniid = up.alumniid INNER JOIN alumnijobs aj ON aa.jobid = aj.jobid WHERE aa.companyid = %s ORDER BY aa.application_ID ASC',(userid,))
    result = cursor.fetchall()

    cursor.execute('SELECT aa.profileimage, aa.alumniid FROM alumniapplication aap INNER JOIN alumniapplicants aa ON aa.alumniid = aap.alumniid WHERE aap.companyid = %s ORDER BY aap.application_ID ASC',(userid,))
    profileimages = cursor.fetchall()
        
    
    if result:
        info = [list(x) for x in result[::-1]]

        n = 0
        for i in profileimages[::-1]:
            info[n].append(i[0])
            info[n][5], info[n][6] = info[n][6], info[n][5]
            n = n+1

    return info

def userreviewsection(id):

    cursor = mysql.connect().cursor()

    alumniid = session.get('userid')
    cursor.execute('SELECT aa.alumniid, aa.profileimage, up.fullname, r.comment, r.review_ID FROM alumniapplicants aa INNER JOIN userprofile up ON aa.alumniid = up.alumniid INNER JOIN reviews r ON aa.alumniid = r.alumniid WHERE aa.alumniid =  %s AND r.companyid = %s',(alumniid,id))
    result = cursor.fetchall()

    return result

def totalreviews(id):

    cursor = mysql.connect().cursor()

    cursor.execute('SELECT up.fullname, aa.profileimage, r.comment FROM reviews r INNER JOIN alumniapplicants aa ON r.alumniid = aa.alumniid INNER JOIN userprofile up ON up.alumniid = r.alumniid WHERE r.companyid = %s AND aa.accountstatus = %s',(id,1))
    result = cursor.fetchall()

    return result

def getalumniname():

    cursor = mysql.connect().cursor()
    alumniid = session.get('userid')

    cursor.execute('SELECT fname FROM userprofile WHERE alumniid = %s',(alumniid,))
    result = cursor.fetchone()[0]

    return result

def filter_applicants(locationinput, categoryinput, searchword, applicants):

    filterresult = []
    for i, tup in enumerate(applicants):
        
        stringword = ' '.join(str(x) for x in tup)
        stringloc = ''.join(x for x in tup[1])
        stringcat = ''.join(x for x in tup[10][7])
        whatmatches = re.findall(searchword.lower(),stringword.lower())
        locmatches = re.findall(locationinput.lower(),stringloc.lower())
        catmatches = re.findall(categoryinput.lower(),stringcat.lower())
        if whatmatches and locmatches and catmatches:
            filterresult.append(applicants[i])

    return filterresult

def paginatedjob(jobpage,query):

    per_page = 5  # Number of items per page
    offset = (jobpage - 1) * per_page

    cursor = mysql.connect().cursor()
    cursor.execute(
        query,
        (1, per_page, offset))
    users = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM alumnijobs")
    total = cursor.fetchone()[0]
    totalpage = (total + per_page - 1) // per_page

    return [users, totalpage]


    #------------------------END OF CUSTOM FUNCTIONS------------------------------------

def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')

@socketio.on('my event')
def handle_my_custom_event(json, methods=['GET', 'POST']):
    print('received my event: ' + str(json))

    username = message = userid = ''
    try:
        username = str(json['user_name'])
        message = str(json['message'])
        userid = str(json['id'])
    except:
        pass

    email = session.get('email')
    ownid = session.get('userid')
    if username or message or userid:
        cursor = mysql.connect().cursor()
        alumniverify = cursor.execute('SELECT * FROM alumniapplicants WHERE alumniid = %s AND emailaddress = %s',(ownid,email))

        if alumniverify:
            cursor.execute('INSERT INTO messages(alumniid,companyid,username,message) VALUES(%s,%s,%s,%s)',(ownid,userid,username,message))
            cursor.connection.commit()
        else:
            cursor.execute('INSERT INTO messages(alumniid,companyid,username,message) VALUES(%s,%s,%s,%s)',(userid,ownid,username,message))
            cursor.connection.commit()
            cursor.close()

    socketio.emit('my response', json, callback=messageReceived)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route("/contactsend", methods=['POST','GET'])
def contactsend():
   if request.method == 'POST':

    email = request.form.get('email')
    
    newpass = random.randint(1,999999999)

    message = f'Your emergency created password is {newpass}. Please change your password as soon as you enter your account.'

    try:
        msg = Message('PHINMA Job Hub Password Change', sender = 'sample@gmail.com', recipients = [email])
        msg.body = message
        mail.send(msg)
        flash('Password review sent! Please check your email to get the emergency password.')
    except:
        flash('An error in the password change has occured. Please try again in a moment.')
        return redirect(url_for('forgotpassword'))

    cursor = mysql.connect().cursor()
    try:
        cursor.execute('UPDATE alumniaccount SET password = %s WHERE emailaddress = %s',(newpass,email))
        cursor.connection.commit()
    except:
        pass
    try:
        cursor.execute('UPDATE employeraccount SET password = %s WHERE emailaddress = %s',(newpass,email))
        cursor.connection.commit()
    except:
        pass
    cursor.close()

    return redirect(url_for('forgotpassword'))

#=========================================================================================================================
#-------------------------------------------------------ALUMNI ROUTES PART--------------------------------------------------
#=========================================================================================================================

#Landing Page
@app.route('/')
def index():

    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    else:
        pass

    cursor = mysql.connect().cursor()


    cursor.execute('SELECT * FROM tblcategory')
    categories = cursor.fetchall()

    jobdetails = list(catjobs())
    jobdetails1 = jobdetails[:5]

    return render_template('index.html', categories = categories, jobdetails = jobdetails1)

#Company page
@app.route('/company')
def company():
    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    else:
        pass

    cursor = mysql.connect().cursor()

    cursor.execute('SELECT * FROM employeraccount WHERE accountstatus = %s',(1,))
    result = cursor.fetchall()
    
    return render_template('company.html', result = result)


@app.route('/aboutUs')
def aboutus():

    return render_template('about.html')

@app.route('/contact')
def contact():

    return render_template('contact.html')

#Company profile page
@app.route('/company-profile/<id>')
def company_profile(id):

    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    else:
        pass

    cursor = mysql.connect().cursor()
    cursor.execute('SELECT * FROM employeraccount WHERE companyid = %s AND accountstatus = %s', (id,1))
    result = cursor.fetchall()

    cursor.execute('SELECT aj.jobid, aj.jobtitle, ea.companyname, aj.category, aj.jobdescription, aj.jobtype, aj.joblocation, aj.minsal, aj.maxsal FROM alumnijobs aj INNER JOIN employeraccount ea ON aj.companyid = ea.companyid WHERE aj.companyid = %s AND aj.jobstatus = %s', (id,1))
    compjobs = cursor.fetchall()

    totalreview = totalreviews(id)

    return render_template('company-profile.html', result = result, compjobs = compjobs, reviews = totalreview)

#Categories page
@app.route('/categories/<c>', methods=['POST','GET'])
def categories(c):

    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    else:
        pass

    searches = []
    num_per_job = []
    num_per_loc_job = []

    indexcatresult = indexcategories(c)

    catlist = list(categorylist())
    num_per_job = [categoryjobcount(num[0]) for num in catlist]

    loclist = list(locationlist())
    num_per_loc_job = [locationjobcount(num) for num in loclist]


    topratedjobslist = topratedjobs()

    if request.method == 'POST':
        searches = list(search_function())
        if not searches:
            flash('Nothing matches your search. Please try again')


    query = "SELECT * FROM alumnijobs INNER JOIN employeraccount ON alumnijobs.companyid = employeraccount.companyid WHERE alumnijobs.jobstatus = %s LIMIT %s OFFSET %s"
    jobpage = request.args.get('pagesNum', 1, type=int)

    jobs, totalpage = paginatedjob(jobpage,query)[0], paginatedjob(jobpage,query)[1]

    return render_template('categories.html', categories = catlist, joblocation = loclist, jobs = jobs, searches = searches, color = 'warning', icr = indexcatresult, jobnum = num_per_job, locjobnum = num_per_loc_job, rated = topratedjobslist, jobpage = jobpage, totalpage = totalpage)

#Job single page
@app.route('/job-details/<id>')
def job_details(id):

    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    else:
        pass

    num_per_job = []
    num_per_loc_job = []
    
    cursor = mysql.connect().cursor()
    cursor.execute('SELECT * FROM alumnijobs INNER JOIN employeraccount ON alumnijobs.companyid = employeraccount.companyid WHERE alumnijobs.jobid = %s AND alumnijobs.jobstatus = %s', (id,1))
    result = cursor.fetchall()


    catlist = list(categorylist())
    num_per_job = [categoryjobcount(num[0]) for num in catlist]

    loclist = list(locationlist())
    num_per_loc_job = [locationjobcount(num) for num in loclist]

    topratedjobslist = topratedjobs()
    
    return render_template('job-single.html', result = result, catlist = catlist, loclist = loclist, numjob = num_per_job, locnumjob = num_per_loc_job, rated = topratedjobslist)

#User Login/Signup page
@app.route('/user',methods=['GET'])
def userpage():

    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    else:
        pass

    return render_template('/userpage/userlogin.html')

#User Signup process to insert in database
#Making user profile row in userprofile table
@app.route('/usersignup', methods=['POST'])
def usersignup():

    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    else:
        pass

    if request.method == 'POST':
        cursor = mysql.connect().cursor()
        email = request.form.get('emailsignup')
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        fullname = firstname + ' ' + lastname
        pass1 = request.form.get('passwordsignup')
        pass2 = request.form.get('password2signup')
        accountcreated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('SELECT emailaddress, alumniid FROM alumniapplicants')
        result = cursor.fetchall()

        providedID = random.randint(1,999999)
        takenID = [int(id[1]) for id in result]
        if providedID in takenID:
            providedID = random.randint(1,999999)
        else:
            pass
        
        for emails in result:
            if email == emails[0]:
                flash('Account already exists')
                return render_template('/userpage/userlogin.html', color = 'danger', notice = 'Error!')
            
        if pass1 != pass2:
            flash('Password mismatch. Please try again')
            return render_template('/userpage/userlogin.html', color = 'danger', notice = 'Error!')
        
        elif email == None or pass1 == None or pass2 == None:
            flash('Please fill out the signup')
            return render_template('/userpage/userlogin.html', color = 'danger', notice = 'Error!')
        
        else:
            hashpass1 = sha256_crypt.encrypt(pass1)
            
            cursor.execute('INSERT INTO alumniapplicants(emailaddress, password, alumniid, accountcreated) VALUES (%s, %s, %s, %s)',(email, hashpass1, providedID, accountcreated))
            cursor.connection.commit()

            cursor.execute('SELECT alumniid FROM alumniapplicants WHERE emailaddress = %s',[email])
            alumniid = cursor.fetchone()[0]

            cursor.execute('INSERT INTO userprofile(alumniid, fname, lname, fullname) VALUES (%s, %s, %s, %s)', (alumniid, firstname, lastname, fullname))
            cursor.connection.commit()
            cursor.close()
            
            flash('Signed up successfully! You can now log in.')
            return render_template('/userpage/userlogin.html', color = 'success', notice = 'Done!')

    return redirect(url_for('userpage'))

@app.route('/googlelogin')
def googlelogin():
    try:# Find out what URL to hit for Google login
        google_provider_cfg = get_google_provider_cfg()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]

        # Use library to construct the request for Google login and provide
        # scopes that let you retrieve user's profile from Google
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=request.base_url + "/callback",
            scope=["openid", "email", "profile"],
        )
        return redirect(request_uri)
    except requests.exceptions.ConnectionError as e:
        Error = "Cannot connect to your google account right now. Please try again later."
        return render_template('/userpage/userlogin.html', error = Error)


@app.route('/googleloginprocess')
def googleloginprocess():
    email = request.args.get('email')

    cursor = mysql.connect().cursor()

    verify = cursor.execute('SELECT * FROM alumniapplicants WHERE emailaddress = %s',(email,))
    result = cursor.fetchall()

    if verify:
        session['loggedin'] = True
        session['email'] = result[0][1]
        session['userid'] = result[0][0]

        return redirect(url_for('user_homepage', page = 0))
    else:
        flash('Something went wrong.')
        return redirect(url_for('userpage'))

@app.route('/googlelogin/callback')
def callback():
    cursor = mysql.connect().cursor()
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    try:
        userinfo_response = requests.get(uri, headers=headers, data=body, timeout=5)
    except requests.exceptions.ConnectionError as e:
        userinfo_response = "No response"

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    verify = cursor.execute('SELECT * FROM alumniapplicants WHERE alumniid = %s',(unique_id,))
    result = cursor.fetchall()

    if not verify:
        cursor.execute('INSERT INTO alumniapplicants(alumniid,emailaddress,profileimage) VALUES (%s,%s,%s)',(unique_id,users_email,picture))
        cursor.execute('INSERT INTO userprofile(alumniid,fullname) VALUES (%s,%s)',(unique_id,users_name))
        cursor.connection.commit()

        return redirect(url_for('googleloginprocess', email = users_email))
    else:
        session['loggedin'] = True
        session['email'] = result[0][1]
        session['userid'] = result[0][0]

        return redirect(url_for('user_homepage', page = 0))
    

#Login process to login the user homepage, or after finishing Signup process
@app.route('/user',methods=['POST','GET'])
def homepagelogin():

    cursor = mysql.connect().cursor()
    email = request.form['emaillogin']
    password = request.form['passwordlogin']
    Error = None

    if request.method == 'POST':
        result = cursor.execute('SELECT password,emailaddress,alumniid, accountstatus FROM alumniapplicants WHERE emailaddress = %s',(email,))
        hashedresult = cursor.fetchone()
        
        if result:
            if int(hashedresult[3]) == 0:

                Error = 'Account not found.'
                return render_template('/userpage/userlogin.html', error = Error)

            if hashedresult[1] == email and sha256_crypt.verify(password, hashedresult[0]):
                session['loggedin'] = True
                session['userid'] = hashedresult[2]
                session['email'] = hashedresult[1]

                return  redirect(url_for('user_homepage', page = 0))
            else:
                Error = 'Incorrect Email or Password...'
                return render_template('/userpage/userlogin.html', error = Error)

        else:
            Error = 'Incorrect Email or Password...'
            return render_template('/userpage/userlogin.html', error = Error)
        
    return redirect(url_for('userpage'))

@app.route('/forgotpass')
def forgotpassword():
            
    return render_template('changepassword.html')

#Route for logging out of users/employers
@app.route('/logout')
def logout():

    email = session.get('email')
    cursor = mysql.connect().cursor()
    adminlogout = cursor.execute('SELECT * FROM adminaccount WHERE email = %s',(email,))

    if adminlogout:
        session.pop('loggedin', None)
        session.pop('userid', None)
        session.pop('email', None)

        return redirect(url_for('adminlogin'))
    else:
        session.pop('loggedin', None)
        session.pop('userid', None)
        session.pop('email', None)

        return redirect(url_for('index'))

#Route for profile data
@app.route('/profiledata',methods = ['POST','GET'])
def profile_data():

    cursor = mysql.connect().cursor()
    
    try:
        result = request.json['data']
        query = "UPDATE alumniapplicants SET company1 = %s, profession1 = %s, company2 = %s, profession2 = %s, education1 = %s, education2 = %s, skills = %s WHERE alumniid = %s"

        cursor.execute(query,(result[2],result[3],result[4],result[5],result[6],result[7],result[8],str(session['userid'])))
        cursor.connection.commit()
        cursor.close()
        
    except:
        pass

    try:
        phone = request.form.get('phone')
        address = request.form.get('address')

        if phone != None or address != None:
            query = "UPDATE alumniapplicants SET phone = %s, address = %s WHERE alumniid = %s"
            cursor.execute(query,(phone,address,str(session['userid'])))
            cursor.connection.commit()
            cursor.close()
        else:
            pass
    except:
        pass

    try:
        worktype = request.form.get('worktype')
        salary = request.form.get('salary')
        salarytype = request.form.get('selectedOption')
        location = request.form.get('location')
        avail = request.form.get('avail')

        if worktype != None or salary != None or salarytype != None or location != None or avail != None:
            query = "UPDATE alumniapplicants SET worktype = %s, salary = %s, salarytype = %s, location = %s, avail = %s WHERE alumniid = %s"
            cursor.execute(query,(worktype,salary,salarytype,location,avail,str(session['userid'])))
            cursor.connection.commit()
            cursor.close()
        else:
            pass
    except:
        pass

    if request.method == 'POST':
        alumniid = session.get('userid')
        about = request.form['about']
        cursor.execute('UPDATE alumniapplicants SET about = %s WHERE alumniid = %s',(about,alumniid))
        cursor.connection.commit()
        cursor.close()

        return redirect(url_for('user_homepage', page = 4))

    return ''

#User logged in pages
@app.route('/userhomepage/<int:page>', methods=['POST','GET'])
def user_homepage(page):

    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    if 'loggedin' not in session:
        return redirect(url_for('index'))
    else:
        pass

    c = request.args.get('c')
    userid = session.get('userid')
    
    cursor = mysql.connect().cursor()
    cursor.execute('SELECT aj.jobtitle, aj.category, aj.jobdescription, aj.jobtype, aj.joblocation, aj.minsal, aj.maxsal, ea.companyname, aj.jobid, ea.companyid, ea.profileimage, aj.joblevel FROM alumnijobs aj INNER JOIN employeraccount ea ON aj.companyid = ea.companyid WHERE aj.jobstatus = %s',(1,))
    results = cursor.fetchall()

    userfname = getalumniname()

    #PAGE 0 IS THE USER HOMEPAGE/USER INDEX PAGE
    if page == 0:
        searches = []
        num_per_job = []
        num_per_loc_job = []
        indexcatresult = []
        savedjobid_index = []

        try:
            indexcatresult = indexcategories(c)
        except:
            pass

        catlist = list(categorylist())
        num_per_job = [categoryjobcount(num[0]) for num in catlist]

        loclist = list(locationlist())
        num_per_loc_job = [locationjobcount(num) for num in loclist]

        topratedjobslist = topratedjobs()

        bookmarkedjobs = returnsavedjobs()

        try:
            savedjobid_index = [i[0] for i in bookmarkedjobs]
        except:
            savedjobid_index = []

        applied = returnappliedjobs(userid)
        
        if request.method == 'POST':
            searches = list(search_function())
            if not searches:
                flash('Nothing matches your search. Please try again')

        """if results:
            return jsonify({
                'success': True,
                'results': results,
                'count': len(results)
            })"""

        jobpage = request.args.get('pagesNum', 1, type=int)
        query = "SELECT aj.jobtitle, aj.category, aj.jobdescription, aj.jobtype, aj.joblocation, aj.minsal, aj.maxsal, ea.companyname, aj.jobid, ea.companyid, ea.profileimage, aj.joblevel FROM alumnijobs aj INNER JOIN employeraccount ea ON aj.companyid = ea.companyid WHERE aj.jobstatus = %s LIMIT %s OFFSET %s"

        jobs, totalpage = paginatedjob(jobpage,query)[0], paginatedjob(jobpage,query)[1]

        
        return render_template('/userpage/userhomepage.html', results = jobs, catlist1 = catlist, loclist = loclist, jobnum = num_per_job, locjobnum = num_per_loc_job, icr = indexcatresult, ratedjob = topratedjobslist, searches = searches, userid = userid, saved = savedjobid_index, appliedposts = applied, name = userfname, jobpage = jobpage, totalpage = totalpage)
    
    #PAGE 1 IS THE COMPANY LIST PAGE
    elif page == 1:
        cursor.execute('SELECT * FROM employeraccount WHERE accountstatus = %s',(1,))
        companyresult = cursor.fetchall()

        return render_template('/userpage/usercompany.html', result = companyresult, name = userfname)
    
    #PAGE 2 IS FOR USER MESSAGES 
    elif page == 2:
        alumniid = session.get('userid')

        cursor.execute('SELECT fullname FROM userprofile WHERE alumniid = %s',(alumniid,))
        name = cursor.fetchone()[0]

        id = companydata = messages = ''

        cursor.execute('SELECT ea.companyid, ea.companyname, ea.profileimage FROM messages m INNER JOIN employeraccount ea ON m.companyid = ea.companyid WHERE m.alumniid = %s AND ea.accountstatus = %s GROUP BY ea.companyid',(str(alumniid),1))
        result = cursor.fetchall()

        try:
            id = request.args.get('id')
        except:
            pass

        if id:
            cursor.execute('SELECT companyname, profileimage FROM employeraccount WHERE companyid = %s',(id,))
            companydata = cursor.fetchall()

            cursor.execute('SELECT message, companyid, username FROM messages WHERE companyid = %s AND alumniid = %s',(id,alumniid))
            messages = cursor.fetchall()

        return render_template('/userpage/usermessages.html', result = result, companydata = companydata, messages = messages, name = name, id = id, name1 = userfname)
    
    #PAGE 3 IS FOR USER NOTIFICATIONS
    elif page == 3:

        notification = usernotification()

        return render_template('/userpage/usernotification.html', notification = notification, name = userfname)
    
    #PAGE 4 IS FOR USER PROFILE
    elif page == 4:
        userid = session.get('userid')
        monthly = yearly = ''

        cursor.execute('SELECT * FROM alumniapplicants aa INNER JOIN userprofile up ON aa.alumniid = up.alumniid WHERE aa.alumniid = %s AND aa.accountstatus = %s',(str(userid),1))
        profile = cursor.fetchall()

        for i in profile:
            if i[14] == 'Monthly':
                monthly = 'checked'
            elif i[14] == 'Yearly':
                yearly = 'checked'

        salarytype = [monthly,yearly]
        
        return render_template('/userpage/userprofile.html', profile = profile, salarytype = salarytype, name = userfname)
    
    #PAGE 5 IS FOR USER SAVED JOBS AND APPLIED JOBS
    elif page == 5:

        savedjobid_index = []
        jobs_with_saved_mark = []
        applied = ''
        post_of_applied_jobs = []
        savedIsTrue = 'false'
        appliedIsTrue = 'false'
        tabIsTrue = [[savedIsTrue,'',''],[appliedIsTrue,'','']]

        try:
            applied = request.args.get('tab')
        except:
            pass

        if applied == 'savedjob':
            savedIsTrue = 'true'
            tabIsTrue[0][1] = 'show active'
            tabIsTrue[0][2] = 'active'
        elif applied == 'appliedjob':
            appliedIsTrue = 'true'
            tabIsTrue[1][1] ='show active'
            tabIsTrue[1][2] = 'active'

        bookmarkedjobs = returnsavedjobs()
        savedjobid_index = [i[0] for i in bookmarkedjobs]

        jobs_with_saved_mark = [i for i in results if i[8] in savedjobid_index]

        applied = returnappliedjobs(userid)
        post_of_applied_jobs = [i for i in results if i[8] in applied]

        return render_template('/userpage/usersavedjobs.html', saved = jobs_with_saved_mark, userid = userid, applied = applied, tabs = tabIsTrue, postJobWithAppliedStat = post_of_applied_jobs, savedindex = savedjobid_index, appliedposts = applied, name = userfname)
    
    #PAGE 6 IS FOR USER SETTINGS
    elif page == 6:

        cursor.execute('SELECT up.fullname, aa.emailaddress, up.address, up.username, aa.password FROM alumniapplicants aa INNER JOIN userprofile up ON aa.alumniid = up.alumniid WHERE aa.alumniid = %s AND accountstatus = %s',[session['userid'],1])
        settings = cursor.fetchall()

        tab1 = tab2 = 'active'
        tab2 = request.args.get('tab2')
        if tab2:
            tab1 = ''
        else:
            tab1 = 'active'
            tab2 = ''
        activetab = [tab1, tab2]

        return render_template('/userpage/usersettings.html', settings = settings, active = activetab, name = userfname)
    
    #PAGE 7 IS FOR LOGGING OUT
    elif page == 7:
        
        return redirect(url_for('logout'))
    elif page == 8:
        return render_template('/userpage/contact.html', name = userfname)
    elif page == 9:
        return render_template('/userpage/about.html', name = userfname)
    else:
        return abort(404)

#ROUTE FOR USER SETTINGS DATA PROCESSING
@app.route('/settingsupdate', methods=['POST','GET'])
def settingsupdate():

    action = request.args.get('action')
    alumniid = session.get('userid')

    if request.method == 'POST':
        cursor = mysql.connect().cursor()

        if action == 'update':
            fullname = request.form['fullname']
            email = request.form.get('email')
            address = request.form['address']
            userid = session.get('userid')
            cursor.execute('UPDATE userprofile up INNER JOIN alumniapplicants aa ON up.alumniid = aa.alumniid SET up.fullname = %s, aa.emailaddress = %s, up.address = %s WHERE aa.alumniid = %s AND aa.accountstatus = %s',(fullname,email,address,str(userid),1))
            cursor.connection.commit()
            cursor.close()
            return redirect(url_for('user_homepage', page=6))
        
        if action == 'delete':
            cursor.execute('DELETE alumniapplicants, userprofile FROM alumniapplicants ON alumniapplicants.alumniid = userprofile.alumniid WHERE alumniapplicants.alumniid = %s',(alumniid,))
            try:
                cursor.execute('DELETE FROM alumnisavedjobs WHERE alumniid = %s',(alumniid,))
            except:
                pass
            try:
                cursor.execute('DELETE FROM alumniapplication WHERE alumniid = %s',(alumniid,))
            except:
                pass
            try:
                cursor.execute('DELETE FROM messages WHERE alumniid = %s',(alumniid,))
            except:
                pass
            try:
                cursor.execute('DELETE FROM reviews WHERE alumniid = %s',(alumniid,))
            except:
                pass

            cursor.connection.commit()
            cursor.close()
            
            return redirect(url_for('user_homepage', page = 7))

        if action == 'update_pass':
            cursor.execute('SELECT password FROM alumniapplicants WHERE alumniid = %s',(alumniid,))
            result = cursor.fetchone()[0]
            oldpass = request.form['oldpass']
            newpass = request.form['newpass']
            verifynewpass = request.form['verifynewpass']

            if not oldpass or not newpass or not verifynewpass:
                flash('Please fill up the forms.')
                return redirect(url_for('user_homepage', page = 6, tab2 = 'active'))
            if not sha256_crypt.verify(oldpass,result):
                flash('Incorrect password. Try again.')
                return redirect(url_for('user_homepage', page = 6, tab2 = 'active'))
            if newpass != verifynewpass:
                flash('Password does not match. Please try again.')
                return redirect(url_for('user_homepage', page = 6, tab2 = 'active'))
            else:
                newpassword = sha256_crypt.encrypt(newpass)
                cursor.execute('UPDATE alumniapplicants SET password = %s WHERE alumniid = %s',(newpassword,alumniid))
                cursor.connection.commit()
                cursor.close()

                flash('Password changed.')
                return redirect(url_for('user_homepage', page = 6, tab2 = 'active'))
        else:
            return redirect(url_for('user_homepage', page = 6))

    return redirect(url_for('user_homepage', page = 6))

#Route for job details/job descriptions inside user logged-in homepage
@app.route('/user-job-details/<id>')
def userjobdetails(id):

    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    if 'loggedin' not in session:
        return redirect(url_for('index'))
    else:
        pass
    
    num_per_job = []
    num_per_loc_job = []
    bookmarked = 'bi-heart-fill'
    unbooked = 'bi-heart'
    icons = [bookmarked,unbooked]
    savedjobid_index = []
    userid = session.get('userid')

    cursor = mysql.connect().cursor()
    cursor.execute('SELECT * FROM alumnijobs aj INNER JOIN employeraccount ea ON aj.companyid = ea.companyid WHERE aj.jobid = %s AND aj.jobstatus = %s', [id,1])
    result = cursor.fetchall()

    catlist = list(categorylist())
    num_per_job = [categoryjobcount(num[0]) for num in catlist]

    loclist = list(locationlist())
    num_per_loc_job = [locationjobcount(num) for num in loclist]

    topratedjobslist = topratedjobs()

    bookmarkedjobs = returnsavedjobs()
    savedjobid_index = [i[0] for i in bookmarkedjobs]

    applied = returnappliedjobs(userid)

    return render_template('/userpage/userjobsingle.html', catlist = catlist, loclist = loclist, result = result, numjob = num_per_job, locnumjob = num_per_loc_job, ratedjob = topratedjobslist, userid = userid, icons = icons, saved = savedjobid_index, appliedposts = applied)
        
#Route for company details page/company profile information
@app.route('/user-company-profile/<id>')
def usercompanyprofile(id):

    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    if 'loggedin' not in session:
        return redirect(url_for('index'))
    else:
        pass
    
    userid = session.get('userid')
    savedjobid_index = []

    cursor = mysql.connect().cursor()
    cursor.execute('SELECT * FROM employeraccount WHERE companyid = %s AND accountstatus = %s', (id,1))
    result = cursor.fetchall()
    cursor.connection.commit()

    cursor.execute('SELECT aj.jobid, aj.jobtitle, ea.companyname, aj.category, aj.jobdescription, aj.jobtype, aj.joblocation, aj.minsal, aj.maxsal, aj.companyid, ea.profileimage FROM alumnijobs aj INNER JOIN employeraccount ea ON aj.companyid = ea.companyid WHERE aj.companyid = %s AND aj.jobstatus = %s', (id,1))
    compjobs = cursor.fetchall()

    bookmarkedjobs = returnsavedjobs()

    try:
        savedjobid_index = [i[0] for i in bookmarkedjobs]
    except:
        savedjobid_index = []

    applied = returnappliedjobs(userid)

    userprofile = userreviewsection(id)

    totalreview = totalreviews(id)

    name = getalumniname()

    return render_template('userpage/usercompany-profile.html', result = result, compjobs = compjobs, userid = userid, saved = savedjobid_index, appliedposts = applied, profile = userprofile, companyid = id, alumniid = userid, reviews = totalreview, name = name)


#---------------------------------------------------------BOOKMARKING SECTION---------------------------------------------
#------------------------------------------------------------------------------------------------------------------------

@app.route('/bookmark',methods=['POST','GET'])
def to_bookmark():

    try:
        data = request.form.get('data')
        data2 = request.form.get('data2')
        userid = session['userid']

        saved_jobs = []
            
        cursor = mysql.connect().cursor()
        cursor.execute('SELECT jobid FROM alumnisavedjobs WHERE alumniid = %s AND savedjobstatus = %s',(str(userid),1))
        result = cursor.fetchall()

        saved_jobs = [i[0] for i in result]

        if int(data) in saved_jobs:
            cursor.execute('UPDATE alumnisavedjobs SET saved = %s WHERE alumniid = %s AND jobid = %s',(1,data2,data))
            cursor.connection.commit()
            cursor.close()
        else:
            cursor.execute('INSERT INTO alumnisavedjobs(alumniid,jobid,saved) VALUES (%s,%s,%s)',(data2,data,1))
            cursor.connection.commit()
            cursor.close()

    except:
        print('Error in bookmarking')
    return data

@app.route('/unbookmark',methods=['POST'])
def to_not_bookmark():

    try:
        data = request.form.get('data')
        data2 = request.form.get('data2')
        
        cursor = mysql.connect().cursor()
        cursor.execute('UPDATE alumnisavedjobs SET saved = 0 WHERE alumniid = %s AND jobid = %s',(data2,data))
        cursor.connection.commit()
        cursor.close()
    except:
        print('Error in unbookmarking')

    return data

#----------------------------------------------------END OF BOOKMARKING SECTION---------------------------------------------
#------------------------------------------------------------------------------------------------------------------------


#Route for resume data processing for insertion in the database and file directory
@app.route('/applicationprocessing', methods=['POST','GET'])
def applicationprocessing():
    
    cursor = mysql.connect().cursor()
    jobid = request.args.get('jobid')
    companyid = request.args.get('compid')
    converted_filename = ''

    if request.method == 'POST':
        email = request.form['email']
        select = request.form.get('history')
        skills = request.form['skills']
        fname = request.form['fname']
        lname = request.form['lname']
        phone = request.form['phone']
        address = request.form['address']
        dateapplied = time.strftime("%Y-%m-%d")

        # check if the post request has the file part
        if 'resume' not in request.files:
            flash('No file part')
            return redirect(url_for('userjobdetails', id = jobid))
        file = request.files['resume']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(url_for('userjobdetails', id = jobid))
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            converted_filename = filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cursor.execute('INSERT INTO alumniapplication(Email,Career_history,Skills,First_name,Last_name,Contact_no,Address,resumename,alumniid,jobid,companyid,dateapplied) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(email,select,skills,fname,lname,phone,address,converted_filename,str(session['userid']),jobid,companyid,dateapplied))
        cursor.connection.commit()

        return redirect(url_for('usersuccess', id = jobid))

@app.route('/profilepicupdate',methods=['POST'])
def profilepicupdate():

    if request.method == "POST":
        cursor = mysql.connect().cursor()
        userid = session.get('userid')

        # check if the post request has the file part
        if 'profilepic' not in request.files:
            flash('No file part')
            return redirect(url_for('user_homepage', page=4))
        image = request.files['profilepic']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if image.filename == '':
            flash('No selected file')
            return redirect(url_for('user_homepage', page=4))
        if image and allowed_image(image.filename):
            imagefile = secure_filename(image.filename)
            userprofilefolder = "/userprofilepic"
            employerprofilefolder = "/employerprofilepic"
            userprofiledirectory = app.config['PROFILEIMAGE_FOLDER'] + userprofilefolder
            employerprofiledirectory = app.config['PROFILEIMAGE_FOLDER'] + employerprofilefolder

            if user_in_session():
                image.save(os.path.join(userprofiledirectory, imagefile))

                cursor.execute('UPDATE alumniapplicants SET profileimage = %s WHERE alumniid = %s',(imagefile,str(userid)))
                cursor.connection.commit()
                flash('Profile image updated!')

                return redirect(url_for('user_homepage', page = 4))

            if employer_in_session():
                image.save(os.path.join(employerprofiledirectory, imagefile))

                cursor.execute('UPDATE employeraccount SET profileimage = %s WHERE companyid = %s',(imagefile,str(userid)))
                cursor.connection.commit()
                flash('Profile image updated!')

                return redirect(url_for('employerpages', pages = 'profile'))
        
    return ''

#User success after resume submission
@app.route('/usersuccess/<int:id>', methods=['POST','GET'])
def usersuccess(id):

    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    if 'loggedin' not in session:
        return redirect(url_for('index'))
    else:
        pass
    
    return render_template('/userpage/successpage.html', id = id)

#Route for downloading files for the employers
@app.route('/downloadresume/<path:filename>',methods=['GET','POST'])
def downloadresume(filename):

    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment = True)
    except:
        print('error')
        return ''
    
@app.route('/applicationapproval',methods=['POST','GET'])
def applicationapproval():

    if request.method == 'POST':

        cursor = mysql.connect().cursor()

        alumniid = request.args.get('alumniid')
        message = request.form.get('applicantapprovemessage')
        companyid = session.get('userid')
        username = request.args.get('uname')

        remark = 'Approved'
        applicationid = request.args.get('applicationid')
        approveddate = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('INSERT INTO messages(alumniid,companyid,username,message) VALUES(%s,%s,%s,%s)',(alumniid,companyid,username,message))
        cursor.execute('UPDATE alumniapplication SET remark = %s, approveddate = %s WHERE application_ID = %s',(remark,approveddate,applicationid))
        cursor.connection.commit()
        cursor.close()

        flash('application approved!')
        return redirect(url_for('employerpages', pages = 'manageapplicants'))

    return redirect(url_for('employerpages', pages = 'manageapplicants'))

@app.route('/applicationreject',methods=['POST','GET'])
def applicationreject():

    if request.method == 'POST':
        cursor = mysql.connect().cursor()
        companyid = session.get('userid')

        applicationid = request.args.get('applicationid')
        alumniid = request.args.get('alumniid')
        uname = request.args.get('uname')
        message = request.form['applicantrejectmessage']
        remark = 'Rejected'

        cursor.execute('UPDATE alumniapplication SET remark = %s WHERE application_ID = %s',(remark,applicationid))
        cursor.execute('INSERT INTO messages(alumniid,companyid,username,message) VALUES(%s,%s,%s,%s)',(alumniid,companyid,uname,message))
        cursor.connection.commit()
        cursor.close()

        flash('Application rejected.')

        return redirect(url_for('employerpages', pages = 'manageapplicants'))

    return redirect(url_for('employerpages', pages = 'manageapplicants'))

@app.route('/applicationdelete',methods=['POST','GET'])
def applicationdelete():

    if request.method == 'POST':
        cursor = mysql.connect().cursor()
        applicationid = request.args.get('applicationid')

        cursor.execute('DELETE FROM alumniapplication WHERE application_ID = %s',(applicationid,))
        cursor.connection.commit()
        cursor.close()

        flash('Application deleted.')
        return redirect(url_for('employerpages', pages = 'manageapplicants'))

@app.route('/reviewprocessing',methods=['POST','GET'])
def reviewprocessing():

    companyid =  request.args.get('companyid')

    if request.method == 'POST':

        cursor = mysql.connect().cursor()

        comment = request.form['comment']
        alumniid = request.args.get('alumniid')

        cursor.execute('INSERT INTO reviews(alumniid,companyid,comment) VALUES(%s,%s,%s)',(alumniid,companyid,comment))
        cursor.connection.commit()
        cursor.close()

        return redirect(url_for('usercompanyprofile', id = companyid))

    return redirect(url_for('usercompanyprofile', id = companyid))

@app.route('/editreview', methods=['POST','GET'])
def editreview():
    if request.method == 'POST':
        reviewID = request.args.get('reviewid')
        comment = request.form['editcomment']
        companyid = request.args.get('companyid')

        cursor = mysql.connect().cursor()
        cursor.execute('UPDATE reviews SET comment = %s WHERE review_ID = %s',(comment,reviewID))
        cursor.connection.commit()
        cursor.close()

    return redirect(url_for('usercompanyprofile',id = companyid))

@app.route('/deletereview')
def deletereview():

    reviewID = request.args.get('reviewid')
    companyid = request.args.get('companyid')

    cursor = mysql.connect().cursor()
    cursor.execute('DELETE FROM reviews WHERE review_ID = %s',(reviewID,))
    cursor.connection.commit()
    cursor.close()

    return redirect(url_for('usercompanyprofile', id = companyid))

#================================================================================================================================
#----------------------------------------------- END OF ALUMNI USER PAGES -------------------------------------------------------
#================================================================================================================================

# EMPLOYER CONTROL PART
@app.route('/employerlogin', methods=['GET','POST'])
def employerpage():

    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if admin_in_session():
        return redirect(url_for('admindb'))
    else:
        pass

    cursor = mysql.connect().cursor()
    error = None 
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        queryvalidation = cursor.execute('SELECT * FROM employeraccount WHERE emailaddress = %s',(email,))
        validresult = cursor.fetchone()
        
        if not queryvalidation:
            error = 'Your email or password is incorrect...'
            return render_template('/recruiterpage/employerlogin.html', error = error)
        if int(validresult[11]) == 0:
            error = 'Invalid account...'
            return render_template('/recruiterpage/employerlogin.html', error = error)
        if queryvalidation and sha256_crypt.verify(password,validresult[3]):
            session['loggedin'] = True
            session['userid'] = validresult[0]
            session['email'] = validresult[1]
            return redirect(url_for('employerpages',pages = 'dashboard'))
        else:
            error = 'Your email or password is incorrect...'
            render_template('/recruiterpage/employerlogin.html', error = error)
            
    return render_template('/recruiterpage/employerlogin.html', error = error)


@app.route('/employerpage/<pages>',methods=['POST','GET'])
def employerpages(pages):

    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if admin_in_session():
        return redirect(url_for('admindb'))
    if 'loggedin' not in session:
        return redirect(url_for('index'))
    else:
        pass

    userid = session.get('userid')
    cursor = mysql.connect().cursor()
    cursor.execute('SELECT * FROM alumnijobs WHERE companyid = %s AND jobstatus = %s',(str(userid),1))
    employerresult = cursor.fetchall()

    if pages == 'dashboard':
        totaljob = len(employerresult)
        jobpostedtoday = jobpostedthismonth = jobpostedthisyear = 0
        totaljobposted = len(employerresult)
        alljobid = []

        jobdates = [str(i[9]).split('-') for i in employerresult]
        timenow = time.strftime('%Y-%m-%d').split('-')

        jobpostedtoday = sum(1 for date in jobdates if int(date[2]) == int(timenow[2]))
        jobpostedthismonth = sum(1 for date in jobdates if int(date[1]) == int(timenow[1]))
        jobpostedthisyear = sum(1 for date in jobdates if int(date[0]) == int(timenow[0]))

        jobposteddates = [jobpostedtoday, jobpostedthismonth, jobpostedthisyear, totaljobposted]

        cursor.execute('SELECT * FROM alumniapplication aa INNER JOIN alumnijobs aj ON aa.jobid = aj.jobid WHERE aj.companyid = %s AND aj.jobstatus = %s AND aa.applicationstatus = %s',(str(userid),1,1))
        applicants = cursor.fetchall()
        counted = len(applicants)

        cursor.execute('SELECT jobid, COUNT(alumniid) AS num_applicants FROM alumniapplication WHERE companyid = %s AND applicationstatus = %s GROUP BY jobid',(str(userid),1))
        applicantsperjob = cursor.fetchall()
        alljobid = [i[0] for i in applicantsperjob]

        result = getEmployer()
        notif = employernotification()

        statuses = [i[14] for i in applicants]
        applicationremarks = [statuses.count('Approved'), statuses.count('Rejected'), statuses.count('Waiting')]

        return render_template('/recruiterpage/employerdashboard.html', job = employerresult, totaljob = totaljob, applicants = counted, totalapplicants = applicantsperjob, compname = result, alljobid = alljobid, notif = notif, statdays = jobposteddates, remarks = applicationremarks)
    elif pages == 'postjob':

        result = getEmployer()
        job_to_edit = ()
        jobid = request.args.get('jobid')

        try:
            jobid = request.args.get('jobid')

            cursor.execute('SELECT * FROM alumnijobs WHERE companyid = %s AND jobid = %s AND jobstatus = %s',(str(userid),jobid,1))
            job_to_edit = cursor.fetchall()
        except:
            print('error in getting job to edit')

        catlist = list(categorylist())
        categories = [x[0] for x in catlist]

        notif = employernotification()

        return render_template('/recruiterpage/employerpostjob.html',compname = result, jobtoedit = job_to_edit, notif = notif, categories = categories)
    elif pages == 'managejobs':
        alljobid = []
        jobsearch = ()

        result = getEmployer()

        cursor.execute('SELECT jobid, COUNT(alumniid) AS num_applicants FROM alumniapplication WHERE companyid = %s AND applicationstatus = %s GROUP BY jobid',(str(userid),1))
        applicantsperjob = cursor.fetchall()
        alljobid = [i[0] for i in applicantsperjob]

        if request.method == 'POST':
            jobsearch = get_employer_job_search_function()
            if jobsearch == None or jobsearch == ():
                flash('Nothing matched up your search... try again.')

        notif = employernotification()

        return render_template('/recruiterpage/employerjobs.html', result = employerresult, totalapplicants = applicantsperjob,compname = result, alljobid = alljobid, jobsearch = jobsearch, notif = notif)
    elif pages == 'manageapplicants':

        companyid = session.get('userid')

        cursor.execute('SELECT companyname FROM employeraccount WHERE companyid = %s',(companyid,))
        companyname = cursor.fetchone()[0]

        jobid_from_applicants_per_job = ""
        jobtitle_from_applicants_per_job = ""
        applicants_by_job = ""
        notif_ID = 0
        notif_applicationID = 0
        application_from_notif = ()

        try:
            jobid_from_applicants_per_job = request.args.get('jobid')
            jobtitle_from_applicants_per_job = request.args.get('jobtitle')
        except:
            pass

        if jobid_from_applicants_per_job == None or jobid_from_applicants_per_job == "":
            pass
        else:
            applicants_by_job = get_applicants_from_jobid(jobid_from_applicants_per_job,jobtitle_from_applicants_per_job)

        applicants = getApplicants()
        categories = categorylist()
        location = locationlist()

        result = getEmployer() #Display the name of the employer/company

        notif = employernotification()

        try:
            notif_ID = request.args.get('alumniid')
            notif_applicationID = request.args.get('appID')
        except:
            pass
        if notif_ID == 0:
            application_from_notif = ()
        else:
            application_from_notif1 = [i for i in applicants if i[2] == notif_ID and int(i[9]) == int(notif_applicationID)]

        if request.method == 'POST':
            locationinput = request.form['locationinput']
            categoryinput = request.form['categoryinput']
            searchword = request.form['searchword']

            filtereddata = filter_applicants(locationinput,categoryinput,searchword,applicants)
            applicants = filtereddata

        return render_template('/recruiterpage/employerapplicants.html',compname = result, applicants = applicants, applicantsbyjob = applicants_by_job, company = companyname, notif = notif, notifapplicant = application_from_notif, categories = categories, location = location)
    elif pages == 'notification':
        
        employer = getEmployer() #Display the name of the employer/company
        
        info = employernotification()

        return render_template('/recruiterpage/employernotification.html', result = info, employer = employer)
    elif pages == 'messages':
        companyid = session.get('userid')
        employer = getEmployer() #Display the name of the employer/company

        cursor.execute('SELECT companyname FROM employeraccount WHERE companyid = %s',(companyid,))
        company = cursor.fetchone()[0]

        id = allmsg = data = ''

        cursor.execute('SELECT aa.alumniid, up.fullname, aa.profileimage FROM alumniapplicants aa INNER JOIN userprofile up ON aa.alumniid = up.alumniid INNER JOIN alumniapplication aap ON aa.alumniid = aap.alumniid WHERE aap.companyid = %s AND aap.applicationstatus = %s GROUP BY aa.alumniid',(companyid,1))
        result = cursor.fetchall()

        try:
            id = request.args.get('id')
        except:
            pass

        if id == None or id == '':
            pass
        else:
            cursor.execute('SELECT m.message, m.username FROM messages m INNER JOIN alumniapplicants aa ON m.alumniid = aa.alumniid WHERE m.alumniid = %s AND m.companyid = %s AND aa.accountstatus = %s',(id,companyid,1))
            allmsg = cursor.fetchall()
            cursor.execute('SELECT up.fullname, aa.profileimage, aa.alumniid FROM alumniapplicants aa INNER JOIN userprofile up ON aa.alumniid = up.alumniid WHERE aa.alumniid = %s AND accountstatus = %s',(id,1))
            data = cursor.fetchall()

        notif = employernotification()
        
        return render_template('/recruiterpage/employermessages.html', result = result, msg = allmsg, id = id, data = data, company = company, employer = employer, notif = notif)
    elif pages == 'profile':

        result = getEmployer()

        notif = employernotification()

        return render_template('/recruiterpage/employerprofile.html',compname = result, notif = notif)
    elif pages == 'logout':

        return redirect(url_for('logout'))
    
    else:

        return abort(404)

@app.route('/viewprofile')
def employerviewalumniprofile():

    alumniid = request.args.get('alumniid')

    cursor = mysql.connect().cursor()
    cursor.execute('SELECT * FROM alumniapplicants LEFT JOIN userprofile ON alumniapplicants.alumniid = userprofile.alumniid WHERE alumniapplicants.alumniid = %s',(alumniid,))
    result = cursor.fetchall()

    return render_template('recruiterpage/employeralumniprofile.html', alumnidata = result)


@app.route('/employerprofilesettings',methods=['POST','GET'])
def employerprofilesettings():

    companyid = session.get('userid')
    cursor = mysql.connect().cursor()

    if request.method == 'POST':

        website = request.form['website']
        industry = request.form['industry']
        size = request.form.get('size')
        location = request.form['comploc']
        about = request.form.get('about')
        specialties = request.form['specialties']

        query = "UPDATE employeraccount SET industry = %s, size = %s, location = %s, about = %s, website = %s, specialties = %s WHERE companyid = %s"
        cursor.execute(query,(industry,size,location,about,website,specialties,companyid))
        cursor.connection.commit()

        flash('Company profile updated! ')
        return redirect(url_for('employerpages', pages = 'profile'))

    return redirect(url_for('employerpages', pages = 'profile'))

@app.route('/postjob', methods=['POST'])
def postjobprocess():

    jobprocess = request.args.get('jobprocess')
    jobid =  request.args.get('jobid')
    companyid = session.get('userid')
    if request.method == 'POST':
        cursor = mysql.connect().cursor()

        jobtitle = request.form['jobtitle']
        jobdescription = request.form.get('jobdescription')
        jobcategory = request.form.get('jobcategory')
        jobtype = request.form.get('jobtype')
        joblevel = request.form.get('joblevel')
        experience = request.form.get('experience')
        minsalary = request.form['minsalary']
        maxsalary = request.form['maxsalary']
        expireddate = request.form['expireddate']
        location = request.form['location']
        skills = request.form['skills']
        datepost = time.strftime("%Y-%m-%d")

        if jobprocess == 'insert':

            query = 'INSERT INTO alumnijobs(companyid,category,jobtitle,minsal,maxsal,deadline,qualification,jobdescription,dateposted,jobtype,joblevel,joblocation,skills) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
            cursor.execute(query, (str(companyid),jobcategory,jobtitle,minsalary,maxsalary,expireddate,experience,jobdescription,datepost,jobtype,joblevel,location,skills))
            cursor.connection.commit()

            flash('Job Posted!')

            return redirect(url_for('employerpages',pages='dashboard'))

        elif jobprocess == 'edit':
            query = "UPDATE alumnijobs SET category = %s, jobtitle = %s, minsal = %s, maxsal = %s, deadline = %s, qualification = %s, jobdescription = %s, dateposted = %s, jobtype = %s, joblevel = %s, joblocation = %s, skills = %s WHERE jobid = %s"
            cursor.execute(query,(jobcategory,jobtitle,minsalary,maxsalary,expireddate,experience,jobdescription,datepost,jobtype,joblevel,location,skills,jobid))
            cursor.connection.commit()

            flash('Job updated!')

            return redirect(url_for('employerpages',pages='dashboard'))

    return redirect(url_for('employerpages',pages='postjob'))

@app.route('/employerdeletejob',methods=['POST','GET'])
def employerdeletejob():

    if request.method == 'POST':

        cursor = mysql.connect().cursor()

        jobid = request.args.get('jobid')

        cursor.execute('DELETE FROM alumnijobs WHERE jobid = %s',(jobid,))

        try:
            cursor.execute('DELETE FROM alumnisavedjobs WHERE jobid = %s',(jobid,))
        except:
            pass
        try:
            cursor.execute('DELETE FROM alumniapplication WHERE jobid = %s',(jobid,))
        except:
            pass

        cursor.connection.commit()
        cursor.close()

        flash('Job removed.')
        return redirect(url_for('employerpages', pages = 'managejobs'))

#=====================================================================================================================
#===============================================ADMIN ROUTE PART======================================================
#=====================================================================================================================

@app.route('/adminlogin')
def adminlogin():

    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if admin_in_session():
        return redirect(url_for('admindb'))
    else:
        pass

    return render_template('/adminpage/adminlogin.html')

@app.route('/adminloginprocess',methods=['POST'])
def adminloginprocess():

    if request.method == "POST":

        cursor = mysql.connect().cursor()

        user = request.form['user']
        password = request.form['password']

        validation = cursor.execute('SELECT * FROM adminaccount WHERE email = %s OR username = %s',(user,user))
        result = cursor.fetchone()

        if validation:
            if (user == result[1] or user == result[3])  and sha256_crypt.verify(password,result[2]):
                session['loggedin'] = True
                session['userid'] = result[0]
                session['email'] = result[1]

                return redirect(url_for('admindb'))
        else:
            flash('Incorrect email or password...')
            return redirect(url_for('adminlogin'))
        
    return redirect(url_for('adminlogin'))

@app.route('/admindashboard', methods=['POST','GET'])
def admindb():

    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if 'loggedin' not in session:
        return redirect(url_for('index'))
    else:
        pass

    email = session.get('email')
    adminid = session.get('userid')
    jobstoday = jobsmonth = jobsyear = 0

    cursor = mysql.connect().cursor()

    cursor.execute('SELECT * FROM adminaccount WHERE email = %s AND adminid = %s',(email,adminid))
    result = cursor.fetchone()

    message = request.args.get('message')
    color = request.args.get('color')

    cursor.execute('SELECT COUNT(application_ID) FROM alumniapplication WHERE applicationstatus = %s',(1,))
    applicants = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(companyid) FROM employeraccount WHERE accountstatus = %s',(1,))
    employers = cursor.fetchone()[0]

    jobs = list(catjobs())

    jobdates = [str(i[9]).split('-') for i in jobs]
    current_date = time.strftime('%Y-%m-%d').split('-')

    jobstoday = sum(1 for date in jobdates if int(date[2]) == int(current_date[2]))
    jobsmonth = sum(1 for date in jobdates if int(date[1]) == int(current_date[1]))
    jobsyear = sum(1 for date in jobdates if int(date[0]) == int(current_date[0]))

    countedjobs = [jobstoday, jobsmonth, jobsyear, len(jobs)]

    totalcategories = len(list(categorylist()))

    cursor.execute('SELECT aa.alumniid, up.fullname, aa.emailaddress, aa.accountcreated, aa.accountstatus, aa.validity FROM alumniapplicants aa INNER JOIN userprofile up ON aa.alumniid = up.alumniid ORDER BY aa.accountcreated DESC')
    applicantdashboard =  cursor.fetchall()

    statuses = [i[5] for i in applicantdashboard]
    accountvalidation = [statuses.count('Registered'), statuses.count('Pending'), statuses.count('Unregistered')]

    cursor.execute('SELECT COUNT(alumniid) FROM alumniapplicants')
    totalapplicants = cursor.fetchone()[0]
    
    return render_template('/adminpage/adb_index.html', result = result, message = message, color = color, applicants = applicants, numjobs = countedjobs, employer = employers, totalcat = totalcategories, alumnidata = applicantdashboard[0:5], total = totalapplicants, accvalid = accountvalidation)

@app.route('/admindashboard/<pages>')
def admindbpages(pages):

    if user_in_session():
        return redirect(url_for('user_homepage', page = 0))
    if employer_in_session():
        return redirect(url_for('employerpages', pages = 'dashboard'))
    if 'loggedin' not in session:
        return redirect(url_for('index'))
    else:
        pass

    cursor = mysql.connect().cursor()
    email = session.get('email')
    adminid = session.get('userid')

    cursor.execute('SELECT * FROM adminaccount WHERE email = %s AND adminid = %s',(email,adminid))
    admindata = cursor.fetchone()

    if pages == 'usersprofile':
        adminid = session.get('userid')

        cursor.execute('SELECT * FROM adminaccount')
        result = cursor.fetchall()

        return render_template('/adminpage/users-profile.html', result = result, admin = admindata, adminid = adminid)
    elif pages == 'company':

        cursor.execute('SELECT * FROM employeraccount WHERE accountstatus = %s',(1,))
        result = cursor.fetchall()

        return render_template('/adminpage/company.html', result = result, admin = admindata)
    elif pages == 'location':

        result = list(locationlist())

        return render_template('/adminpage/joblocation.html', result = result, admin = admindata)
    elif pages == 'applicant':

        adminid = session.get('userid')
        data = []
        titlesdata = []
        companyname = []
        applieddate = []
        alumniid = []
        totalapplicantsdata = []
        applicationID = []
        remarks = []
        allapplicants = []
        
        cursor.execute('SELECT aa.alumniid, aa.companyid, aa.jobid, aa.dateapplied, aa.application_ID, aa.remark, up.fullname FROM alumniapplication aa INNER JOIN userprofile up ON aa.alumniid = up.alumniid WHERE applicationstatus = %s',(1,))
        result = cursor.fetchall()
        
        cursor.execute('SELECT alumniid, fullname FROM userprofile')
        profile = cursor.fetchall()
        
        cursor.execute('SELECT aj.jobid, aj.jobtitle, ea.companyname FROM alumnijobs aj INNER JOIN employeraccount ea ON aj.companyid = ea.companyid WHERE aj.jobstatus = %s',(1,))
        titles = cursor.fetchall()

        cursor.execute('SELECT aa.jobid, aj.jobtitle, ea.companyname FROM alumniapplication aa INNER JOIN alumnijobs aj ON aa.jobid = aj.jobid INNER JOIN employeraccount ea ON aa.companyid = ea.companyid WHERE aj.jobstatus = %s',(1,))
        data1 = cursor.fetchall()

        count = 0
        for i in result:
            x = list(i) + list(data1[count])
            allapplicants.append(x)
            count = count + 1

        if result:
            for i in result:
                applieddate.append(i[3])
                alumniid.append(i[0])
                applicationID.append(i[4])
                remarks.append(i[5])
                for j in profile:
                    if j[0] == i[0]:
                        data.append(j[1])
        if result:
            for i in result:
                for j in titles:
                    if j[0] == i[2]:
                        titlesdata.append(j[1])
                        companyname.append(j[2])

        try:
            totalapplicantsdata = list(zip(alumniid,data,titlesdata,companyname,applieddate,applicationID,remarks))
        except:
            pass        

        return render_template('/adminpage/applicant.html', total = totalapplicantsdata, admin = admindata, adminid = adminid, all = allapplicants)
    elif pages == 'category':

        error = ''

        try:
            error = request.args.get('error')
        except:
            pass

        result = list(categorylist())

        return render_template('/adminpage/category.html', result = result, admin = admindata, error = error)
    elif pages == 'manageuser':

        adminid = session.get('userid')
        allarchived = []

        cursor.execute('SELECT * FROM adminaccount WHERE accountstatus = %s',(1,))
        result = cursor.fetchall()

        cursor.execute('SELECT up.alumniid, up.fullname, aa.emailaddress, up.fname, up.lname, aa.validity, aa.accountstatus FROM userprofile up INNER JOIN alumniapplicants aa ON aa.alumniid = up.alumniid WHERE aa.accountstatus = %s',(1,))
        applicants = cursor.fetchall()

        cursor.execute('SELECT * FROM employeraccount WHERE accountstatus = %s',(1,))
        employer = cursor.fetchall()

        cursor.execute('SELECT * FROM employeraccount WHERE accountstatus = %s',(0,))
        archivedemployer = cursor.fetchall()

        cursor.execute('SELECT aa.alumniid, aa.emailaddress, up.fullname FROM alumniapplicants aa INNER JOIN userprofile up ON aa.alumniid = up.alumniid WHERE aa.accountstatus = %s',(0,))
        archivedapplicants = cursor.fetchall()
        
        allarchived = archivedemployer + archivedapplicants

        return render_template('/adminpage/manage-user.html', result = result, applicants = applicants, employer = employer, archived = allarchived, admin = admindata, adminid = adminid)
    
    else:
        return abort(404)

@app.route('/adminprofileedit', methods = ['POST'])
def adminprofileedit():

    if request.method == 'POST':
        cursor = mysql.connect().cursor()
        email = session.get('email')
        adminid = session.get('userid')

        username = request.form['username']
        current = request.form['password']
        new = request.form['newpassword']
        retype_new = request.form['renewpassword']

        cursor.execute('SELECT * FROM adminaccount WHERE email = %s AND adminid = %s',(email,adminid))
        result = cursor.fetchone()

        correctpass = sha256_crypt.verify(current,result[2])

        if (new == '' or new == None) and (retype_new == '' or retype_new == None) and correctpass:
            cursor.execute('UPDATE adminaccount SET username = %s WHERE adminid = %s',(username,adminid))
            cursor.connection.commit()
            cursor.close()

            flash('Profile edited!')
            return redirect(url_for('admindbpages', pages = 'usersprofile', message = 'Done!', color = 'success'))

        if correctpass and (new == retype_new):
            hash_new = sha256_crypt.encrypt(new)
            cursor.execute('UPDATE adminaccount SET username = %s, password = %s WHERE adminid = %s',(username,hash_new,adminid))
            cursor.connection.commit()
            cursor.close()

            flash('Profile edited!')
            return redirect(url_for('admindbpages', pages = 'usersprofile', message = 'Done!', color = 'success'))

        else:
            flash('Something went wrong. Please check your input information again if it is correct.')
            return redirect(url_for('admindbpages', pages = 'usersprofile'))

    return redirect(url_for('admindbpages', pages = 'usersprofile'))

@app.route('/adminaddcompany', methods=['POST'])
def addcompany():
    if request.method == 'POST':

        cursor = mysql.connect().cursor()

        companyname = request.form['companyname']
        address = request.form['address']
        email = request.form['email']
        password = request.form['password']
        accountcreated = time.strftime('%Y-%m-%d')

        hash_pass = sha256_crypt.encrypt(password)

        cursor.execute('INSERT INTO employeraccount(companyname,location,emailaddress,password,accountcreated) VALUES (%s,%s,%s,%s,%s)',(companyname,address,email,hash_pass,accountcreated))
        cursor.connection.commit()
        cursor.close()
        
        flash('Company added!')
        return redirect(url_for('admindbpages', pages = 'company'))

    return redirect(url_for('admindbpages', pages = 'company'))

@app.route('/admineditcompany', methods=['POST'])
def editcompany():

    if request.method == 'POST':

        cursor = mysql.connect().cursor()
        hash_pass = ''

        companyname = request.form['editcompanyname']
        address = request.form['editaddress']
        email = request.form['editemail']
        password = request.form['editpassword']
        companyid = request.args.get('compid')

        cursor.execute('SELECT password FROM employeraccount WHERE companyid = %s',(companyid,))
        result = cursor.fetchone()[0]

        if password:
            hash_pass = sha256_crypt.encrypt(password)
        else:
            hash_pass = result

        cursor.execute('UPDATE employeraccount SET companyname = %s, location = %s, emailaddress = %s, password = %s WHERE companyid = %s',(companyname,address,email,hash_pass,companyid))
        cursor.connection.commit()
        cursor.close()

        flash('Company info edited!')
        return redirect(url_for('admindbpages', pages = 'company'))

    return redirect(url_for('admindbpages', pages = 'company'))


@app.route('/addlocation', methods = ['POST','GET'])
def adminaddlocation():
    if request.method == 'POST':

        cursor = mysql.connect().cursor()

        location = request.form['location']
        cursor.execute('INSERT INTO joblocation(location) VALUES(%s)',(location,))
        cursor.connection.commit()
        cursor.close()

        flash('Location added!')
        return redirect(url_for('admindbpages', pages = 'location'))

    return redirect(url_for('admindbpages', pages = 'location'))

@app.route('/modifylocation', methods=['POST','GET'])
def modifylocation():
    if request.method == 'POST':

        cursor = mysql.connect().cursor()

        locationid = request.args.get('locid')
        action = request.args.get('action')

        if action == 'edit':
            location = request.form['editlocation']
            cursor.execute('UPDATE joblocation SET location = %s WHERE locationid = %s',(location,locationid))
            cursor.connection.commit()
            cursor.close()
            flash('Location edited')
        elif action == 'delete':
            cursor.execute('DELETE FROM joblocation WHERE locationid = %s',(locationid,))
            cursor.connection.commit()
            cursor.close()
            flash('Location deleted')
        else:
            pass
        return redirect(url_for('admindbpages', pages = 'location'))

    return redirect(url_for('admindbpages', pages = 'location'))

@app.route('/modifyapplication', methods = ['POST','GET'])
def modifyapplication():

    if request.method == 'POST':

        cursor = mysql.connect().cursor()

        application_ID = request.args.get('appid')
        cursor.execute('DELETE FROM alumniapplication WHERE application_ID = %s',(application_ID,))
        cursor.connection.commit()
        cursor.close()

        flash('Application form deleted.')
        return redirect(url_for('admindbpages', pages = 'applicant'))

    return redirect(url_for('admindbpages', pages = 'applicant'))

@app.route('/adminmodifycategory', methods=['POST','GET'])
def adminmodifycategory():

    cursor = mysql.connect().cursor()

    if request.method == 'POST':

        action = request.args.get('action')

        if action == 'add':

            category = request.form['category']
            cursor.execute('INSERT INTO tblcategory(category) VALUES(%s)',(category,))
            cursor.connection.commit()
            cursor.close()

            flash('Category inserted.')
            return redirect(url_for('admindbpages', pages = 'category'))
        
        if action == 'edit':

            category = request.form['editcategory']
            categoryid = request.args.get('catid')

            cursor.execute('SELECT imagename FROM tblcategory WHERE categoryid = %s',(categoryid,))
            categoryname = cursor.fetchall()

            # check if the post request has the file part
            if 'categorypic' not in request.files:
                flash('No file part')
                return redirect(url_for('admindbpages', pages ='category'))
            image = request.files['categorypic']
            # If the user does not select a file, the browser submits an
            # empty file without a filename.
            if image.filename == '':
                flash('No selected file')
                return redirect(url_for('admindbpages', pages = 'category'))
            if image and allowed_image(image.filename):
                imagefile = secure_filename(image.filename)
                app.config['categoryprofile'] = "static/assets/img/categories-landingpage"

                if imagefile == categoryname[0][0]:
                    pass
                else:
                    image.save(os.path.join(app.config['categoryprofile'], imagefile))

                cursor.execute('UPDATE tblcategory SET category = %s, imagename = %s WHERE categoryid = %s',(category,imagefile,categoryid))
                cursor.connection.commit()
                cursor.close()

            flash('Category edited.')
            return redirect(url_for('admindbpages', pages = 'category'))

        if action == 'delete':

            categoryid = request.args.get('catid')

            cursor.execute('DELETE FROM tblcategory WHERE categoryid = %s',(categoryid,))
            cursor.connection.commit()
            cursor.close()

            flash('Category deleted.')
            return redirect(url_for('admindbpages', pages = 'category'))
        else:

            flash('Something went wrong.')
            return redirect(url_for('admindbpages', pages = 'category', error = 'Error'))

    return redirect(url_for('admindbpages', pages = 'category'))


@app.route('/adminmodifyaccount',methods=['POST','GET'])
def adminmodifyaccount():
    if request.method == 'POST':

        cursor = mysql.connect().cursor()

        action = request.args.get('action')

        if action == 'add':
            email = request.form['addadminemail']
            username = request.form['addadminuname']
            password = request.form['addadminpw']
            role = request.form.get('addadminrole')
            adminid = session.get('userid')

            hash_pass = sha256_crypt.encrypt(password)

            cursor.execute('INSERT INTO adminaccount(email,username,password,role) VALUES(%s,%s,%s,%s)',(email,username,hash_pass,role))
            cursor.connection.commit()
            cursor.close()

            flash('New admin has been added.')
            return redirect(url_for('admindbpages', pages = 'manageuser'))
        if action == 'edit':

            email = request.form['editadminemail']
            username = request.form['editadminuname']
            password = request.form['editadminpw']
            role = request.form.get('editadminrole')
            adminid = request.args.get('adminid')
            hash_pass = ''

            cursor.execute('SELECT * FROM adminaccount WHERE adminid = %s',(adminid,))
            result = cursor.fetchall()

            if password:
                hash_pass = sha256_crypt.encrypt(password)
            else:
                hash_pass = result[0][2]

            cursor.execute('UPDATE adminaccount SET email = %s, password = %s, username = %s, role = %s WHERE adminid = %s',(email,password,username,role,hash_pass))
            cursor.connection.commit()
            cursor.close()

            flash('Admin edited.')
            return redirect(url_for('admindbpages', pages = 'manageuser'))
        
        if action == 'delete':

            adminid = request.args.get('adminid')

            cursor.execute('DELETE FROM adminaccount WHERE adminid = %s',(adminid,))
            cursor.connection.commit()
            cursor.close()

            flash('Admin account deleted.')
            return redirect(url_for('admindbpages', pages = 'manageuser'))
        
        if action == 'archive':

            adminid = request.args.get('adminid')

            cursor.execute('UPDATE adminaccount SET accountstatus = %s WHERE adminid = %s',(0,adminid))
            cursor.connection.commit()
            cursor.close()

            return redirect(url_for('admindbpages', pages = 'manageuser'))

    return redirect(url_for('admindbpages', pages = 'manageuser'))

@app.route('/adminmodifyalumni', methods=['POST','GET'])
def adminmodifyalumni():
    if request.method == 'POST':

        action = request.args.get('action')

        cursor = mysql.connect().cursor()

        if action == 'add':
            firstname = request.form['addalumnifname']
            lastname = request.form['addalumnilname']
            email = request.form['addalumniemail']
            password = request.form['addalumnipw']
            accountcreated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute('SELECT alumniid FROM alumniapplicants')
            result = cursor.fetchall()

            providedID = random.randint(1,999999)
            takenID = [int(id[1]) for id in result]
            if providedID in takenID:
                providedID = random.randint(1,999999)
            else:
                pass

            fullname = firstname + ' ' + lastname

            hash_pass = sha256_crypt.encrypt(password)

            cursor.execute('INSERT INTO alumniapplicants(emailaddress, password, accountcreated) VALUES(%s,%s,%s)',(email,hash_pass,accountcreated))
            cursor.connection.commit()

            cursor.execute('SELECT alumniid FROM alumniapplicants WHERE emailaddress = %s',(email,))
            result = cursor.fetchall()

            cursor.execute('INSERT INTO alumniprofile(fname,lname,fullname) VALUES(%s,%s,%s)',(firstname,lastname,fullname))
            cursor.connection.commit()

            cursor.close()

            flash('Alumni added.')
            return redirect(url_for('admindbpages', pages = 'manageuser'))

        if action == 'edit':

            alumniid = request.args.get('alumniid')

            firstname = request.form['editalumnifname']
            lastname = request.form['editalumnilname']
            email = request.form['editalumniemail']
            password = request.form['editalumnipw']
            accvalidation = request.form['accvalidation']
            hash_pass = ''
            fullname = str(firstname) + ' ' + str(lastname)


            if password:
                hash_pass = sha256_crypt.encrypt(password)
            else:
                cursor.execute('SELECT password FROM alumniapplicants WHERE alumniid = %s',(alumniid,))
                result = cursor.fetchall()

                hash_pass = result[0][0]

            cursor.execute('UPDATE alumniapplicants SET emailaddress = %s, password = %s, validity = %s WHERE alumniid = %s',(email,hash_pass,accvalidation,alumniid))
            cursor.execute('UPDATE userprofile SET fname = %s, lname = %s, fullname = %s WHERE alumniid = %s',(firstname,lastname,fullname,alumniid))
            cursor.connection.commit()
            cursor.close()

            flash('Alumni account edited.')
            return redirect(url_for('admindbpages', pages = 'manageuser'))
        
        
        if action == 'delete':

            alumniid = request.args.get('alumniid')

            cursor.execute('DELETE FROM alumniapplicants WHERE alumniid =  %s',(alumniid,))
            cursor.execute('DELETE FROM userprofile WHERE alumniid = %s',(alumniid,))

            try:
                cursor.execute('DELETE FROM alumniapplication WHERE alumniid = %s,',(alumniid,))
            except:
                pass
            try:
                cursor.execute('DELETE FROM messages WHERE alumniid = %s',(alumniid,))
            except:
                pass
            try:
                cursor.execute('DELETE FROM reviews WHERE alumniid = %s',(alumniid,))
            except:
                pass
            cursor.connection.commit()
            cursor.close()

            flash('Alumni account deleted.')
            return redirect(url_for('admindbpages', pages = 'manageuser'))
        
        else:
            return redirect(url_for('admindbpages', pages = 'manageuser'))

    else:

        cursor = mysql.connect().cursor()

        try:
            action = request.args.get('action')
        except:
            pass

        if action == 'archive':
            alumniid = request.args.get('alumniid')

            cursor.execute('UPDATE alumniapplicants aa INNER JOIN userprofile up SET aa.accountstatus = %s WHERE aa.alumniid = %s',(0,alumniid))
            cursor.execute('UPDATE alumniapplication SET applicationstatus = %s WHERE alumniid = %s',(0,alumniid))
            cursor.connection.commit()
            cursor.close()

            flash('Alumni account archived.')
            return redirect(url_for('admindbpages', pages = 'manageuser'))
        else:
            return redirect(url_for('admindbpages', pages = 'manageuser'))


@app.route('/archivecompanyacc', methods=['POST','GET'])
def archivecompany():

    cursor = mysql.connect().cursor()
    companyid = request.args.get('compid')

    verify_if_job_exist = cursor.execute('SELECT * FROM alumnijobs WHERE companyid = %s',(companyid,))
    verify_if_application_exist = cursor.execute('SELECT * FROM alumniapplication WHERE companyid = %s',(companyid,))
        
    cursor.execute('UPDATE employeraccount SET accountstatus = %s WHERE companyid = %s',(0,companyid))
    cursor.connection.commit()

    if verify_if_job_exist:
        cursor.execute('UPDATE alumnijobs aj INNER JOIN alumnisavedjobs SET jobstatus = %s WHERE companyid = %s',(0,companyid))
        cursor.connection.commit()
    else:
        pass

    if verify_if_application_exist:
        cursor.execute('UPDATE alumniapplication SET applicationstatus = %s WHERE companyid = %s',(0,companyid))
        cursor.connection.commit()
    else:
        pass

    cursor.close()

    flash('Company archived.')
    return redirect(url_for('admindbpages', pages = 'company'))
    
    

@app.route('/deleteacc', methods=['POST'])
def deleteacc():
    if request.method == 'POST':

        cursor = mysql.connect().cursor()

        companyid = request.args.get('compid')

        cursor.execute('DELETE FROM employeraccount WHERE companyid  = %s',(companyid,))


        try:
            cursor.execute('DELETE FROM alumniapplication WHERE companyid = %s',(companyid,))
        except:
            pass
        try:
            cursor.execute('DELETE FROM alumnijobs WHERE companyid = %s',(companyid,))
        except:
            pass
        try:
            cursor.execute('DELETE FROM alumnisavedjobs WHERE companyid = %s',(companyid,))
        except:
            pass
        try:
            cursor.execute('DELETE FROM messages WHERE companyid = %s',(companyid,))
        except:
            pass
        try:
            cursor.execute('DELETE FROM reviews WHERE companyid = %s',(companyid,))
        except:
            pass
        cursor.connection.commit()
        cursor.close()

        flash('Deleted company account.')
        return redirect(url_for('admindbpages', pages = 'company'))
    return redirect(url_for('admindbpages', pages = 'company'))

@app.route('/unarchive')
def unarchive():

    cursor = mysql.connect().cursor()

    userid = request.args.get('userid')
    email = request.args.get('email')

    verify_if_alumni_acc = cursor.execute('SELECT * FROM alumniapplicants WHERE alumniid = %s AND emailaddress = %s',(userid,email))
    verify_if_company_acc = cursor.execute('SELECT * FROM employeraccount WHERE companyid = %s AND emailaddress = %s',(userid,email))

    if verify_if_company_acc:
        cursor.execute('UPDATE employeraccount SET accountstatus = %s WHERE companyid = %s',(1,userid))
        cursor.execute('UPDATE alumnijobs SET jobstatus = %s WHERE companyid = %s',(1,userid))
        cursor.execute('UPDATE alumniapplication SET applicationstatus = %s WHERE companyid = %s',(1,userid))
        cursor.connection.commit()
        cursor.close()
            
    if verify_if_alumni_acc:
        cursor.execute('UPDATE alumniapplicants SET accountstatus = %s WHERE alumniid = %s',(1,userid))
        cursor.execute('UPDATE alumniapplication SET applicationstatus = %s WHERE alumniid = %s',(1,userid))
        cursor.connection.commit()
        cursor.close()

    return redirect(url_for('admindbpages', pages = 'manageuser'))

if __name__ == '__main__':
    app.run(debug=True)
    socketio.run(app)
    app.run(ssl_context="adhoc")