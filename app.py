from random import randint
from flask import Flask, render_template, request, Response, redirect, send_file,session,url_for
from flask_login import LoginManager,login_required,UserMixin, current_user,login_user,logout_user
from flask_mail import Mail,Message
from flask_sqlalchemy import SQLAlchemy
import os
import cv2
import numpy as np
import csv
import face_recognition
from deepface import DeepFace
from datetime import datetime
#import pyshine as ps
import timeit
import time
from playsound import playsound
import pandas as pd
import plotly
import plotly.express as px
import json

app = Flask(__name__)

#configurations for database and mail
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///EmployeeDB.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'mysecretkey'
db = SQLAlchemy(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS']= True
app.config['MAIL_USERNAME'] = 'f770654@gmail.com'
app.config['MAIL_PASSWORD'] = 'facerecogManisha'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
mail_ = Mail(app)



@login_manager.user_loader
def load_user(user_id):
    return users.query.get(user_id)

#employee database 
class employee(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    hiringDate = db.Column(db.String(10), default=datetime.now().strftime("%d-%m-%Y"))

    def __repr__(self) -> str:
        return f"{self.id} - {self.name} - {self.department} - {self.email} - {self.hiringDate}"

#users/owner database
class users(db.Model,UserMixin):
    id = db.Column(db.String(20), primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(80), nullable = True) 
    mail = db.Column(db.String(80), nullable = True) 
    password = db.Column(db.String(80), nullable=False)
    dateCreated = db.Column(db.DateTime, default = datetime.utcnow)

    def __repr__(self):
        return '<User {}>'.format(self.username)

path = 'static/TrainingImages'

@app.route('/')
def index():
    try:
        cap.release()
    except:
        pass
    try:
        cap2.release()
    except:
        pass
    return render_template('index.html')

#user login
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.query.filter_by(username=username).first()
        #if user exist in database then login otherwise back to login page a message
        if user is not None and user.password == password:
            login_user(user)
            return redirect('/')
        else:
            return render_template('login.html', incorrect=True)
    return render_template('login.html')

#user logout
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect('/')

#to mail employee/user for successful registraition 
def send_mail(email, text):
    msg = Message('Successfully Registered', recipients=[email], sender = 'employeesecurity@facerecog.com', body=text)
    mail_.send(msg)

#user registration
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        id = request.form['id']
        username = request.form['username']
        name = request.form['name']
        mail = request.form['mail']
        pass1 = request.form['pass']
        pass2 = request.form['pass2']

        #check if the owner id and username are unique or not.
        user = users.query.filter_by(username=username).first()
        user2 = users.query.filter_by(id = id).first()
        #if not unique or passwords do not match then back to sign up page with informative message, otherwise register the user
        if user is not None or user2 is not None:
            return render_template('signup.html', incorrect=True, msg = 'User with same ID or Username already exist')
        elif pass1 != pass2:
            return render_template('signup.html', incorrect = True, msg = "Passwords do not match")
        else:
            new_user = users(id = id,name = name, mail = mail,username=username, password=pass1)
            db.session.add(new_user)
            db.session.commit()
            msg = f'''Hello {new_user.name}
Your owner account has been successfully created

Thank You.
Face Recognition Based Employee Attendance Logger
'''
            send_mail(new_user.mail,msg)
            return render_template('login.html', registered = True)

    return render_template('signup.html')


#user password reset request
@app.route('/reset_request',methods = ['GET','POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form['mail']
        user = users.query.filter_by(mail = email).first()
        #if user with given mail id exists then generate an OTP and mail to the user
        if user:           
            otp = randint(000000,999999)
            sendResetMail(email,otp)
            session['id'] = user.id
            session['otp'] = otp
            return render_template('OTP.html')
        else:
            return render_template('resetRequest.html', incorrect = True)
    return render_template('resetRequest.html')

#function to mail password reset OTP
def sendResetMail(mail,otp):
    msg = Message('Reset Password', recipients=[mail],sender='employeesecurity@facerecog.com')
    msg.body = f''' your otp is {str(otp)}. if you didn't send a password reset request, please ignore this message'''
    mail_.send(msg)

#to verigy OTP
@app.route('/verifyOTP', methods = ['GET','POST'])
def verifyOTP():
    #if sent OTP matches with user typed OTP then redirect to reset password page
    otp2 = int(request.form['otp'])
    if session['otp'] == otp2:
        return render_template('resetPassword.html')
    else:
        return render_template('OTP.html', incorrect = True)

#user password reset
@app.route('/resetPass',methods = ['GET','POST'])
def resetPass():
    pw1 = request.form['pass1']
    pw2 = request.form['pass2']
    #if both passwords matches and are of length atleast 8, then chnage the user password.
    if pw1 == pw2:
        user = users.query.filter_by(id = session['id']).first()
        user.password = pw1
        db.session.commit()
        return render_template('login.html', reseted = True)
    else:
        return render_template('resetPassword.html',incorrect = True)

#add new employee in the employee database
@app.route("/add", methods=['GET', 'POST'])
@login_required
def add():
    try:
        cap2.release()
    except:
        pass
    invalid =0
    if request.method == 'POST':
        id = request.form['id']
        name = request.form['name']
        dept = request.form['dept']
        mail = request.form['mail']
        #in below code invalid = 0 for no problem, invalid = 1 for not a unique id, invalid=2 for not uploading photo
        #if account created the send mail to the employee otherwise rollback last submission
        try:
            invalid = 1
            emp = employee(id=id, name=name, department=dept, email=mail)
            db.session.add(emp)
            db.session.commit()
            fileNm = id + '.jpg'
            msg = f'''Hi {name},

Welcome to the organization.
you have been successfully registered in employee database.
    
Thank You.
Face Recognition Based Employee Attendance Logger'''
            send_mail(mail,msg)
            try:
                photo = request.files['photo']
                photo.save(os.path.join(path, fileNm))
            except:
                invalid = 2
                cv2.imwrite(os.path.join(path, fileNm), pic)
                del globals()['pic']
            invalid = 0
        except:
            db.session.rollback()
    allRows = employee.query.all()
    return render_template("insertPage.html", allRows=allRows, invalid = invalid)

#to delete an existing employee
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    #delete from database
    emp = employee.query.filter_by(id=id).first()
    db.session.delete(emp)
    db.session.commit()
    fn = id + ".jpg"
    #delete photo stored in training images
    try:
        os.unlink(os.path.join(path, fn))
    except:
        pass
    #marking status as terminated in attendance records for deleted employee
    df = pd.read_csv("static/records.csv")
    df.loc[df["Id"] == id, "Status"] = "Terminated"
    df.to_csv("static/records.csv", index=False)

    return redirect("/add")

#to update an existing employee
@app.route("/update", methods=['GET', 'POST'])
@login_required
def update():
    id = request.form['id']
    emp = employee.query.filter_by(id=id).first()
    #upate in database
    emp.name = request.form['name']
    emp.department = request.form['dept']
    emp.email = request.form['mail']
    db.session.commit()
    #update photo
    fileNm = id + '.jpg'
    try:
        try:
            photo = request.files['photo']
            photo.save(os.path.join(path, fileNm))
        except:
            cv2.imwrite(os.path.join(path, fileNm), pic)
            del globals()['pic']
    except:
        pass
    #update in attendance records
    df = pd.read_csv("static/records.csv")
    df.loc[(df["Id"] == id) & (df['Status'] == 'On Service'), ['Name','Department']] = [emp.name,emp.department]
    df.to_csv("static/records.csv", index=False)
    return redirect("/add")

#generating frames for capturing photo ny detecting smile
def gen_frames_takePhoto():
    start = timeit.default_timer()
    flag = False
    num = -1

    while True:
        ret, frame = cap2.read()  # read the camera feed
        if ret:
            if num == 0:
                #if the numbering for capturing phto has completed then release camera and save the image 
                global pic
                pic = frame
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                playsound("static/cameraSound.wav")
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n'+frame+b'\r\n')
                cap2.release()
                break

            # resize and convert the frame to Gray
            frameS = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
            frameS = cv2.cvtColor(frameS, cv2.COLOR_BGR2RGB)
            # finding list of face locations
            facesLoc = face_recognition.face_locations(frameS)
            #if more than 1 person is in frame then don't consider
            if len(facesLoc) > 1:
                cv2.putText(frame, "Only one person allowed", (100, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                flag = False
                continue

            for faceLoc in facesLoc:  
                # analyze the frame and look for emotion attribute and save it in a result
                result = DeepFace.analyze(
                    frame, actions=['emotion'], enforce_detection=False)
                #face locations
                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                #if the smotion is happy, start numbering and check same for 3 upcoming frames
                if result['dominant_emotion'] == 'happy' and timeit.default_timer() - start > 5:

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    if flag:
                        cv2.putText(frame, str(num), (150, 200),cv2.FONT_HERSHEY_SIMPLEX, 6, (255, 255, 255), 20)
                        time.sleep(1)
                        num = num-1

                    else:
                        flag = True
                        num = 3
                else:
                    flag = False
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            #pass the frame to show on html page
            yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n'+frame+b'\r\n')

#passing generated frames to html page
@app.route('/takePhoto', methods=['GET', 'POST'])
def takePhoto():
    #start camera 
    global cap2
    cap2 = cv2.VideoCapture(0 + cv2.CAP_DSHOW)
    return Response(gen_frames_takePhoto(), mimetype='multipart/x-mixed-replace; boundary=frame')

#encodings of known faces
@app.route("/encode")
@login_required
def encode():
    images = []
    myList = os.listdir(path)

    global encodedList
    global imgNames

    #function for saving images name ie employees' ids in imgNames
    def findClassNames(myList):
        cNames = []
        for l in myList:
            curImg = cv2.imread(f'{path}/{l}')
            images.append(curImg)
            cNames.append(os.path.splitext(l)[0])
        return cNames
    #function for saving face encodings in encodedList
    def findEncodings(images):
        encodeList = []
        for img in images:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            try:
                encode = face_recognition.face_encodings(img)[0]
                encodeList.append(encode)
            except:
                pass
        return encodeList

    imgNames = findClassNames(myList)
    encodedList = findEncodings(images)
    return render_template("recogPage.html")

#generating frames for recognizer
def gen_frames():
    oldIds = []
    #functin to mark attendance
    def markEntry(id):
        with open('static/records.csv', 'r+') as f:
            #extract todays' attendance
            myDataList = [
                line for line in f if datetime.now().strftime('%d-%m-%Y') in line]
            idList = []
            for line in myDataList:
                entry = line.split(',')
                idList.append(entry[0])
            #mark attendance only if the employee is not already marked
            if (id not in idList):
                now = datetime.now()
                date = now.strftime("%d-%m-%Y")
                dtime = now.strftime('%H:%M:%S')
                emp = employee.query.filter_by(id=id).first()
                f.writelines(
                    f'\n{id},{emp.name},{emp.department}, {dtime},{date},{"On Service"}')

    while True:
        success, img = cap.read()
        
        if success is True:
            img = cv2.flip(img,1)
            #resize and covert the frame to RGB
            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
            #put date on the frame
            cv2.putText(img, datetime.now().strftime("%D %H:%M:%S"),
                    (10, 15), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 255), 1)
            #finding face locations in frame
            facesCurFrame = face_recognition.face_locations(imgS)
            #encoding found faces
            encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)
            #for each face in the frame
            for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
                #compare face encoding with known face encodings
                matches = face_recognition.compare_faces(encodedList, encodeFace)
                faceDis = face_recognition.face_distance(encodedList, encodeFace)
                # the one with minimum euiclidian distance
                matchIndex = np.argmin(faceDis)

                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                #if person is known then show id and name in green color and mark attendance if he is appearing for first time in the day
                if ((matches[matchIndex]) & (faceDis[matchIndex] < 0.5)):
                    Id = imgNames[matchIndex]
                    emp = employee.query.filter_by(id=Id).first()
                    cv2.putText(img, Id, (x1, y2 + 25), cv2.FONT_HERSHEY_TRIPLEX, 0.8, (0, 255, 0), 2)
                    cv2.putText(img, emp.name, (x1, y2 + 50),cv2.FONT_HERSHEY_TRIPLEX, 0.8, (0, 255, 0), 2)
                    # below two lines can also be used instead of above two, text look better with putBText
                    # ps.putBText(img, emp.name, text_offset_x= x1+5, text_offset_y=y2 +45, vspace=5,hspace=5, font_scale=1, background_RGB=(0,255,0), text_RGB=(255,255,255), thickness=2, alpha=0.5)
                    # ps.putBText(img, Id, text_offset_x= x1+5, text_offset_y=y2+10, vspace=5,hspace=5, font_scale=1, background_RGB=(0,255,0), text_RGB=(255,255,255), thickness=2, alpha=0.5)
                    cv2.rectangle(img, (x1, y1), (x2, y2-4), (0,255,0), 2)
                    if Id in oldIds:
                        pass
                    else:
                        markEntry(Id)
                        oldIds.append(Id)
                # if not matches then show unknown in red color 
                else:
                    #ps.putBText(img, 'Unknown', text_offset_x= x1+5, text_offset_y=y2+10, vspace=5,hspace=5, font_scale=1, background_RGB=(255,0,0), text_RGB=(255,255,255), thickness=2, alpha=0.5)
                    cv2.putText(img, 'unknown', (x1, y2 + 25), cv2.FONT_HERSHEY_TRIPLEX, 0.8, (0, 0, 255), 2)
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0,0,255), 2)

            ret, buffer = cv2.imencode('.jpg', img)
            img = buffer.tobytes()
            #passsing frame to show on html page
            yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n'+img+b'\r\n')
            
#passing generated frames to html page 'recogPage.html'
@app.route('/video', methods=['GET', 'POST'])
def video():
    global cap
    cap = cv2.VideoCapture(0)
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

#show attendance records
@app.route("/AttendanceSheet")
@login_required
def AttendanceSheet():
    rows = []
    with open('static/records.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    fieldnames = ['Id', 'Name', 'Department', 'Time', 'Date', 'Status']
    return render_template('RecordsPage.html', allrows=rows, fieldnames=fieldnames, len=len)

# download all records (combined for all dates)
@app.route("/downloadAll")
def downloadAll():
    return send_file('static/records.csv', as_attachment=True)

# download today's attendance records only
@app.route("/downloadToday")
def downloadToday():
    #extracting todays' records only
    df = pd.read_csv("static/records.csv")
    df = df[df['Date'] == datetime.now().strftime("%d-%m-%Y")]
    df.to_csv("static/todayAttendance.csv", index=False)
    return send_file('static/todayAttendance.csv', as_attachment=True)

# reset today's attendance
@app.route("/resetToday")
@login_required
def resetToday():
    df = pd.read_csv("static/records.csv")
    df = df[df['Date'] != datetime.now().strftime("%d-%m-%Y")]
    df.to_csv("static/records.csv", index=False)
    return redirect('/AttendanceSheet')

# some stats on attendance records
@app.route("/stats")
@login_required
def stats():

    #fetching data from attendance csv file and employee database
    df = pd.read_csv("static/records.csv")
    rows = employee.query.all()
    db = [str(row) for row in rows]
    db = pd.DataFrame(db)
    db = pd.DataFrame(data=list(map(lambda x: x.split(" - "), db[0])), columns=['Id', 'Name', 'Department', 'Mail', 'Hiring Date'])

    #create a dataframe which consists the num of employees registered and present today grouped by their dept
    today = df[(df["Date"] == datetime.now().strftime("%d-%m-%Y")) & (df['Status'] == 'On Service')]
    today_counts = pd.DataFrame(today.groupby(['Department']).count()['Id'])
    db_counts = pd.DataFrame(db.groupby(['Department']).count()['Id'])
    attendance = pd.merge(db_counts, today_counts,
                          how='outer', left_index=True, right_index=True)
    attendance.columns = ["Registered", "Present"]
    attendance = attendance.fillna(0).astype(int)
    attendance['Absent'] = attendance['Registered']-attendance['Present']

    #today's attendance dept wise 
    fig1 = px.bar(attendance, x=attendance.index, y=attendance.columns, barmode='group',  labels={'value': 'No of Employees'}, 
    title='Department Wise today\'s Attendance', color_discrete_sequence=px.colors.qualitative.T10, template='presentation')

    #department wise attendance in percentage&counts
    fig2 = []
    for d in db['Department'].unique():
        present = len(today[today['Department'] == d])
        fig2.append(px.pie(df, values=[present, len(db[db['Department'] == d])-present], names=['Present', 'Absent'],  
         hole=.4, title=d + ' Department', color_discrete_sequence=px.colors.qualitative.T10))

    #last 7 working days' attendance
    dates = df['Date'].unique()[-7:]
    df_last7 = df[df['Date'].isin(dates)]
    fig3 = px.histogram(df_last7, x='Date', color="Department", title='Date & Department wise Attendance',  
    color_discrete_sequence=px.colors.qualitative.T10, template='presentation')

    #individual attendance percentage
    hiringDates = [datetime.date(datetime.strptime(d, '%d-%m-%Y')) for d in db['Hiring Date']]
    daysInJob = [(datetime.date(datetime.now()) - d).days + 1 for d in hiringDates]
    presentDays = [len(df[(df['Id'] == id) & (df['Status'] == 'On Service')]) for id in db['Id']]
    db['Attendance(%)'] = [round(presentDays[i]*100/daysInJob[i], 2) for i in range(0, len(db))]


    JSON1 = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)
    JSON2 = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)
    JSON3 = json.dumps(fig3, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template('statsPage.html', JSON1=JSON1, JSON2=JSON2, JSON3=JSON3,depts=db['Department'].unique(), 
    td=[sum(attendance['Registered']), sum(attendance['Present'])], titles=db.columns.values, 
    data=list(db.sort_values(by='Attendance(%)', ascending=False, kind="mergesort").values.tolist()), len=len)

@app.route('/get')
def get_bot_response():
    userText = request.args.get('msg')
    # fetch ans corresponding to given question, bot_responses is a global variable declared in helpBot route
    bot_response = bot_responses.get(userText, "Sorry, Can't help with it :(")
    return bot_response
    

@app.route('/helpBot')
def helpBot():
    #load json file globally
    global bot_responses
    with open('static/help.json') as f:
        bot_responses = json.load(f) 
    return render_template('chatBot.html', keys = [*bot_responses])


if __name__ == "__main__":
    db.create_all()
    app.run(debug=False, port=8000)
