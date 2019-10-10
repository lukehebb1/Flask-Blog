import secrets, os
from PIL import Image #Pillow
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog import app, db, bcrypt, mail
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, RequestResetForm, ResetPasswordForm
from flaskblog.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message

@app.route("/")
@app.route("/home")
def home():
	page = request.args.get('page', 1, type=int) #get page else go to page 1
	posts = Post.query.paginate(page=page, per_page=5) #display posts from database, only display 5 at a time
	return render_template('home.html', posts=posts) #display home.html

@app.route("/about")
def about():
	return render_template('about.html', title='About') #display about.html with title

@app.route("/register", methods=['GET', 'POST']) #route accepts GET and POST requests
def register():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = RegistrationForm() #initialise form
	if form.validate_on_submit(): #ensure form is valid on submission
		hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8') #create hashed password
		user = User(username=form.username.data, email=form.email.data, password=hashed_pw) #create User object with info from form
		db.session.add(user) #add user to database
		db.session.commit() #commit changes
		flash(f'Your account has been created! You are now able to log in', 'success')
		return redirect(url_for('login')) #redirect to login page
	return render_template('register.html', title='Register', form=form) #display register.html with RegistrationForm

@app.route("/login", methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = LoginForm()
	if form.validate_on_submit(): #ensure form is valid on submission
		user = User.query.filter_by(email=form.email.data).first() #find user by email
		if user and bcrypt.check_password_hash(user.password, form.password.data): #if user exists and password entered matches user's password
			login_user(user, remember=form.remember.data) #login user
			next_page = request.args.get('next') #get next page
			flash('Login successful!', 'success')
			return redirect(next_page) if next_page else redirect(url_for('home')) #redirect to the next page if it exists else redirect to the homepage
		else:
			flash('Login Unsuccessful. Please check email and password', 'danger')
	return render_template('login.html', title='Login', form=form) #display login.html with LoginForm

@app.route("/logout")
def logout():
	logout_user()
	flash('Logout successful', 'success')
	return redirect(url_for('home'))

def save_picture(form_picture): #TODO: change picture to image
	random_hex = secrets.token_hex(8) #base of file name
	f_name, f_ext = os.path.splitext(form_picture.filename) #get file extention
	picture_fn = random_hex + f_ext #create image file name
	picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn) #create picture path

	output_size = (125, 125) #tuple of size in pixels
	i = Image.open(form_picture) #open image with Pillow
	i.thumbnail(output_size) #set thumbnail of image in certain size
	i.save(picture_path) #save image to picture path

	return picture_fn

@app.route("/account", methods=['GET', 'POST'])
@login_required #we need to login to access this route
def account():
	form = UpdateAccountForm()
	if form.validate_on_submit(): #ensure form is valid on submission
		if form.picture.data: #if change picture is used
			picture_file = save_picture(form.picture.data) #save and compress it
			current_user.image_file = picture_file #update it
		current_user.username = form.username.data #change username to new username
		current_user.email = form.email.data #change email to new email
		db.session.commit() #commit changes
		flash('Your account has been updated!', 'success')
		return redirect(url_for('account')) #redirect to account page
	elif request.method == 'GET':
		form.username.data = current_user.username #put username in username field
		form.email.data = current_user.email #put email in email field
	image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
	return render_template('account.html', title='Account', image_file=image_file, form=form)

@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
	form = PostForm()
	if form.validate_on_submit(): #ensure form is valid on submission
		post = Post(title=form.title.data, content=form.content.data, author=current_user) #create Post object using info from form
		db.session.add(post) #add post to database
		db.session.commit() #commit changes
		flash('Your post has been created', 'success')
		return redirect(url_for('home')) #redirect to homepage
	return render_template('create_post.html', title='New Post', form=form, legend='New Post')

@app.route("/post/<int:post_id>") #/post/1 etc
def post(post_id):
	post = Post.query.get_or_404(post_id) #give me the post with this id else give me 404 error
	return render_template('post.html', title=post.title, post=post)

@app.route("/post/<int:post_id>/update", methods=['GET', 'POST']) #/post/1 etc
@login_required
def update_post(post_id):
	post = Post.query.get_or_404(post_id) #give me the post with this id else give me 404 error
	if post.author != current_user:
		abort(403) #produce 403 error
	form = PostForm()
	if form.validate_on_submit(): #ensure form is valid on submission
		post.title = form.title.data #change title
		post.content = form.content.data #change content
		db.session.commit() #commit changes
		flash('Your post has been updated!', 'success')
		return redirect(url_for('post', post_id=post.id))
	elif request.method == 'GET':
		form.title.data = post.title #put in current title in title box
		form.content.data = post.content #put in current content in content box
	return render_template('create_post.html', title='Update Post', form=form, legend='Update Post')

@app.route("/post/<int:post_id>/delete", methods=['POST']) #/post/1 etc
@login_required
def delete_post(post_id):
	post = Post.query.get_or_404(post_id) #give me the post with this id else give me 404 error
	if post.author != current_user:
		abort(403) #produce 403 error
	db.session.delete(post) #delete post
	db.session.commit() #commit changes
	flash('Your post has been deleted', 'success')
	return redirect(url_for('home')) #redirect to home

@app.route("/user/<string:username>")
def user_post(username): #TODO rename to user_post or user_profile
	page = request.args.get('page', 1, type=int) #get page else go to page 1
	user = User.query.filter_by(username=username).first_or_404() #get the first user with the username else return 404 error
	posts = Post.query.filter_by(author=user).paginate(page=page, per_page=5) #display posts from database from this specific user, only display 5 at a time
	return render_template('user_posts.html', posts=posts, user=user)

def send_reset_email(user):
	token = user.get_reset_token() #get token
	msg = Message('Password Reset Request', sender='noreply@demo.com', recipients=[user.email]) #create message object
	msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email.''' #message body

	mail.send(msg) #send email

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request(): #route where they request reset password
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = RequestResetForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first() #give me first user with this email
		send_reset_email(user)
		flash('An email has been sent with instructions to reset your password', 'info')
		return redirect(url_for('login'))
	return render_template('reset_request.html', title='Reset Password', form=form)

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token): #route where they reset password with token active
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	user = User.verify_reset_token(token)
	if user is None: #if token is expired or invalid
		flash('That is an invalid or expired token', 'warning')
		return redirect(url_for('reset_request'))
	form = ResetPasswordForm()
	if form.validate_on_submit(): #ensure form is valid on submission
		hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8') #create hashed password
		user.password = hashed_pw #update password
		db.session.commit() #commit changes
		flash(f'Your password has been updated! You are now able to log in', 'success')
		return redirect(url_for('login')) #redirect to login
	return render_template('reset_token.html', title='Reset Password', form=form) 

#error handling
@app.errorhandler(404)
def error_404(error):
	return render_template('404.html'), 404

@app.errorhandler(403)
def error_403(error):
	return render_template('403.html'), 403

@app.errorhandler(500)
def error_500(error):
	return render_template('500.html'), 500