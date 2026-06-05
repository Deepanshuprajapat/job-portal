# 🚀 AI Resume Screening & Job Portal System

A modern Flask-based Job Portal and AI Resume Screening System that helps recruiters post jobs, manage applications, and automatically evaluate candidate resumes using Machine Learning techniques.

## 📌 Features

### 👨‍💼 Recruiter Features

* Recruiter Registration & Login
* Post New Job Openings
* View Posted Jobs
* Manage Job Applications
* Shortlist or Reject Candidates
* Track Applicant Status

### 👨‍🎓 Candidate Features

* Candidate Registration & Login
* Browse Available Jobs
* Search Jobs by Title & Location
* Apply for Jobs
* Upload Resume (PDF/DOCX)
* Track Application Status

### 🤖 AI Resume Screening

* Resume Parsing from PDF and DOCX files
* TF-IDF Based Resume Analysis
* Cosine Similarity Matching
* Automatic Resume Match Score Generation
* Skill-Based Resume Ranking

### 🔒 Security Features

* Password Hashing using Werkzeug
* Session-Based Authentication
* Role-Based Access Control
* Secure File Upload Handling

---

## 🛠️ Tech Stack

### Backend

* Python
* Flask
* SQLite

### Machine Learning

* Scikit-Learn
* TF-IDF Vectorizer
* Cosine Similarity

### Frontend

* HTML5
* CSS3
* JavaScript
* Jinja2 Templates

### Resume Processing

* PDFPlumber
* Python-Docx

---

## 📂 Project Structure

```text
job-portal/
│
├── static/
│   ├── css/
│   ├── uploads/
│   └── assets/
│
├── templates/
│   ├── index.html
│   ├── jobs.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── post_job.html
│   └── ...
│
├── database.db
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/Deepanshuprajapat/job-portal.git
cd job-portal
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Environment

Windows:

```bash
venv\Scripts\activate
```

Linux / Mac:

```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run Application

```bash
python app.py
```

### 6. Open Browser

```text
http://127.0.0.1:5000
```

---

## 📊 Resume Matching Process

1. Candidate uploads Resume
2. Resume text is extracted
3. Job description and requirements are processed
4. TF-IDF vectorization is applied
5. Cosine similarity score is calculated
6. Skills are matched with requirements
7. Final Resume Match Score is generated

---

## 🎯 Future Enhancements

* Email Notifications
* Interview Scheduling
* AI Chatbot Assistant
* Resume Suggestions
* Job Recommendations
* Admin Dashboard
* Multi-Company Support
* Advanced Analytics
* JWT Authentication
* PostgreSQL Integration

---

## 📸 Screenshots

Add screenshots of:

* Home Page
* Job Listings
* Recruiter Dashboard
* Candidate Dashboard
* Resume Match Score
* Job Application Page

---

## 👨‍💻 Author

**Deepanshu Prajapati**

* GitHub: https://github.com/Deepanshuprajapat
* LinkedIn: https://www.linkedin.com/in/deepanshu-prajapat-04769a30a

---

## 📄 License

This project is developed for educational and learning purposes.

⭐ If you like this project, don't forget to star the repository.
