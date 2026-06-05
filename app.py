import os
import sqlite3
from functools import wraps
from flask import Flask, request, redirect, url_for, render_template, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# File parsing imports
import pdfplumber
import docx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = 'super_secret_resume_screening_key_change_me_in_prod'

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

DATABASE = os.path.join(app.root_path, 'database.db')

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        # Create users table
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('candidate', 'recruiter')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
def insert_sample_jobs():
    with app.app_context():
        db = get_db()

        # Check if jobs already exist
        existing_jobs = db.execute(
            "SELECT COUNT(*) as total FROM jobs"
        ).fetchone()["total"]

        # Check if recruiter exists
        recruiter = db.execute(
            "SELECT id FROM users WHERE role='recruiter' LIMIT 1"
        ).fetchone()

        if existing_jobs == 0 and recruiter:
            recruiter_id = recruiter["id"]

            sample_jobs = [
                ("Python Developer", "Infosys", "Bangalore", "Develop and maintain Flask applications.", "Python, Flask, SQL"),
                ("Full Stack Developer", "TCS", "Hyderabad", "Work on frontend and backend systems.", "Python, React, MySQL"),
                ("Data Scientist", "Wipro", "Pune", "Build machine learning models.", "Python, Pandas, Machine Learning"),
                ("Frontend Developer", "Accenture", "Mumbai", "Create responsive web interfaces.", "HTML, CSS, JavaScript, React"),
                ("Backend Developer", "HCL", "Noida", "Develop APIs and backend services.", "Python, Flask, PostgreSQL"),
                ("Machine Learning Engineer", "IBM", "Bangalore", "Design and deploy ML systems.", "Python, TensorFlow, NLP"),
                ("DevOps Engineer", "Capgemini", "Chennai", "Manage CI/CD and cloud deployments.", "Docker, Kubernetes, AWS"),
                ("Cloud Engineer", "Amazon", "Remote", "Deploy and maintain cloud infrastructure.", "AWS, Linux, Terraform"),
                ("Cyber Security Analyst", "Tech Mahindra", "Delhi", "Monitor and improve security systems.", "Security, SIEM, Networking"),
                ("AI Engineer", "OpenAI Labs", "Remote", "Develop AI-powered applications.", "Python, LLM, Machine Learning")
            ]

            for title, company, location, description, requirements in sample_jobs:
                db.execute("""
                    INSERT INTO jobs
                    (recruiter_id, title, company, location, description, requirements)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    recruiter_id,
                    title,
                    company,
                    location,
                    description,
                    requirements
                ))

            db.commit()
            print("10 sample jobs inserted successfully.")        
        # Create jobs table
        db.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recruiter_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                description TEXT NOT NULL,
                requirements TEXT,
                location TEXT NOT NULL,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recruiter_id) REFERENCES users (id)
            )
        ''')
        # Create applications table
        db.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                candidate_id INTEGER NOT NULL,
                resume_filename TEXT NOT NULL,
                match_score REAL DEFAULT 0.0,
                parsed_text TEXT,
                status TEXT NOT NULL DEFAULT 'Applied' CHECK(status IN ('Applied', 'Reviewed', 'Shortlisted', 'Rejected')),
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs (id),
                FOREIGN KEY (candidate_id) REFERENCES users (id)
            )
        ''')
        db.commit()


# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') != role:
                flash('You do not have permission to view this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Resume parsers
def extract_text_from_pdf(filepath):
    text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error parsing PDF: {e}")
    return text


def extract_text_from_docx(filepath):
    text = ""
    try:
        doc = docx.Document(filepath)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error parsing DOCX: {e}")
    return text


def calculate_match_score(resume_text, job_requirements, job_description):
    if not resume_text:
        return 0.0
    
    # 1. TF-IDF Similarity
    job_text = f"{job_requirements} {job_description}"
    vectorizer = TfidfVectorizer(stop_words='english')
    try:
        tfidf = vectorizer.fit_transform([job_text, resume_text])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])
        tfidf_score = float(similarity[0][0]) * 100
    except Exception as e:
        tfidf_score = 0.0

    # 2. Key requirements checking (boost score for matching key skills)
    req_score = 0.0
    if job_requirements:
        keywords = [k.strip().lower() for k in job_requirements.split(',') if k.strip()]
        if keywords:
            found = 0
            resume_lower = resume_text.lower()
            for kw in keywords:
                if kw in resume_lower:
                    found += 1
            req_score = (found / len(keywords)) * 100

    # Composite score
    if job_requirements:
        final_score = (tfidf_score * 0.4) + (req_score * 0.6)
    else:
        final_score = tfidf_score
        
    return min(100.0, round(final_score, 1))


# Routes
@app.route('/')
def index():
    db = get_db()
    jobs = db.execute('''
        SELECT jobs.*, users.username as recruiter_name 
        FROM jobs JOIN users ON jobs.recruiter_id = users.id 
        ORDER BY posted_at DESC LIMIT 6
    ''').fetchall()
    return render_template('index.html', jobs=jobs)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        role = request.form['role']
        
        if not username or not email or not password or not role:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
            
        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)',
                (username, email, generate_password_hash(password), role)
            )
            db.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or Email already exists.', 'danger')
            
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        
        if not email or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('login.html')
            
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    if session['role'] == 'recruiter':
        # Get jobs posted by this recruiter
        jobs = db.execute(
            'SELECT * FROM jobs WHERE recruiter_id = ? ORDER BY posted_at DESC',
            (session['user_id'],)
        ).fetchall()
        
        # Get count of applicants per job
        jobs_with_counts = []
        for job in jobs:
            count = db.execute(
                'SELECT COUNT(*) as count FROM applications WHERE job_id = ?',
                (job['id'],)
            ).fetchone()['count']
            
            # Convert row to dict to append dynamic attributes
            job_dict = dict(job)
            job_dict['applicant_count'] = count
            jobs_with_counts.append(job_dict)
            
        return render_template('recruiter_dashboard.html', jobs=jobs_with_counts)
    else:
        # Candidate dashboard - show jobs applied to
        applications = db.execute('''
            SELECT applications.*, jobs.title, jobs.company, jobs.location 
            FROM applications 
            JOIN jobs ON applications.job_id = jobs.id 
            WHERE applications.candidate_id = ? 
            ORDER BY applications.applied_at DESC
        ''', (session['user_id'],)).fetchall()
        
        return render_template('candidate_dashboard.html', applications=applications)


@app.route('/jobs')
def jobs():
    search = request.args.get('search', '').strip()
    location = request.args.get('location', '').strip()
    
    db = get_db()
    query = '''
        SELECT jobs.*, users.username as recruiter_name 
        FROM jobs JOIN users ON jobs.recruiter_id = users.id
    '''
    params = []
    
    if search or location:
        query += ' WHERE'
        conditions = []
        if search:
            conditions.append('(jobs.title LIKE ? OR jobs.company LIKE ? OR jobs.description LIKE ?)')
            params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
        if location:
            conditions.append('jobs.location LIKE ?')
            params.append(f'%{location}%')
        query += ' ' + ' AND '.join(conditions)
        
    query += ' ORDER BY posted_at DESC'
    jobs = db.execute(query, params).fetchall()
    return render_template('jobs.html', jobs=jobs, search=search, location=location)


@app.route('/job/<int:job_id>')
def job_detail(job_id):
    db = get_db()
    job = db.execute('''
        SELECT jobs.*, users.username as recruiter_name 
        FROM jobs JOIN users ON jobs.recruiter_id = users.id 
        WHERE jobs.id = ?
    ''', (job_id,)).fetchone()
    
    if not job:
        flash('Job not found.', 'danger')
        return redirect(url_for('jobs'))
        
    has_applied = False
    application = None
    if 'user_id' in session and session['role'] == 'candidate':
        application = db.execute(
            'SELECT * FROM applications WHERE job_id = ? AND candidate_id = ?',
            (job_id, session['user_id'])
        ).fetchone()
        if application:
            has_applied = True
            
    return render_template('job_detail.html', job=job, has_applied=has_applied, application=application)


@app.route('/post-job', methods=['GET', 'POST'])
@role_required('recruiter')
def post_job():
    if request.method == 'POST':
        title = request.form['title'].strip()
        company = request.form['company'].strip()
        location = request.form['location'].strip()
        description = request.form['description'].strip()
        requirements = request.form['requirements'].strip()
        
        if not title or not company or not location or not description:
            flash('Please fill in all required fields.', 'danger')
            return render_template('post_job.html')
            
        db = get_db()
        db.execute('''
            INSERT INTO jobs (recruiter_id, title, company, location, description, requirements)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], title, company, location, description, requirements))
        db.commit()
        
        flash('Job posted successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('post_job.html')


@app.route('/apply/<int:job_id>', methods=['POST'])
@role_required('candidate')
def apply_job(job_id):
    db = get_db()
    job = db.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    if not job:
        flash('Job not found.', 'danger')
        return redirect(url_for('jobs'))
        
    # Check if already applied
    already_applied = db.execute(
        'SELECT id FROM applications WHERE job_id = ? AND candidate_id = ?',
        (job_id, session['user_id'])
    ).fetchone()
    
    if already_applied:
        flash('You have already applied for this job.', 'warning')
        return redirect(url_for('job_detail', job_id=job_id))
        
    if 'resume' not in request.files:
        flash('No file uploaded.', 'danger')
        return redirect(url_for('job_detail', job_id=job_id))
        
    file = request.files['resume']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('job_detail', job_id=job_id))
        
    if file and allowed_file(file.filename):
        # Create a unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        new_filename = f"resume_{session['user_id']}_{job_id}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(filepath)
        
        # Parse text from resume
        resume_text = ""
        if ext == 'pdf':
            resume_text = extract_text_from_pdf(filepath)
        elif ext == 'docx':
            resume_text = extract_text_from_docx(filepath)
            
        # Calculate matching score
        match_score = calculate_match_score(
            resume_text, 
            job['requirements'], 
            job['description']
        )
        
        # Save to database
        db.execute('''
            INSERT INTO applications (job_id, candidate_id, resume_filename, match_score, parsed_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (job_id, session['user_id'], new_filename, match_score, resume_text))
        db.commit()
        
        flash(f'Application submitted successfully! Your Resume Match Score is: {match_score}%', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid file format. Please upload PDF or DOCX only.', 'danger')
        return redirect(url_for('job_detail', job_id=job_id))


@app.route('/job/<int:job_id>/applications')
@role_required('recruiter')
def job_applications(job_id):
    db = get_db()
    # Check if this recruiter owns this job
    job = db.execute(
        'SELECT * FROM jobs WHERE id = ? AND recruiter_id = ?',
        (job_id, session['user_id'])
    ).fetchone()
    
    if not job:
        flash('Unauthorized or job not found.', 'danger')
        return redirect(url_for('dashboard'))
        
    # Get all applications for this job
    applications = db.execute('''
        SELECT applications.*, users.username, users.email 
        FROM applications 
        JOIN users ON applications.candidate_id = users.id 
        WHERE applications.job_id = ? 
        ORDER BY applications.match_score DESC
    ''', (job_id,)).fetchall()
    
    return render_template('job_applications.html', job=job, applications=applications)


@app.route('/application/<int:app_id>/status', methods=['POST'])
@role_required('recruiter')
def update_status(app_id):
    status = request.form.get('status')
    if status not in ['Applied', 'Reviewed', 'Shortlisted', 'Rejected']:
        flash('Invalid status choice.', 'danger')
        return redirect(url_for('dashboard'))
        
    db = get_db()
    
    # Ensure this recruiter owns the job of the application
    app_info = db.execute('''
        SELECT applications.id, jobs.recruiter_id, applications.job_id 
        FROM applications 
        JOIN jobs ON applications.job_id = jobs.id 
        WHERE applications.id = ?
    ''', (app_id,)).fetchone()
    
    if not app_info or app_info['recruiter_id'] != session['user_id']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('dashboard'))
        
    db.execute('UPDATE applications SET status = ? WHERE id = ?', (status, app_id))
    db.commit()
    
    flash(f'Application status updated to {status}!', 'success')
    return redirect(url_for('job_applications', job_id=app_info['job_id']))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
