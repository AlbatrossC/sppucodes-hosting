from flask import Flask, render_template, send_from_directory, abort, request, redirect, url_for, flash
import os
import psycopg2
from psycopg2 import pool
from flask_caching import Cache
from flask_compress import Compress

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'karlos'

# Initialize caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Initialize compression
Compress(app)

# Database connection pool
DATABASE_URL = os.getenv("DATABASE_URL")
connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URL
)

def get_db_connection():
    """Get a connection from the connection pool."""
    return connection_pool.getconn()

def return_db_connection(conn):
    """Return a connection to the connection pool."""
    connection_pool.putconn(conn)

@app.route('/submit', methods=["GET", "POST"])
def submit():
    """Handle form submission."""
    conn = get_db_connection()
    if conn is None:
        return "Database Connection error. Please try again later"

    if request.method == "POST":
        try:
            cur = conn.cursor()

            name = request.form.get("name")
            year = request.form.get("year")
            branch = request.form.get("branch")
            subject = request.form.get("subject")
            question = request.form.get("question")
            answer = request.form.get("answer")

            if name and year and branch and subject and question and answer:
                cur.execute("INSERT INTO codes (name, year, branch, subject, question, answer) VALUES (%s,%s,%s,%s,%s,%s)",
                            (name, year, branch, subject, question, answer))
                conn.commit()
                flash("Code Sent Successfully! Thank you", "success")
                return redirect(url_for('submit'))
            else:
                flash("PLEASE FILL ALL NECESSARY FIELDS", "error")

            cur.close()
        except Exception as e:
            flash(f"Error inserting data: {e}", "error")
        finally:
            return_db_connection(conn)

    return render_template("submit.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    """Handle contact form submission."""
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        if name and email and message:
            try:
                conn = get_db_connection()
                if conn is None:
                    flash("Database connection error. Please try again later.", "error")
                    return redirect(url_for('contact'))

                cur = conn.cursor()
                cur.execute("INSERT INTO contacts (name, email, message) VALUES (%s, %s, %s)", 
                            (name, email, message))
                conn.commit()
                cur.close()
                return_db_connection(conn)
                
                flash("Message sent successfully! Thank you", "success")
            except Exception as e:
                flash(f"Error inserting data: {e}", "error")
            return redirect(url_for('contact'))
        else:
            flash("PLEASE FILL ALL NECESSARY FIELDS", "error")
            
    return render_template("contact.html")

@app.route('/')
@cache.cached(timeout=50)  # Cache the index page for 50 seconds
def index():
    """Render the home page."""
    return render_template('index.html')

# For Downloading codes
downloads_folder = os.path.join(app.root_path, 'downloads')

@app.route('/download')
def download():
    """Render the download page."""
    return render_template('download.html')

@app.route('/downloads/<filename>')
def download_file(filename):
    """Serve files from the downloads folder."""
    return send_from_directory(downloads_folder, filename)

@app.route('/<subject_name>')
def subject(subject_name):
    """Render subject-specific pages."""
    try:
        return render_template(f'subjects/{subject_name}.html')
    except Exception:
        return render_template("error.html")

@app.route('/<subject>/<filename>')
def get_answer(subject, filename):
    """Serve answer files for a subject."""
    try:      
        base_dir = os.path.abspath(os.path.dirname(__file__))
        answers_dir = os.path.join(base_dir, 'answers', subject)

        if not os.path.exists(answers_dir):
            abort(404)

        full_path = os.path.join(answers_dir, filename)
        if not os.path.exists(full_path):
            abort(404)
            
        return send_from_directory(answers_dir, filename)
    except Exception:
        abort(404)

@app.route('/disclaimer')
def disclaimer():
    """Render the disclaimer page."""
    return render_template('disclaimer.html')

@app.route('/copy')
def copy():
    """Render the copy page."""
    return render_template('copy.html')

@app.route('/images/<filename>')
def get_image(filename):
    """Serve images."""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    images_dir = os.path.join(base_dir, 'images')
    return send_from_directory(images_dir, filename)

@app.route('/sitemap.xml')
def sitemap():
    """Serve the sitemap."""
    return send_from_directory('.', 'sitemap.xml')

@app.route('/robots.txt')
def robots():
    """Serve the robots.txt file."""
    return send_from_directory('.', 'robots.txt')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int("3000"), debug=True)