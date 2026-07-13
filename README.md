# 🎓 ExamGuard-AI

### AI-Powered Secure Online Examination & Proctoring Platform

ExamGuard-AI is a secure online examination platform designed to conduct academic assessments with real-time AI-based proctoring, automated violation detection, and comprehensive exam management. It provides separate portals for administrators, teachers, and students while maintaining the integrity of online examinations through continuous monitoring and forensic-ready audit logs.

---

## 🚀 Features

### 👨‍💼 Admin Dashboard

* Manage students, teachers, and classrooms
* Create, schedule, and publish examinations
* Monitor ongoing examinations in real time
* View examination analytics and reports
* Generate downloadable result reports

### 👨‍🏫 Faculty Dashboard

* Create and manage question banks
* Conduct secure online examinations
* View student performance statistics
* Monitor live examination sessions
* Review examination violations

### 👨‍🎓 Student Portal

* Secure login with authentication
* Join scheduled examinations
* Full-screen examination environment
* Automatic submission on timeout
* View examination history and results

---

## 🛡️ AI-Based Proctoring

ExamGuard-AI continuously monitors students during examinations using computer vision and browser activity tracking.

### Supported Violation Detection

* Multiple face detection
* Face not detected
* Head movement detection
* Looking away from the screen
* Tab switching detection
* Window minimization
* Full-screen exit detection
* Browser focus loss
* Camera disconnection alerts

Every violation is timestamped and stored for later review.

---

## 📊 Dashboard Analytics

The dashboard provides real-time insights, including:

* Total Students
* Active Exams
* Live Examination Sessions
* Today's Violations
* Average Student Score
* Pass vs Fail Statistics
* Monthly Examination Trends
* Recent Examination Activity

---

## 📚 Question Bank

* Create subject-wise question banks
* Support for multiple-choice questions
* Difficulty level categorization
* Randomized question selection
* Reusable question collections

---

## 📝 Examination Management

* Create examinations
* Schedule examination dates
* Configure duration
* Set start and end times
* Automatic submission
* Negative marking support
* Randomized question order
* Result generation

---

## 👥 User Roles

### Administrator

* Manage users
* Manage classrooms
* Monitor examinations
* Access reports
* Configure platform settings

### Faculty

* Create examinations
* Upload questions
* Monitor students
* Evaluate results

### Student

* Attempt examinations
* View results
* Access examination history

---

## 🔐 Security Features

* JWT Authentication
* Role-Based Access Control (RBAC)
* Secure Password Hashing
* Session Timeout Protection
* Refresh Token Support
* Protected API Endpoints
* Rate Limiting
* Secure Environment Variables
* CSRF Protection
* SQL Injection Prevention
* Input Validation
* Audit Logging

---

## 🖥️ Live Monitoring

Administrators can monitor ongoing examinations through a live dashboard displaying:

* Student status
* Camera status
* Full-screen status
* Active violations
* Examination progress
* Online participants

---

## 📈 Reports & Analytics

Generate reports for:

* Student performance
* Examination statistics
* Violation history
* Attendance reports
* Classroom performance
* Faculty performance

---

## 🛠️ Tech Stack

### Frontend

* HTML5
* CSS3
* JavaScript
* Bootstrap
* Chart.js

### Backend

* Flask
* Flask-JWT-Extended
* Flask-SocketIO
* SQLAlchemy

### Database

* PostgreSQL

### AI & Computer Vision

* OpenCV
* MediaPipe

### Authentication

* JWT Authentication
* Session Management

### Deployment & DevOps

* Git
* GitHub
* Docker
* Gunicorn

---

## 📂 Project Structure

```text
ExamGuard-AI/
│
├── app/
│   ├── authentication/
│   ├── exams/
│   ├── classrooms/
│   ├── monitoring/
│   ├── recordings/
│   ├── analytics/
│   ├── templates/
│   ├── static/
│   └── models/
│
├── migrations/
├── uploads/
├── instance/
├── config.py
├── requirements.txt
├── run.py
└── README.md
```

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/your-username/ExamGuard-AI.git
cd ExamGuard-AI
```

### Create Virtual Environment

```bash
python -m venv venv
```

Activate the environment:

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file and configure values such as:

* SECRET_KEY
* DATABASE_URL
* JWT_SECRET_KEY
* MAIL_USERNAME
* MAIL_PASSWORD

### Run Database Migrations

```bash
flask db upgrade
```

### Start the Application

```bash
python run.py
```

Open the application in your browser.

---

## 🎯 Future Enhancements

* AI-based gaze estimation
* Voice activity detection
* Browser lockdown mode
* LLM-assisted question generation
* AI-powered result analytics
* Mobile application
* Multi-language support
* LMS integration
* Cloud recording storage

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a new feature branch.
3. Commit your changes.
4. Push the branch.
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 👩‍💻 Developed By

**Jaskirat Kaur**

Secure Online Examination & AI Proctoring Platform developed as a full-stack academic project focused on secure, scalable, and intelligent online assessments.
