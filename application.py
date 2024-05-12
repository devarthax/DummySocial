from datetime import datetime
from typing import List
from flask import Flask, redirect, url_for, render_template, request, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy, query #type: ignore
from sqlalchemy import ForeignKey #type: ignore
from sqlalchemy import Integer #type: ignore
import hashlib
import os
from sqlalchemy.orm import relationship #type: ignore

# flask application and configurations parameters
app = Flask(__name__)
app.secret_key = "sjWXXQLMn8"
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root@localhost:3306/dbsito"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "propics" 
ALLOWED_EXTENSIONS = {'jpg', 'png'}

db = SQLAlchemy(app)

class Utente(db.Model):

    __tablename__ = "Utente"

    _id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.types.CHAR(40), unique=True, nullable=False)
    email = db.Column(db.types.CHAR(40), unique=True, nullable=False)
    password = db.Column(db.types.CHAR(40), nullable=False)
    profilePicture = db.Column(db.String(120), nullable=False)

    def __init__(self, name, email, password, profilePicture):
        self.name = name
        self.email = email
        self.password = password
        self.profilePicture = profilePicture

class Post(db.Model):
    _id = db.Column("idPost", db.Integer, primary_key=True)
    descr = db.Column(db.String(500), nullable=False)
    date = db.Column(db.types.DATE)
    userId = db.Column(ForeignKey("Utente.id"))
    utente = relationship("Utente")

    def __init__(self, descr, date, userId):
        self.descr = descr
        self.date = date
        self.userId = userId

@app.route("/")
def default_url():
    return redirect(url_for("welcome_message"))

@app.route("/index.html")
def welcome_message():
    return render_template("index.html")

@app.route("/signup.html", methods=["POST", "GET"])
def go_to_signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        file = request.files["propic"]

        # make the name of the file unique in the directory (in the model name is set as unique, i.e. all records MUST have
        # different names, so for the transitive property if I substitute the filename with name + propic each file
        # will have unique filename.)
        filename = username + "-propic" + "." + file.filename[-3:] 
        
        if allowed_file(filename):
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            flash("File non consentito.")
            return render_template("signup.html")

        hash_password = hashlib.sha1(password.encode()).hexdigest()
        usr = Utente(username, email, hash_password, filename)
        
        try:
            db.session.add(usr)
            db.session.commit()
        except: 
            flash("Errore. Utente già esistente.")
            return render_template("signup.html")
        
        return redirect(url_for("login"))

    else:  
        return render_template("signup.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        enteredMail = request.form["userEmail"]
        enteredPass = request.form["userPassword"]
        hash_pass = hashlib.sha1(enteredPass.encode()).hexdigest()

        try:
            entry = Utente.query.filter_by(email=enteredMail, password=hash_pass).first()
        except Exception as e:
            flash("Qualcosa è andato storto.")
            return render_template("login.html")
        
        if entry:
            session["id"] = entry._id
            session["username"] = entry.name
            session["email"] = entry.email
            session["propic"] = entry.profilePicture

            return redirect(url_for("welcome_message"))
        else:
            flash("Utente non trovato. Ricontrolla le credenziali.")
            return render_template("login.html")
    else:
        return render_template("login.html")

@app.route("/update-user", methods=["POST", "GET"])
def update_user():
    if "username" in session:
        if request.method == "GET":
            return render_template("update.html")
        else:
            entry = Utente.query.filter_by(email=session["email"]).first()
            newUser = request.form["username"]
            newMail = request.form["email"]
            entry.name = newUser
            entry.email = newMail 
            db.session.commit()
            session["username"] = newUser
            session["email"] = newMail

            flash("Credenziali aggiornate")
            return redirect(url_for("login"))
    else:
        return render_template("signup.html")

@app.route("/insert-post", methods=["POST", "GET"])
def insert_post():
    if request.method == "GET":
        return render_template("insert-post.html")
    else:
        descr = request.form["descr"]
        post = Post(descr, datetime.today().strftime('%Y-%m-%d'), session["id"])
        
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("insert_post"))

@app.route("/del-post/<postId>")
def del_post(postId):
    try:
        Post.query.filter_by(_id=postId, userId=session["id"]).delete()
        db.session.commit()
        return redirect(url_for("show_user", username=session["username"]))
    except: 
        return redirect(url_for("login"))


@app.route("/find-user", methods=["POST", "GET"])
def find_user():
    if request.method == "GET":
        return render_template("find-user.html")
    else:
        inputValue = request.form["searchValue"]
        search = "%{}%".format(inputValue)
        users = Utente.query.filter(Utente.name.like(search)).all()
        
        for user in users:
            flash(user.name)
        
        return render_template("find-user.html")

@app.route("/users/<username>")
def show_user(username):
    entry = Utente.query.filter_by(name=username).first()
    
    if entry:
        posts = Post.query.filter_by(userId = entry._id).all()
        return render_template("show-user.html", utente=entry.name,foto=entry.profilePicture, postsFound = posts)
    else:
        return render_template("page-not-found.html")

@app.route("/propics/<name>")
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name) 

@app.route("/user")
def user():
    if "username" in session:
        return render_template("user.html")
    else:
        return redirect(url_for("go_to_signup"))

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("email", None)
    return redirect(url_for("go_to_signup"))

@app.errorhandler(404)
def page_not_found(error):
    return render_template("page-not-found.html"), 404

with app.app_context():
    db.create_all()

# functions 
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

  