from flask import Flask, render_template, send_from_directory, abort, request, redirect, url_for, flash, make_response
from flask_caching import Cache
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import psycopg2
from functools import wraps
import gzip
import hashlib
from datetime import datetime, timedelta
from hosting.quecount import quecount_bp

# App configuration
app = Flask(__name__)
app.secret_key = 'karlos'
app.wsgi_app = ProxyFix(app.wsgi_app)

# Cache configuration
cache_config = {
    'CACHE_TYPE': 'filesystem',  # Using filesystem cache
    'CACHE_DIR': 'flask_cache',  # Cache directory
    'CACHE_DEFAULT_TIMEOUT': 300,  # Default timeout in seconds
    'CACHE_THRESHOLD': 1000,  # Maximum number of items in cache
    'CACHE_OPTIONS': {
        'mode': 384  # File mode for cache files
    }
}
app.config.from_mapping(cache_config)
cache = Cache(app)

# Register blueprint
app.register_blueprint(quecount_bp)

DATABASE_URL = os.getenv("DATABASE_URL")

# Database connection pool
def get_db_pool():
    return psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=20,
        dsn=DATABASE_URL
    )

db_pool = get_db_pool()

def get_db():
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)

# Compression middleware
def gzip_response(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        if not request.path.endswith(('.png', '.jpg', '.gif')):
            accept_encoding = request.headers.get('Accept-Encoding', '')
            if 'gzip' in accept_encoding:
                response.data = gzip.compress(response.data)
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Vary'] = 'Accept-Encoding'
                response.headers['Content-Length'] = len(response.data)
        return response
    return wrapped

# Generate ETag for file caching
def generate_etag(filename):
    file_stat = os.stat(filename)
    return hashlib.md5(f"{filename}{file_stat.st_mtime}{file_stat.st_size}".encode()).hexdigest()

@app.route('/submit', methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        try:
            with next(get_db()) as conn:
                cur = conn.cursor()
                
                form_data = {
                    'name': request.form.get("name"),
                    'year': request.form.get("year"),
                    'branch': request.form.get("branch"),
                    'subject': request.form.get("subject"),
                    'question': request.form.get("question"),
                    'answer': request.form.get("answer")
                }

                if all(form_data.values()):
                    cur.execute("""
                        INSERT INTO codes (name, year, branch, subject, question, answer) 
                        VALUES (%(name)s, %(year)s, %(branch)s, %(subject)s, %(question)s, %(answer)s)
                    """, form_data)
                    conn.commit()
                    flash("Code Sent Successfully! Thank you", "success")
                    cache.delete_memoized('get_codes')
                    return redirect(url_for('submit'))
                else:
                    flash("PLEASE FILL ALL NECESSARY FIELDS", "error")
        except Exception as e:
            flash(f"Error inserting data: {e}", "error")

    return render_template("submit.html")

@app.route("/contact", methods=["GET", "POST"])
@gzip_response
def contact():
    if request.method == "POST":
        form_data = {
            'name': request.form.get("name"),
            'email': request.form.get("email"),
            'message': request.form.get("message")
        }

        if all(form_data.values()):
            try:
                with next(get_db()) as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO contacts (name, email, message) 
                        VALUES (%(name)s, %(email)s, %(message)s)
                    """, form_data)
                    conn.commit()
                flash("Message sent successfully! Thank you", "success")
            except Exception as e:
                flash(f"Error inserting data: {e}", "error")
            return redirect(url_for('contact'))
        else:
            flash("PLEASE FILL ALL NECESSARY FIELDS", "error")
            
    return render_template("contact.html")

@app.route('/')
@cache.cached(timeout=300)  # Cache for 5 minutes
@gzip_response
def index():
    return render_template('index.html')

@app.route('/download')
@cache.cached(timeout=3600)  # Cache for 1 hour
@gzip_response
def download():
    return render_template('download.html')

@app.route('/downloads/<filename>')
def download_file(filename):
    downloads_folder = os.path.join(app.root_path, 'downloads')
    file_path = os.path.join(downloads_folder, filename)
    
    if not os.path.exists(file_path):
        abort(404)
        
    etag = generate_etag(file_path)
    if request.if_none_match and etag in request.if_none_match:
        return '', 304
        
    response = send_from_directory(downloads_folder, filename)
    response.headers['ETag'] = etag
    response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
    return response

@app.route('/<subject_name>')
@cache.memoize(timeout=3600)  # Cache for 1 hour
@gzip_response
def subject(subject_name):
    try:
        return render_template(f'subjects/{subject_name}.html')
    except Exception:
        return render_template("error.html")

@app.route('/<subject>/<filename>')
def get_answer(subject, filename):
    try:      
        base_dir = os.path.abspath(os.path.dirname(__file__))
        answers_dir = os.path.join(base_dir, 'answers', subject)

        if not os.path.exists(answers_dir):
            abort(404)

        file_path = os.path.join(answers_dir, filename)
        if not os.path.exists(file_path):
            abort(404)
            
        etag = generate_etag(file_path)
        if request.if_none_match and etag in request.if_none_match:
            return '', 304
            
        response = send_from_directory(answers_dir, filename)
        response.headers['ETag'] = etag
        response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
        return response
    except Exception:
        abort(404)

@app.route('/disclaimer')
@cache.cached(timeout=86400)  # Cache for 24 hours
@gzip_response
def disclaimer():
    return render_template('disclaimer.html')

@app.route('/copy')
@cache.cached(timeout=86400)  # Cache for 24 hours
@gzip_response
def copy():
    return render_template('copy.html')

@app.route('/images/<filename>')
def get_image(filename):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    images_dir = os.path.join(base_dir, 'images')
    
    file_path = os.path.join(images_dir, filename)
    if not os.path.exists(file_path):
        abort(404)
        
    etag = generate_etag(file_path)
    if request.if_none_match and etag in request.if_none_match:
        return '', 304
        
    response = send_from_directory(images_dir, filename)
    response.headers['ETag'] = etag
    response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
    return response

@app.route('/sitemap.xml')
@cache.cached(timeout=86400)  # Cache for 24 hours
def sitemap():
    return send_from_directory('.', 'sitemap.xml')

@app.route('/robots.txt')
@cache.cached(timeout=86400)  # Cache for 24 hours
def robots():
    return send_from_directory('.', 'robots.txt')

@app.errorhandler(404)
@cache.cached(timeout=3600)  # Cache for 1 hour
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
@cache.cached(timeout=3600)  # Cache for 1 hour
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int("3000"), debug=False)