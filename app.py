from flask import Flask, render_template, request, flash, redirect, session, jsonify
from werkzeug.security import generate_password_hash as passgen
from werkzeug.security import check_password_hash as passcheck
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os
from datetime import datetime

cred = credentials.Certificate("keys.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
blogsRef = db.collection(u'blogs')
authorsRef = db.collection(u'authors')


app = Flask(__name__)

app.config['SECRET_KEY'] = os.urandom(24)

@app.route('/')
def index():
	query = blogsRef.order_by(u"postedOn", direction=firestore.Query.DESCENDING)
	blogs = query.stream()
	print(type(blogs))
	return render_template("index.html", blogs=blogs)

@app.route('/admin/register/', methods=['GET', 'POST'])
def register():
	if request.method == 'POST':
		details = request.form
		if details['admin_key'] == os.environ['LocalEyesAdminKey']:
			fullname = str(details['first_name']).capitalize() + " " + str(details['last_name']).capitalize()
			password = passgen(details['password'])
			role = "Content Writer"
			identifier = str(details['first_name']).lower() + "." + str(details['last_name']).lower()
			authorsRef.document(identifier).set({
				u"fullname": fullname,
				u"identifier": identifier,
				u"password": password,
				u"role": role,
				u"isVerified": False
			})
			flash(f"ACCOUNT CREATION SUCCESSFULL. Welcome to LocalEyes {fullname}", "success")
			return redirect('/')
		else:
			flash("You are not authorized to create a Writer Account at LocalEyes.", "danger")
	return render_template('register.html')

@app.route('/admin/login/', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		details = request.form
		identifier = details['fullname']
		result = authorsRef.document(identifier).get()
		if result.exists:
			author = result.to_dict()
			check_pass = passcheck(author['password'], details['password'])
			if check_pass:
				session['logged_in'] = True
				session['author'] = author['fullname']
				session['isVerified'] = bool(author['isVerified'])
				session['role'] = author['role']
				flash(f"Login Successful. Welcome {session['author']}", "success")
				print(session['logged_in'], session['author'], session['isVerified'], session['role'])
				return redirect('/')
			else:
				flash("Password is incorrect, please try again.", "danger")
				return render_template("login.html")
		else:
			flash("User does not exist", "danger")
			return render_template("login.html")
	return render_template("login.html")

@app.route('/author/<identifier>')
def author(identifier):
	authorRef = authorsRef.document(identifier).get()
	if authorRef.exists:
		author = authorRef.to_dict()
		return jsonify({"result": author})
	else:
		return "No Such Author"

@app.route('/blog/<id>/')
def blogs(id):
	blog = blogsRef.document(id).get()
	if blog.exists:
		return render_template('blogs.html', blog=blog.to_dict())
	return "Blog Not Found"

@app.route('/write-blog/', methods=['GET', 'POST'])
def write_blog():
	if request.method == 'POST':
		if session['isVerified']:
			blogpost = request.form
			blogData = {
			u'title' : blogpost['title'],
			u'body' : blogpost['body'],
			u'category' : blogpost['category'],
			u'author' : session['author'],
			u'postedOn': datetime.now()
			}
			tagline = blogpost['title'].replace(" ", "-").replace(",", "").replace("!", "").replace(".", "").lower()
			blogsRef.document(tagline).set(blogData)
			flash('Blog Posted Successfully', 'success')
			return redirect('/')
		else:
			flash("You are not verified to write blogs right now", "danger")
			return redirect('/')
	return render_template('write-blog.html')

@app.route('/my-blogs/')
def my_blogs():
	author = session['author']
	resultBlog = blogsRef.where(u"author", u"==", author).stream()
	return render_template('my-blogs.html', my_blogs=resultBlog)

@app.route('/categories')
def categories():
	_categories = ['LAUNCH', 'DESIGN', 'FEATURES']
	blogsList = {}
		
	if request.args:
		category = str(request.args.get('q')).upper()
		blogs = blogsRef.where(u"category", u"==", category).get()
		blogsList[category] = []
	else:
		for _category in _categories:
			blogsList[_category] = []
		blogs = blogsRef.order_by(u"category", direction=firestore.Query.DESCENDING).get()
	for blog in blogs:
		blogsList[blog.to_dict()['category']].append(blog.to_dict())
	return jsonify(blogsList)

@app.route('/edit-blog/<int:id>/', methods=['GET', 'POST'])
def edit_blog(id):
	if request.method == 'POST':
		cur = mysql.connection.cursor()
		body = request.form['body']
		title = request.form['title']
		cur.execute("UPDATE blog SET title=%s, body=%s WHERE blog_id=%s", (title, body, id))
		mysql.connection.commit()
		cur.close()
		flash('Blog Updated Successfully', 'success')
		return redirect('/blog/{}'.format(id))

	cur = mysql.connection.cursor()
	resultvalue = cur.execute("SELECT * FROM blog WHERE blog_id={}".format(id))
	if resultvalue > 0:
		blog = cur.fetchone()
		blog_form = {}
		blog_form['title'] = blog[1]
		blog_form['body'] = blog[3]
		return render_template('edit-blog.html', blog_form=blog_form)

@app.route('/delete-blog/<int:id>/')
def delete_blog(id):
	cur = mysql.connection.cursor()
	cur.execute("DELETE FROM blog WHERE blog_id={}".format(id))
	mysql.connection.commit()
	flash('Blog Deleted Successfully !!', 'success')
	return redirect('/')

@app.route('/logout/')
def logout():
	session.clear()
	flash("Logged Out Successfully", "warning")
	return redirect('/')

if __name__ == '__main__':
	app.run(debug=True)
