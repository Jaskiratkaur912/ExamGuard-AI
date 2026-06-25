from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, emit
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta  
import pymysql
import re
import random

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# CRITICAL: A secret key is required to cryptographically sign session cookies
app.secret_key = 'your_super_secure_secret_matrix_key_here' 

# Set session duration lifetime window configuration to 15 minutes
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

# --- RECORDING STORAGE SETUP ---
# Local disk for now. To switch to cloud storage later (S3 / GCS / etc.),
# replace the body of save_recording_file() with an upload call to that
# service and store the returned URL instead of a local filename.
RECORDINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")
os.makedirs(RECORDINGS_DIR, exist_ok=True)

print("Connected") 

# --- MOCK USER DATABASE ---
USER_DATABASE = {
    "admin@gmail.com": {
        "password": generate_password_hash("Admin@1234"), 
        "otp": None
    },
    "student@gmail.com": {
        "password": generate_password_hash("Student@1234"), 
        "otp": None
    }
}

# --- UNIFIED PERMANENT STORAGE SETUP ---
DATA_FILE = "classroom_storage.json"

def load_system_data():
    """Loads all system states so they persist across sessions."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return (
                    data.get("classrooms", []), 
                    data.get("enrollments", {}),
                    data.get("exams", {}),          
                    data.get("results", {}),        
                    data.get("activity_logs", {}),
                    data.get("recordings", {}),
                    data.get("exam_papers", {}),
                    data.get("exam_submissions", {})
                )
        except:
            return [], {}, {}, {}, {}, {}, {}, {}
    return [], {}, {}, {}, {}, {}, {}, {}

def save_system_data():
    """Saves classrooms, enrollments, exams, results, activity logs, recordings, exam papers, and submissions to disk."""
    payload = {
        "classrooms": CLASSROOM_DATABASE,
        "enrollments": STUDENT_ENROLLMENTS,
        "exams": EXAM_DATABASE,
        "results": RESULT_DATABASE,
        "activity_logs": ACTIVITY_LOGS,
        "recordings": RECORDINGS_DATABASE,
        "exam_papers": EXAM_PAPERS_DATABASE,
        "exam_submissions": EXAM_SUBMISSIONS_DATABASE
    }
    with open(DATA_FILE, "w") as f:
        json.dump(payload, f, indent=4)

# FIXED: Explicitly declaring ALL variables when the script boots up
(CLASSROOM_DATABASE, STUDENT_ENROLLMENTS, EXAM_DATABASE, RESULT_DATABASE, ACTIVITY_LOGS,
 RECORDINGS_DATABASE, EXAM_PAPERS_DATABASE, EXAM_SUBMISSIONS_DATABASE) = load_system_data()

# --- EXAM PAPER FILE STORAGE (uploaded PDFs for 'pdf' type exam papers) ---
EXAM_PAPERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exam_papers")
os.makedirs(EXAM_PAPERS_DIR, exist_ok=True)

def validate_password_requirements(password):
    if len(password) > 20: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[0-9]", password): return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): return False
    return True

# --- COMPREHENSIVE SESSION CONFIGURATION HOOK ---
@app.before_request
def make_session_permanent():
    # Makes sure the 15-minute timer resets on every active server interaction request
    session.permanent = True

# --- STUDENT DASHBOARD ROUTE ---
@app.route('/student-dashboard')
def student_dashboard():
    if 'user_type' not in session or session['user_type'] != 'student':
        return redirect(url_for('student_login'))
        
    student_email = session.get('user_email', 'student@gmail.com')
    joined_tokens = STUDENT_ENROLLMENTS.get(student_email, [])
    my_classes = [c for c in CLASSROOM_DATABASE if c['token'] in joined_tokens]
    
    return render_template('student_gateway.html', student_email=student_email, my_classes=my_classes)

# --- JOIN CLASSROOM VIA CODE ENDPOINT ---
@app.route('/join-classroom', methods=['POST'])
def join_classroom():
    if 'user_type' not in session or session['user_type'] != 'student':
        return redirect(url_for('student_login'))

    student_email = request.form.get('student_email')
    input_code = request.form.get('class_code', '').strip().upper()
    
    # 1. Check if the class code actually exists in the system
    target_class = next((c for c in CLASSROOM_DATABASE if c['token'] == input_code), None)
    
    if not target_class:
        return redirect(url_for('student_dashboard', email=student_email, error="Invalid code structure or class matrix doesn't exist."))
    
    # 2. Register the enrollment mapping
    if student_email not in STUDENT_ENROLLMENTS:
        STUDENT_ENROLLMENTS[student_email] = []
        
    if input_code not in STUDENT_ENROLLMENTS[student_email]:
        STUDENT_ENROLLMENTS[student_email].append(input_code)
        save_system_data()  # Save enrollment mapping instantly to disk file
        
    return redirect(url_for('student_dashboard', email=student_email))

# --- STUDENT VIEW OF A SPECIFIC CLASSROOM ---
@app.route('/student/classroom/<token>')
def student_classroom_home(token):
    if 'user_type' not in session or session['user_type'] != 'student':
        return redirect(url_for('student_login'))

    student_email = session.get('user_email', 'student@gmail.com')
    
    # Security Check: Ensure student is actually enrolled
    joined_tokens = STUDENT_ENROLLMENTS.get(student_email, [])
    if token.upper() not in joined_tokens:
        return "Access Denied: You are not enrolled in this matrix ecosystem.", 403
        
    classroom = next((c for c in CLASSROOM_DATABASE if c['token'] == token.upper()), None)
    if not classroom:
        return "Classroom profile not found.", 404

    exams_data = EXAM_DATABASE.get(token.upper(), {
        "upcoming": [],
        "assigned_exams": [],
        "assigned_assignments": [],
        "deadlines": []
    })
    pdf_bank = EXAM_DATABASE.get(f"{token.upper()}_PDFS", [])
    recordings = [r for r in RECORDINGS_DATABASE.get(token.upper(), []) if r.get('shared')]
    exam_papers = EXAM_PAPERS_DATABASE.get(token.upper(), [])

    # Attach this student's submission status to each paper so the template
    # can show "Completed" instead of "Enter Exam" once they've submitted.
    student_subs = EXAM_SUBMISSIONS_DATABASE.get(student_email, {})
    for paper in exam_papers:
        paper['_submitted'] = paper['id'] in student_subs

    return render_template('student_classroom.html', classroom=classroom, exams=exams_data,
                            pdf_bank=pdf_bank, recordings=recordings, exam_papers=exam_papers)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/send-otp', methods=['POST'])
def send_otp():
    email = request.form.get('email')
    if email not in USER_DATABASE:
        return jsonify({"success": False, "message": "Email not found."}), 404
    
    otp_code = str(random.randint(100000, 999999))
    USER_DATABASE[email]['otp'] = otp_code
    
    print("\n" + "="*40)
    print(f" Target User: {email} | Secure OTP: {otp_code}")
    print("="*40 + "\n")
    return jsonify({"success": True, "message": "OTP printed to console!"})

# --- ADMIN DASHBOARD ROUTE ---
@app.route('/admin-dashboard')
def admin_dashboard():
    # Security Gate: Redirect if session credentials don't match
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('admin_login'))
        
    admin_name = request.args.get('name', 'Administrator')
    return render_template('admin_dashboard.html', admin_name=admin_name, classrooms=CLASSROOM_DATABASE)

# --- CREATE CLASS ENDPOINT ---
@app.route('/create-classroom', methods=['POST'])
def create_classroom():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('admin_login'))

    class_name = request.form.get('class_name')
    class_token = request.form.get('class_token')
    admin_name = request.form.get('admin_name', 'Administrator')

    if class_name and class_token:
        # 1. Append to current live memory list
        CLASSROOM_DATABASE.append({
            "name": class_name.strip(),
            "token": class_token.strip().upper()
        })
        # 2. Write it straight to the file on your hard drive!
        save_system_data()
    
    return redirect(url_for('admin_dashboard', name=admin_name))

# --- DELETE CLASS ENDPOINT ---
@app.route('/delete-classroom/<token>', methods=['POST'])
def delete_classroom(token):
    global CLASSROOM_DATABASE
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('admin_login'))

    # Filter out the deleted class
    CLASSROOM_DATABASE = [c for c in CLASSROOM_DATABASE if c['token'] != token.upper()]
    
    # Clean up student enrollments for the deleted classroom token
    for student in STUDENT_ENROLLMENTS:
        if token.upper() in STUDENT_ENROLLMENTS[student]:
            STUDENT_ENROLLMENTS[student].remove(token.upper())

    # Re-save the updated cleaner lists back to your file
    save_system_data()
    
    admin_name = request.form.get('admin_name', 'Administrator')
    return redirect(url_for('admin_dashboard', name=admin_name))

# ============================================================
# EXAM PAPER MANAGEMENT (admin creates PDF or MCQ exam papers)
# ============================================================

def _new_exam_id():
    return __import__('uuid').uuid4().hex[:10]

@app.route('/classroom/<token>/create-exam', methods=['POST'])
def create_exam(token):
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('admin_login'))

    token = token.upper()
    exam_type = request.form.get('exam_type')  # 'pdf' or 'mcq'
    title = request.form.get('title', '').strip()
    duration = int(request.form.get('duration_minutes', 60))
    start_time = request.form.get('start_time')  # 'YYYY-MM-DDTHH:MM' from <input type=datetime-local>

    if not title or not start_time:
        return "Title and start time are required.", 400

    exam_entry = {
        "id": _new_exam_id(),
        "title": title,
        "type": exam_type,
        "duration_minutes": duration,
        "start_time": start_time,
        "created_at": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    if exam_type == 'pdf':
        file = request.files.get('exam_pdf')
        if not file or file.filename == '':
            return "A PDF file is required for a PDF-based exam.", 400
        classroom_dir = os.path.join(EXAM_PAPERS_DIR, token)
        os.makedirs(classroom_dir, exist_ok=True)
        safe_name = secure_filename(f"{exam_entry['id']}_{file.filename}")
        file.save(os.path.join(classroom_dir, safe_name))
        exam_entry["pdf_filename"] = safe_name

    elif exam_type == 'mcq':
        # Questions arrive as parallel form arrays from the MCQ builder UI:
        # question_text[], option_0[], option_1[], option_2[], option_3[], correct_index[]
        questions_raw = request.form.getlist('question_text[]')
        opt0 = request.form.getlist('option_0[]')
        opt1 = request.form.getlist('option_1[]')
        opt2 = request.form.getlist('option_2[]')
        opt3 = request.form.getlist('option_3[]')
        correct = request.form.getlist('correct_index[]')

        questions = []
        for i, q_text in enumerate(questions_raw):
            if not q_text.strip():
                continue
            questions.append({
                "question": q_text.strip(),
                "options": [opt0[i], opt1[i], opt2[i], opt3[i]],
                "correct_index": int(correct[i])
            })
        if not questions:
            return "At least one MCQ question is required.", 400
        exam_entry["questions"] = questions

    else:
        return "Invalid exam type.", 400

    EXAM_PAPERS_DATABASE.setdefault(token, []).append(exam_entry)
    save_system_data()
    return redirect(url_for('classroom_home', token=token))

@app.route('/classroom/<token>/delete-exam/<exam_id>', methods=['POST'])
def delete_exam(token, exam_id):
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('admin_login'))
    token = token.upper()
    EXAM_PAPERS_DATABASE[token] = [e for e in EXAM_PAPERS_DATABASE.get(token, []) if e['id'] != exam_id]
    save_system_data()
    return redirect(url_for('classroom_home', token=token))

# Serves the exam PDF only inside the locked exam window, only once the exam has started,
# and only to students enrolled in that classroom (or the admin, for review).
@app.route('/exam-paper-file/<token>/<exam_id>')
def serve_exam_pdf(token, exam_id):
    if 'user_type' not in session:
        return "Access Denied", 403
    token = token.upper()
    paper = next((e for e in EXAM_PAPERS_DATABASE.get(token, []) if e['id'] == exam_id), None)
    if not paper or paper.get('type') != 'pdf':
        return "Exam paper not found.", 404

    if session['user_type'] == 'student':
        student_email = session.get('user_email', '')
        if token not in STUDENT_ENROLLMENTS.get(student_email, []):
            return "Access Denied: Not enrolled.", 403
        import datetime as _dt
        start = _dt.datetime.fromisoformat(paper['start_time'])
        if _dt.datetime.now() < start:
            return "This exam has not started yet.", 403

    classroom_dir = os.path.join(EXAM_PAPERS_DIR, token)
    return send_from_directory(classroom_dir, paper['pdf_filename'])

# --- STUDENT: EXAM ENTRY (the locked exam-taking window) ---
@app.route('/exam/<token>/<exam_id>')
def take_exam(token, exam_id):
    if 'user_type' not in session or session['user_type'] != 'student':
        return redirect(url_for('student_login'))

    token = token.upper()
    student_email = session.get('user_email', '')
    if token not in STUDENT_ENROLLMENTS.get(student_email, []):
        return "Access Denied: Not enrolled in this classroom.", 403

    paper = next((e for e in EXAM_PAPERS_DATABASE.get(token, []) if e['id'] == exam_id), None)
    if not paper:
        return "Exam paper not found.", 404

    if exam_id in EXAM_SUBMISSIONS_DATABASE.get(student_email, {}):
        return "You have already submitted this exam.", 403

    classroom = next((c for c in CLASSROOM_DATABASE if c['token'] == token), None)
    return render_template('exam_room.html', paper=paper, token=token, classroom=classroom,
                            student_email=student_email)

# --- STUDENT: SUBMIT EXAM ANSWERS / FINISH ---
@app.route('/exam/<token>/<exam_id>/submit', methods=['POST'])
def submit_exam(token, exam_id):
    if 'user_type' not in session or session['user_type'] != 'student':
        return jsonify({"success": False, "message": "Not authenticated."}), 403

    token = token.upper()
    student_email = session.get('user_email', '')
    paper = next((e for e in EXAM_PAPERS_DATABASE.get(token, []) if e['id'] == exam_id), None)
    if not paper:
        return jsonify({"success": False, "message": "Exam not found."}), 404

    payload = request.get_json(force=True) or {}
    answers = payload.get('answers', {})
    violation_log = payload.get('violations', [])

    score = None
    total = None
    if paper.get('type') == 'mcq':
        questions = paper.get('questions', [])
        total = len(questions)
        score = 0
        for i, q in enumerate(questions):
            given = answers.get(str(i))
            if given is not None and int(given) == q['correct_index']:
                score += 1

    EXAM_SUBMISSIONS_DATABASE.setdefault(student_email, {})[exam_id] = {
        "exam_title": paper['title'],
        "token": token,
        "answers": answers,
        "score": score,
        "total": total,
        "violations": violation_log,
        "submitted_at": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    save_system_data()

    return jsonify({"success": True, "score": score, "total": total})

# --- LIVE PROCTORING ALERT (browser -> server -> admin, via Socket.IO room) ---
@app.route('/exam/<token>/<exam_id>/flag', methods=['POST'])
def flag_violation(token, exam_id):
    if 'user_type' not in session or session['user_type'] != 'student':
        return jsonify({"success": False}), 403

    token = token.upper()
    student_email = session.get('user_email', '')
    payload = request.get_json(force=True) or {}
    reason = payload.get('reason', 'Unspecified violation')

    # Push a live alert into the admin's proctoring room for this exam, over Socket.IO
    socketio.emit('proctor-alert', {
        "student": student_email,
        "reason": reason,
        "timestamp": __import__('datetime').datetime.now().strftime("%H:%M:%S")
    }, room=f"proctor-{token}-{exam_id}")

    return jsonify({"success": True})

# --- ADMIN: LIVE PROCTORING MONITOR PAGE ---
@app.route('/classroom/<token>/proctor/<exam_id>')
def proctor_monitor(token, exam_id):
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('admin_login'))
    token = token.upper()
    paper = next((e for e in EXAM_PAPERS_DATABASE.get(token, []) if e['id'] == exam_id), None)
    if not paper:
        return "Exam paper not found.", 404
    classroom = next((c for c in CLASSROOM_DATABASE if c['token'] == token), None)
    return render_template('proctor_monitor.html', paper=paper, token=token, classroom=classroom)

# --- DYNAMIC CLASSROOM HOME PAGE ROUTE ---
@app.route('/classroom/<token>')
def classroom_home(token):
    # if 'user_type' not in session or session['user_type'] != 'admin':
    #     return redirect(url_for('admin_login'))

    # classroom = next((c for c in CLASSROOM_DATABASE if c['token'] == token.upper()), None)
    
    # if not classroom:
    #     return "Classroom Environment Matrix Not Found", 404
        
    # return render_template('classroom.html', classroom=classroom)

    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('admin_login'))

    classroom = next((c for c in CLASSROOM_DATABASE if c['token'] == token.upper()), None)
    if not classroom:
        return "Classroom Environment Matrix Not Found", 404

    # Fetch data sets or default to empty list/dict structures if not initialized
    exams_data = EXAM_DATABASE.get(token.upper(), {
        "upcoming": [],
        "assigned_exams": [],
        "assigned_assignments": [],
        "deadlines": []
    })
    
    pdf_bank = EXAM_DATABASE.get(f"{token.upper()}_PDFS", [])
    activities = ACTIVITY_LOGS.get(token.upper(), [])
    recordings = RECORDINGS_DATABASE.get(token.upper(), [])
    exam_papers = EXAM_PAPERS_DATABASE.get(token.upper(), [])

    return render_template(
        'classroom.html', 
        classroom=classroom, 
        exams=exams_data,
        pdf_bank=pdf_bank,
        activities=activities,
        recordings=recordings,
        exam_papers=exam_papers
    )

# --- LOGIN POST HANDLERS ---
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        full_name = request.form.get('full_name') or 'Administrator'
        email = request.form.get('identity')
        password = request.form.get('password')
        otp_attempt = request.form.get('otp')
        login_mode = request.form.get('login_mode')

        user_data = USER_DATABASE.get(email)
        if not user_data or not email.endswith('@gmail.com'):
            return "Access Denied", 401

        # Validation success helper
        if (login_mode == 'otp' and otp_attempt == user_data['otp']) or \
           (login_mode == 'password' and check_password_hash(user_data['password'], password)):
            if login_mode == 'otp': user_data['otp'] = None
            
            # Establish Server Session Storage Parameters
            session['user_type'] = 'admin'
            session['user_email'] = email
            return redirect(url_for('admin_dashboard', name=full_name))
        
        return "Authentication Failure", 401
    return render_template('admin.html')

@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form.get('identity')
        password = request.form.get('password')
        otp_attempt = request.form.get('otp')
        login_mode = request.form.get('login_mode')

        user_data = USER_DATABASE.get(email)
        if not user_data or not email.endswith('@gmail.com'):
            return "Access Denied", 401

        if (login_mode == 'otp' and otp_attempt == user_data['otp']) or \
           (login_mode == 'password' and check_password_hash(user_data['password'], password)):
            if login_mode == 'otp': user_data['otp'] = None
            
            # Establish Server Session Storage Parameters
            session['user_type'] = 'student'
            session['user_email'] = email
            return redirect(url_for('student_dashboard'))
            
        return "Authentication Failure", 401
    return render_template('student.html')

@app.route('/logout')
def logout():
    session.clear() # Completely wipes out server-side cookies
    return redirect(url_for('home'))

# --- LIVE MEET ROOM ---
@app.route('/meet/<token>')
def meet_room(token):
    # Either an admin or an enrolled student may enter, per the classroom token
    if 'user_type' not in session:
        return redirect(url_for('home'))

    token = token.upper()
    classroom = next((c for c in CLASSROOM_DATABASE if c['token'] == token), None)
    if not classroom:
        return "Classroom Environment Matrix Not Found", 404

    is_admin = session['user_type'] == 'admin'

    if is_admin:
        self_name = request.args.get('name', 'Administrator')
        back_url = url_for('classroom_home', token=token)
    else:
        student_email = session.get('user_email', 'student@gmail.com')
        joined_tokens = STUDENT_ENROLLMENTS.get(student_email, [])
        if token not in joined_tokens:
            return "Access Denied: You are not enrolled in this classroom.", 403
        self_name = student_email.split('@')[0]
        back_url = url_for('student_classroom_home', token=token)

    return render_template('meet.html', classroom=classroom, is_admin=is_admin,
                            self_name=self_name, back_url=back_url)

# --- RECORDING UPLOAD (admin browser -> server disk) ---
@app.route('/upload-recording', methods=['POST'])
def upload_recording():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({"success": False, "message": "Only the admin can save recordings."}), 403

    token = request.form.get('token', '').strip().upper()
    file = request.files.get('recording')

    if not token or not file:
        return jsonify({"success": False, "message": "Missing recording data."}), 400

    classroom_dir = os.path.join(RECORDINGS_DIR, token)
    os.makedirs(classroom_dir, exist_ok=True)

    safe_name = secure_filename(file.filename) or f"meet_{token}_{int(__import__('time').time())}.webm"
    save_path = os.path.join(classroom_dir, safe_name)
    file.save(save_path)

    RECORDINGS_DATABASE.setdefault(token, []).append({
        "filename": safe_name,
        "timestamp": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M"),
        "shared": False
    })
    save_system_data()

    return jsonify({"success": True, "filename": safe_name})

# --- SERVE A SAVED RECORDING (admin-only download) ---
@app.route('/recordings/<token>/<filename>')
def serve_recording(token, filename):
    if 'user_type' not in session:
        return "Access Denied", 403
    token = token.upper()

    if session['user_type'] == 'admin':
        classroom_dir = os.path.join(RECORDINGS_DIR, token)
        return send_from_directory(classroom_dir, filename, as_attachment=True)

    if session['user_type'] == 'student':
        student_email = session.get('user_email', '')
        if token not in STUDENT_ENROLLMENTS.get(student_email, []):
            return "Access Denied: Not enrolled in this classroom.", 403
        record = next((r for r in RECORDINGS_DATABASE.get(token, []) if r['filename'] == filename), None)
        if not record or not record.get('shared'):
            return "This recording has not been shared with students yet.", 403
        classroom_dir = os.path.join(RECORDINGS_DIR, token)
        return send_from_directory(classroom_dir, filename, as_attachment=True)

    return "Access Denied", 403

@app.route('/toggle-recording-share', methods=['POST'])
def toggle_recording_share():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({"success": False, "message": "Admin access required."}), 403

    token = request.form.get('token', '').strip().upper()
    filename = request.form.get('filename', '').strip()

    records = RECORDINGS_DATABASE.get(token, [])
    record = next((r for r in records if r['filename'] == filename), None)
    if not record:
        return jsonify({"success": False, "message": "Recording not found."}), 404

    record['shared'] = not record.get('shared', False)
    save_system_data()
    return jsonify({"success": True, "shared": record['shared']})

# --- WEBRTC SIGNALING (Socket.IO) ---
# In-memory map of socket id -> {room, name, is_admin}, used for cleanup on disconnect.
ACTIVE_MEET_PARTICIPANTS = {}

@socketio.on('join-proctor-room')
def on_join_proctor_room(data):
    # Admin's monitoring dashboard joins this room to receive live violation
    # alerts pushed by flag_violation() for the given exam.
    room = f"proctor-{data.get('token', '').strip().upper()}-{data.get('exam_id', '')}"
    join_room(room)

@socketio.on('join-room')
def on_join_room(data):
    room = data.get('room', '').strip().upper()
    name = data.get('name', 'Participant')
    is_admin = bool(data.get('isAdmin'))

    join_room(room)
    ACTIVE_MEET_PARTICIPANTS[request.sid] = {"room": room, "name": name, "is_admin": is_admin}

    # Tell everyone already in the room that a new peer joined, so they initiate the offer
    emit('user-joined', {"id": request.sid, "name": name}, room=room, include_self=False)

@socketio.on('offer')
def on_offer(data):
    target = data.get('target')
    if target:
        emit('offer', {"from": request.sid, "offer": data.get('offer'), "name": data.get('name')}, to=target)

@socketio.on('answer')
def on_answer(data):
    target = data.get('target')
    if target:
        emit('answer', {"from": request.sid, "answer": data.get('answer')}, to=target)

@socketio.on('ice-candidate')
def on_ice_candidate(data):
    target = data.get('target')
    if target:
        emit('ice-candidate', {"from": request.sid, "candidate": data.get('candidate')}, to=target)

@socketio.on('recording-status')
def on_recording_status(data):
    room = data.get('room', '').strip().upper()
    emit('recording-status', {"recording": bool(data.get('recording'))}, room=room, include_self=False)

@socketio.on('leave-room')
def on_leave_room(data):
    room = data.get('room', '').strip().upper()
    leave_room(room)
    ACTIVE_MEET_PARTICIPANTS.pop(request.sid, None)
    emit('user-left', {"id": request.sid}, room=room, include_self=False)

@socketio.on('disconnect')
def on_disconnect():
    info = ACTIVE_MEET_PARTICIPANTS.pop(request.sid, None)
    if info:
        emit('user-left', {"id": request.sid}, room=info["room"], include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)