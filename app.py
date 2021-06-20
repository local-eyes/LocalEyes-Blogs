from flask import Flask, render_template, request, flash, redirect, session, jsonify
from flask_bootstrap import Bootstrap
from flask_mysqldb import MySQL
from flask_ckeditor import CKEditor
from werkzeug.security import generate_password_hash as passgen
from werkzeug.security import check_password_hash as passcheck
from yaml import load, FullLoader
import os
import random 

app = Flask(__name__)
print(os.environ['LocalEyesAdminKey'])

# Ad-On Enablers 
Bootstrap(app)
CKEditor(app)
mysql = MySQL(app)

# MySQL Database Configuration
db = load(open('db.yaml'), Loader=FullLoader)
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']
app.config['CURSORCLASS'] = 'DictCursor'
app.config['SECRET_KEY'] = os.urandom(24)


@app.route('/')
def index():
	cur = mysql.connection.cursor()
	allblogs = cur.execute("SELECT * FROM blog;")
	if allblogs > 0:
		blogs = cur.fetchall()
		cur.close()
		return render_template('index.html', blogs=blogs)
	cur.close()
	return render_template('index.html', blogs=None)

@app.route('/admin/register/', methods=['GET', 'POST'])
def register():
	if request.method == 'POST':
		details = request.form
		if details['admin_key'] == os.environ['LocalEyesAdminKey']:
			fullname = details['fullname']
			password = passgen(details['password'])
			role = "Content Writer"
			verified = False
			identifier = str(fullname).replace(' ', '.').lower()
			cur = mysql.connection.cursor()
			cur.execute("INSERT INTO authors(fullname, password, role, identifier, verified) VALUES(%s, %s, %s, %s, %b);", (fullname, password, role, identifier, verified))
			mysql.connection.commit()
			cur.close()
			flash(f"ACCOUNT CREATION SUCCESSFULL. Welcome to LocalEyes {fullname}", "success")
			return redirect('/')
		else:
			flash("You are not authorized to create a Writer Account at LocalEyes.", "danger")
	return render_template('login.html')

@app.route('/admin/login/', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		cur = mysql.connection.cursor()
		details = request.form
		identifier = details['username']
		result = cur.execute("SELECT * FROM authors WHERE identifier='{}';".format(identifier))
		if result > 0:
			author = cur.fetchone()
			check_pass = passcheck(author[2], details['password'])
			if check_pass:
				session['logged_in'] = True
				session['author']
		else:
			flash("User does not exist", "danger")
	return render_template("login.html")

@app.route('/author/<identifier>')
def author(identifier):
	cur = mysql.connection.cursor()
	res = cur.execute("SELECT * FROM authors WHERE identifier='{}';".format(identifier))
	if res > 0:
		author = cur.fetchone()
		return jsonify({"result": author})
	else:
		return "No Such Author"

@app.route('/blog/<int:id>/')
def blogs(id):
	cur = mysql.connection.cursor()
	resultBlog = cur.execute("SELECT * FROM blog WHERE blog_id={}".format(id))
	if resultBlog > 0:
		blog = cur.fetchone()
		return render_template('blogs.html', blogs=blog)
	return "Blog Not Found"

@app.route('/write-blog/', methods=['GET', 'POST'])
def write_blog():
	if request.method == 'POST':
		blogpost = request.form
		title = blogpost['title']
		body = blogpost['body']
		category = blogpost['category']
		author = session['first_name'] + ' ' + session['last_name']

		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO blog(title, body, author, category) VALUES(%s, %s, %s, %s);", (title, body, author, category))
		mysql.connection.commit()
		cur.close()
		flash('Blog Posted Successfully', 'success')
		return redirect('/')
	return render_template('write-blog.html')

@app.route('/my-blogs/')
def my_blogs():
	author = session['first_name'] + ' ' + session['last_name']
	cur = mysql.connection.cursor()
	resultBlog = cur.execute("SELECT * FROM blog WHERE author=%s", [author])
	if resultBlog > 0:
		my_blogs = cur.fetchall()
		return render_template('my-blogs.html', my_blogs=my_blogs)
	else:
		return render_template('my-blogs.html', my_blogs=None)

@app.route('/categories')
def categories():
	cur = mysql.connection.cursor()
	if request.args:
		category = str(request.args.get('q')).upper()
		res = cur.execute("SELECT * FROM blog WHERE category='{}';".format(category))
		if res > 0:
			blogs = cur.fetchall()
			return jsonify({"result" : blogs})
		else:
			return "No Blogs of such category"
	else :
		res = cur.execute("SELECT * FROM blog ORDER BY category")
		if res > 0:
			blogs = cur.fetchall()
			return jsonify({"result" : blogs})
		else:
			return "No Blogs found"


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

if __name__ == '__main__':
	app.run(debug=True)
