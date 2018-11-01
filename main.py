from flask import Flask, request, redirect, render_template, flash, session
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://blogz:lanstar@localhost:8889/blogz"
app.config['SQLALCHEMY_ECHO'] = True

db = SQLAlchemy(app)
app.secret_key = '123'

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    db_title = db.Column(db.String(120))
    db_body = db.Column(db.String(10000))
    db_date = db.Column(db.String(120))
    deleted = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __init__(self, title, body, date, author):
        self.db_title = title
        self.db_body = body
        self.db_date = date
        self.deleted = False
        self.author = author
    
    def __repr__(self):
        return "<Post %r>" % self.db_title

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), unique=False, nullable=False)
    blogs = db.relationship('Post', backref = 'author')

    def __init__(self, username, password):
        self.username = username
        self.password = password
    
    def __repr__(self):
        return '<User %r>' % self.username

#if the session is active, returns user
def in_session():
    if 'username' in session:
        current_user = User.query.filter_by(username=session['username']).first()
        print("-In Session-")
        return current_user
    else:
        print("-Not In Session-")
        return False

#get the previous entries in reverse order
def get_entries(author_id):
    if author_id.isdigit():
        return Post.query.filter_by(deleted=False, author_id=author_id).order_by(Post.id.desc())
    else:
        return Post.query.filter_by(deleted=False).order_by(Post.id.desc())
def get_authors():
    return User.query.order_by(User.id).all()

#require login 
@app.before_request
def require_login():

    print("-Before Request-")
    allowed_routes = ['login', 'signup', 'index', 'home']

    if request.endpoint not in allowed_routes and 'username' not in session and '/static/' not in request.path:
        flash("Login or Signup required.", "error")
        return redirect('/login')

    if request.endpoint in allowed_routes[0:2] and 'username' in session:
        flash("Already logged in!", "error")

#log user in
@app.route("/login", methods=['POST', 'GET'])
def login():

    if request.method == 'POST':
        login_username = request.form['user_login']
        login_pass = request.form['user_pass']
        user = User.query.filter_by(username=login_username).first()
        
        if user and login_pass:
            session['username'] = login_username
            flash("Welcome {0}, you are logged in.".format(user.username), "greenlight")
            return redirect("/newentry")
        
        elif not login_username or not login_pass:
            flash("All fields must be filled out", 'error')
        
        elif login_username and not user:
            flash("That username does not exist", 'error')
            return render_template('login.html', loggedin = in_session())

        else:
            flash("Incorrect password.", "error")
            return render_template('login.html', loggedin = in_session())

    return render_template('login.html', loggedin= in_session())

#function to validate new user input 
def validated(username, pass1, pass2):

    if username == "" or pass1 == "":
        flash("Please fill out all fields.", "error")
        return False

    if len(pass1) < 4 or len(pass1) > 20:
        flash("Password must be between 4 and 20 characters.", "error")
        return False

    if pass1 != pass2:
        flash("Passwords do not match.", "error")
        return False
        
    return True

#register or sign up a new user
@app.route("/signup", methods=['POST', 'GET'])
def signup():

    if request.method == 'POST':
        reg_username = request.form['new_user']
        reg_password = request.form['new_pass']
        verify = request.form['new_pass_2']
        existing_user = User.query.filter_by(username=reg_username).first()

        if validated(reg_username, reg_password, verify):
            if not existing_user:
                user = User(reg_username, reg_password)
                db.session.add(user)
                db.session.commit()
                session['username'] = reg_username
                flash("New user account created for {0}".format(reg_username), "greenlight")
                return redirect('/')
            else:
                flash("Username already exists.", "error")
        
    return render_template('signup.html', loggedin = in_session())

#log user out
@app.route('/logout')
def logout():
        del session['username']
        flash("User succesfully logged out.", "greenlight")
        return redirect('/blog')

#delete an entry
@app.route("/del-entry", methods=['POST'])
def del_entry():
    post_id = request.form['post_id']
    print(post_id)
    
    deleted_post = Post.query.get(post_id)
    deleted_post.deleted = True
    db.session.add(deleted_post)
    db.session.commit()

    return redirect("/")

#display an entry on its own page
@app.route("/entry")
def single_entry():
    post_id = request.args.get("id")
    display_entry = Post.query.filter_by(id=post_id).first()

    if display_entry not in get_entries("").all():
        flash("Entry ID '{0}' does not exist. ".format(post_id), "error")
        return redirect("/")

    return render_template('singleentry.html', post=display_entry, loggedin = in_session())

#display the new entry page
@app.route("/newentry")
def new_entry():
    return render_template('newentry.html', loggedin = in_session())

#add a new entry to database
@app.route("/add-entry", methods=['GET', 'POST'])
def add_entry():

    if request.method == 'POST':
        new_title = request.form['title']
        new_body = request.form['body']

        if not new_title or not new_body:
            flash("All fields must be filled out")
            return render_template('newentry.html', entry_title=new_title, entry_body=new_body, loggedin = in_session())

        #username = session['user']
        author = User.query.filter_by(username=session['username']).first()
    
        new_entry = Post(new_title, new_body, get_date(), author)
        db.session.add(new_entry)
        db.session.commit()

        return render_template('singleentry.html', post=new_entry, loggedin = in_session())

    return render_template('newentry.html', loggedin = in_session())

#home page with list of authors
@app.route("/home")
def home():
    
    return render_template('home.html', author_list=get_authors(), loggedin = in_session())

#return posts authored by the logged-in user
@app.route("/selfpost")
def self_post():
    self_author = User.query.filter_by(username=session['username']).first()
    return redirect("/blog?id="+str(self_author.id))

#return posts by a specific author
@app.route("/blog")
def single_user_entries():
    
    by_author = request.args.get("id")
    blog_author = User.query.get(by_author)

    if blog_author not in get_authors():
        flash("Author ID '{0}' does not exist. ".format(by_author), "error")
        return redirect("/")

    return render_template('entries.html', post_list=get_entries(by_author).all(), author = blog_author, loggedin = in_session())

def get_title():
    title = request.endpoint
    print(title)
    if title not in ["login", "signup", "authors"]:
        title = ""
    else:
        title = "- "+title
    return title

#gets the date the post was submitted at
def get_date():
    postdate = datetime.datetime.now()
    at_date = postdate.strftime("%b %d %Y")
    at_time = postdate.strftime("%I:%M %p")
    return at_time+" | "+at_date

@app.route("/")
def index():
    posts = Post.query.filter_by(deleted=False).all()

    return render_template('entries.html', post_list = posts, loggedin=in_session())

if __name__ == "__main__":
    app.run()