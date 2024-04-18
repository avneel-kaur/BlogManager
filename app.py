import os
import PIL
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.widgets import TextArea
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user

#getting absolute path of current directory
basedir = os.path.abspath(os.path.dirname(__file__))
app=Flask(__name__)
#For form security key
app.config["SECRET_KEY"]="subhas"
#Add database
app.config["SQLALCHEMY_DATABASE_URI"] =\
'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#Initialze the database
db=SQLAlchemy(app)
app.app_context().push()
migrate=Migrate(app,db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(username):
    return Users.query.get(username)

# define form class
class LoginForm(FlaskForm):
	username = StringField("User Name",validators=[DataRequired()])
	upassword = PasswordField("Password", validators=[DataRequired()])
	sub_button = SubmitField("Login")

# define signup form class
class SignUp(FlaskForm):
	username = StringField("User Name",validators=[DataRequired()])
	upassword = PasswordField("Password", validators=[DataRequired()])
	image = FileField("Profile Picture", validators = [DataRequired()])
	sub_button = SubmitField("SignUp")

class NewFollow(FlaskForm):
	username = StringField("User Name",validators=[DataRequired()])
	sub_button = SubmitField("Search")

class PostForm(FlaskForm):
    title  = StringField("title", validators = [DataRequired()])
    body = StringField("body", validators = [DataRequired()], widget = TextArea())
    image = FileField("image", validators = [DataRequired()])
    submit = SubmitField("submit")


class EditForm(FlaskForm):
    title  = StringField("title", validators = [DataRequired()])
    body = StringField("body", validators = [DataRequired()], widget = TextArea())
    image = FileField("New Image (optional)")
    submit = SubmitField("submit")

#define class for database
class Users(db.Model, UserMixin):
	username=db.Column(db.String, primary_key=True)
	#useremail=db.Column(db.String, unique=True)
	password=db.Column(db.String)

	follower = db.relationship('Follows', backref = 'followers', foreign_keys = 'Follows.follower')
	following = db.relationship('Follows', backref = 'followings', foreign_keys = 'Follows.following')

	posts = db.relationship('Posts', backref = 'poster', foreign_keys = 'Posts.user')

	def get_id(self):
           return (self.username)

class Posts(db.Model):
    __tablename__= 'posts'
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(255))
    body = db.Column(db.Text)
    user = db.Column(db.String(255), db.ForeignKey('users.username'))
    date = db.Column(db.DateTime, default = datetime.utcnow)

