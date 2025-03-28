from flask import Flask, render_template, send_from_directory, abort, request, redirect, url_for, flash, jsonify
import os
import psycopg2
import json
import requests
from datetime import datetime
from hosting.quecount import quecount_bp

app = Flask(__name__)
app.secret_key = 'karlos'

# Root directory containing the pyqs
BASE_DIR = os.path.join(os.path.dirname(__file__), 'static', 'pyqs')

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent'

@app.route('/questionpapers')
def select():
    # Render the select page at the sub-URL
    return render_template('select.html')

@app.route('/api/directories')
def get_directories():
    path = request.args.get('path', '')
    # Remove 'pyqs/' prefix if present
    if path.startswith('pyqs/'):
        path = path[len('pyqs/'):]
    full_path = os.path.join(BASE_DIR, path)
    
    if not os.path.exists(full_path):
        print(f"Path does not exist: {full_path}")  # Debug
        return jsonify([])
    
    if os.path.isdir(full_path):
        items = os.listdir(full_path)
        print(f"Items in {full_path}: {items}")  # Debug
        if any(item.lower().endswith('.pdf') for item in items):
            files = [f for f in items if f.lower().endswith('.pdf')]
            return jsonify(files)
        else:
            directories = [d for d in items if os.path.isdir(os.path.join(full_path, d))]
            return jsonify(directories)
    return jsonify([])

@app.route('/viewer')
def viewer():
    pdf_path = request.args.get('pdf')
    return render_template('viewer.html', pdf_path=pdf_path)

@app.route('/static/pyqs/<path:filename>')
def serve_pdf(filename):
    return send_from_directory(BASE_DIR, filename)

# Register the quecount blueprint
app.register_blueprint(quecount_bp)
DATABASE_URL = os.getenv("DATABASE_URL")

# Database connection function
def connect_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Custom Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html'), 500

# Route for submitting codes
@app.route('/submit', methods=["GET", "POST"])
def submit():
    conn = connect_db()
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
            conn.close()

    return render_template("submit.html")

# Route for contact form
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")  # Changed from "msg" to "message"

        if name and email and message:
            try:
                conn = connect_db()
                if conn is None:
                    flash("Database connection error. Please try again later.", "error")
                    return redirect(url_for('contact'))

                cur = conn.cursor()
                cur.execute("INSERT INTO contacts (name, email, message) VALUES (%s, %s, %s)", 
                          (name, email, message))
                conn.commit()
                cur.close()
                conn.close()
                
                flash("Message sent successfully! Thank you", "success")
            except Exception as e:
                flash(f"Error inserting data: {e}", "error")
            return redirect(url_for('contact'))
        else:
            flash("PLEASE FILL ALL NECESSARY FIELDS", "error")
            
    return render_template("contact.html")

# Home route
@app.route('/')
def index():
    return render_template('index.html')

# Route for downloading codes
downloads_folder = os.path.join(app.root_path, 'downloads')

@app.route('/download')
def download():
    return render_template('download.html')

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory(downloads_folder, filename)

# Route for serving questions
QUESTIONS_DIR = os.path.join(os.path.dirname(__file__), 'questions')

@app.route("/<subject_code>")
@app.route("/<subject_code>/<question_id>")
def question(subject_code, question_id=None):
    # Construct the path to the JSON file
    json_file_path = os.path.join(QUESTIONS_DIR, f"{subject_code}.json")
    
    # Check if the JSON file exists
    if not os.path.exists(json_file_path):
        abort(404, description="Subject not found")

    # Load the JSON data
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    subject = data.get("default", {})
    questions = data.get("questions", [])

    # Convert questions list to a dictionary for O(1) access
    question_dict = {q["id"]: q for q in questions}

    # Default metadata for subject page
    title = f"SPPU Codes - {subject.get('subject_name', '')}"
    description = subject.get("description", "")
    keywords = subject.get("keywords", [])
    url = subject.get("url", f"https://sppucodes.vercel.app/{subject_code}")

    selected_question = question_dict.get(question_id) if question_id else None

    if selected_question:
        title = selected_question["question"]
        description = f"SPPU Codes: {selected_question['question']}"
        keywords = [selected_question["question"], selected_question["title"]] + subject.get("keywords", [])
        url = f"https://sppucodes.vercel.app/{subject_code}/{question_id}"

    # Organize questions by group for FAQ display
    groups = {}
    for q in questions:
        groups.setdefault(q["group"], []).append(q)

    return render_template(
        "subject.html",
        title=title,
        description=description,
        keywords=keywords,
        url=url,
        subject_code=subject_code,
        subject_name=subject.get("subject_name", ""),
        groups=groups,
        sorted_groups=sorted(groups.keys()),
        question=selected_question
    )

# Route for serving answers
@app.route('/answers/<subject>/<filename>')
def get_answer(subject, filename):
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

# New endpoint to proxy Gemini API requests
@app.route('/api/explain-code', methods=['POST'])
def explain_code():
    if not GEMINI_API_KEY:
        return jsonify({"error": "API key not configured"}), 500

    data = request.get_json()
    instruction = data.get('instruction')
    question = data.get('question')
    code_text = data.get('codeText', '')

    if not instruction or not question:
        return jsonify({"error": "Missing instruction or question"}), 400

    # Prepare the request body for Gemini API
    request_body = {
        "contents": [{
            "parts": [
                {"text": instruction},
                {"text": f"Question: {question}\n\nCode:\n{code_text}" if code_text else f"Question: {question}"}
            ]
        }]
    }

    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json=request_body
        )
        response.raise_for_status()
        response_data = response.json()
        explanation = response_data['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"explanation": explanation})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route for disclaimer page
@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')

# Route for copy page
@app.route('/copy')
def copy():
    return render_template('copy.html')

# Route for serving images
@app.route('/images/<filename>')
def get_image(filename):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    images_dir = os.path.join(base_dir, 'images')
    return send_from_directory(images_dir, filename)

# Route for sitemap
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('.', 'sitemap.xml')

# Route for robots.txt
@app.route('/robots.txt')
def robots():
    return send_from_directory('.', 'robots.txt')

@app.route('/79107a527a7f49eca3699d19f4f83224.txt')
def verify():
    return send_from_directory('.', '79107a527a7f49eca3699d19f4f83224.txt')

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int("3000"), debug=True)