class Follows(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    follower = db.Column(db.String, db.ForeignKey('users.username'))
    following = db.Column(db.String, db.ForeignKey('users.username'))


@app.route("/", methods = ["GET", "POST"])
def login():
	form = LoginForm()

	if form.validate_on_submit():
		name = request.form.get("username")
		password = request.form.get("upassword")
		user = Users.query.filter_by(username=name).first()
		if user is None:
			return render_template("no_user.html")
		elif user.password == password:
			login_user(user)
			return redirect(url_for('feed'))
		else:
			return render_template("incorrect_password.html")

	return render_template("index.html", form=form)

@app.route("/signup", methods = ["GET", "POST"])
def signup():
	form = SignUp()
	if form.validate_on_submit():
		user = Users.query.get(form.username.data)
		if user is not None:
			return "username not available"
		name = form.username.data
		password = form.upassword.data
		user=Users(username=name, password=password)

		db.session.add(user)
		db.session.commit()

		
		path = user.username
		
		file = form.image.data
		im = Image.open(file)
		os.chdir(os.getcwd() + "/static")
		im.save(str(path) + ".png")
		os.chdir("..")
		return redirect(url_for('login'))

	return render_template("signup.html", form=form)

@app.route("/<string:name>")
@login_required
def profile(name):
	if name != current_user.username:
		return render_template("no_user.html")

	posts = Posts.query.filter_by(user=name).order_by(Posts.date)
	no_of_follow = Follows.query.filter_by(follower=name).count()
	no_of_follower = Follows.query.filter_by(following=name).count()
	no_of_blogs = Posts.query.filter_by(user=name).count()
	return render_template('profile.html', name = name, posts = posts, no_of_follow = no_of_follow, no_of_follower = no_of_follower, no_of_blogs = no_of_blogs)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add_post', methods=['GET', 'POST'])
@login_required
def add_post():
    form = PostForm()

    if form.validate_on_submit():
        post = Posts(title = form.title.data, body = form.body.data, user = current_user.username)
        
        form.title.data = None
        form.body.data = None

        db.session.add(post)
        db.session.commit()

        # path = post.id
        
        file = form.image.data
        im = Image.open(file)
        os.chdir(os.getcwd() + "/static")
        im.save(str(post.id) + ".png")
        os.chdir("..")
        return redirect(url_for('add_post'))

    return render_template("add_post.html", form = form)


@app.route('/new_follow', methods=['GET', 'POST'])
@login_required
def new_follow():
	app.config['url_follow'] = url_for('new_follow')
	app.config['url_unfollow'] = url_for('new_follow')
	form = NewFollow()

	users = Users.query.all()
	for user in users:
		if user.username == current_user.username:
			users.remove(user)
	
	following = []
	already_following = Follows.query.filter_by(follower = current_user.username).all()
	for x in already_following:
		following.append(x.following)

	if form.validate_on_submit():
		to_search = form.username.data
		search = "%{}%".format(to_search)
		users = Users.query.filter(Users.username.like(search)).all()
		for user in users:
			if user.username == current_user.username:
				users.remove(user)

	return render_template("new_follow.html", form = form, users = users, following = following)


@app.route('/<string:name1>/<string:name2>')
@login_required
def follow(name1, name2):
	if(name1 == name2):
		return "you can not follow yourself"

	if(current_user.username != name1):
		return redirect(url_for('login'))
	
	users = Users.query.all()
	username = []
	for user in users:
		username.append(user.username)
	if username.count(name2) == 0:
		return "no such person exist"

	connection = Follows.query.filter_by(follower = name1, following = name2).first()
	
	if connection is not None:
		return "you already follow" + name2

	follow = Follows(follower = name1, following = name2)
	db.session.add(follow)
	db.session.commit()

	# if button_from_followers is True:
	# 	return redirect(url_for('followers'))

	return redirect(app.config['url_follow'])


@app.route('/unfollow/<string:name1>/<string:name2>')
@login_required
def unfollow(name1, name2):
	if(name1 == name2):
		return "you can not unfollow yourself"

	if(current_user.username != name1):
		return redirect(url_for('login'))

	users = Users.query.all()
	username = []
	for user in users:
		username.append(user.username)
	if username.count(name2) == 0:
		return "no such person exist"

	connection = Follows.query.filter_by(follower = name1, following = name2).first()

	if connection is None:
		return "you do not follow" + name2

	db.session.delete(connection)
	db.session.commit()

	return redirect(app.config['url_unfollow'])


@app.route('/feed')
@login_required
def feed():
	name = current_user.username
	following = []
	follows = Follows.query.filter_by(follower=name).all()

	for follow in follows:
		following += [follow.following]
	
	posts = Posts.query.filter(Posts.user.in_(following)).all()

	return render_template('feed.html', posts = posts)


@app.route('/delete/<int:id>')
@login_required
def delete(id):

	post = Posts.query.get(id)
	name = current_user.username
	if name == post.user:
		db.session.delete(post)
		db.session.commit()
	else:
		return "you can not delete other user's posts"

	os.chdir(os.getcwd() + "/static")
	os.remove(str(post.id) + ".png")
	os.chdir("..")
	return redirect(url_for('profile', name = name))


@app.route('/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit(id):
	
	post = Posts.query.get(id)
	if current_user.username != post.user:
		return "you can not edit other's posts."
	
	form = EditForm()

	if form.validate_on_submit():
		post.title = form.title.data
		post.body = form.body.data
		db.session.add(post)
		db.session.commit()

		if form.image.data is not None:
			try:
				path = post.id
				file = form.image.data
				im = Image.open(file)
				os.chdir(os.getcwd() + "/static")
				im.save(str(post.id) + ".png")
				os.chdir("..")
			except:
				pass
		return redirect(url_for('profile', name = current_user.username))

	form.title.data = post.title
	form.body.data = post.body
	return render_template('edit.html', form = form)


@app.route('/followers')
def followers():
	app.config['url_follow'] = url_for('followers')
	app.config['url_unfollow'] = url_for('followers')
	name = current_user.username
	followers = Follows.query.filter_by(following=name).all()

	following = []
	already_following = Follows.query.filter_by(follower = current_user.username).all()
	for x in already_following:
		following.append(x.following)

	return render_template('followers.html', followers = followers, following = following)


@app.route('/following')
def following():
	app.config['url_follow'] = url_for('following')
	app.config['url_unfollow'] = url_for('following')
	name = current_user.username
	followers = Follows.query.filter_by(follower=name).all()

	return render_template('following.html', followers = followers, following = following)


@app.route('/other/<string:name>')
def other(name):
	users = Users.query.all()
	username = []
	for user in users:
		username.append(user.username)
	if username.count(name) == 0:
		return "no such person exist" 

	posts = Posts.query.filter_by(user=name).order_by(Posts.date)
	no_of_follow = Follows.query.filter_by(follower=name).count()
	no_of_follower = Follows.query.filter_by(following=name).count()
	no_of_blogs = Posts.query.filter_by(user=name).count()
	return render_template('other.html', name = name, posts = posts, no_of_follow = no_of_follow, no_of_follower = no_of_follower, no_of_blogs = no_of_blogs)


if __name__ == '__main__':
	app.run(debug=True)