from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///desktime_demo.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="employee")

class WorkSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="working")
    activity = db.Column(db.String(120), default="General work")
    user = db.relationship("User", backref="sessions")

def current_user():
    if "user_id" not in session:
        return None
    return db.session.get(User, session["user_id"])

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("login"))
        if user.role != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper

def serialize_session(ws):
    elapsed = int(((ws.ended_at or datetime.utcnow()) - ws.started_at).total_seconds())
    return {
        "id": ws.id, "employee": ws.user.name, "user_id": ws.user_id,
        "started_at": ws.started_at.isoformat() + "Z",
        "ended_at": ws.ended_at.isoformat() + "Z" if ws.ended_at else None,
        "status": ws.status, "activity": ws.activity, "seconds": max(0, elapsed)
    }

@app.route("/")
def index():
    return redirect(url_for("dashboard") if current_user() else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user())

@app.route("/api/me")
@login_required
def api_me():
    user = current_user()
    active = WorkSession.query.filter_by(user_id=user.id, ended_at=None).order_by(WorkSession.id.desc()).first()
    return jsonify({"id": user.id, "name": user.name, "role": user.role,
                    "active": serialize_session(active) if active else None})

@app.route("/api/summary")
@login_required
def api_summary():
    user = current_user()
    query = WorkSession.query
    if user.role != "admin":
        query = query.filter_by(user_id=user.id)
    sessions = query.order_by(WorkSession.started_at.desc()).limit(100).all()
    today = date.today()
    today_sessions = [s for s in sessions if s.started_at.date() == today]
    total = sum(int(((s.ended_at or datetime.utcnow()) - s.started_at).total_seconds()) for s in today_sessions)
    active_count = WorkSession.query.filter_by(ended_at=None).count()
    return jsonify({
        "total_seconds": max(0, total),
        "active_count": active_count if user.role == "admin" else (1 if any(s.ended_at is None for s in today_sessions) else 0),
        "sessions": [serialize_session(s) for s in sessions],
        "is_admin": user.role == "admin"
    })

@app.route("/api/start", methods=["POST"])
@login_required
def start():
    user = current_user()
    existing = WorkSession.query.filter_by(user_id=user.id, ended_at=None).first()
    if existing:
        return jsonify({"error": "A timer is already running."}), 409
    activity = (request.json or {}).get("activity", "General work")[:120]
    ws = WorkSession(user_id=user.id, activity=activity)
    db.session.add(ws)
    db.session.commit()
    payload = serialize_session(ws)
    socketio.emit("session_update", payload)
    return jsonify({"ok": True, "session": payload})

@app.route("/api/stop", methods=["POST"])
@login_required
def stop():
    user = current_user()
    ws = WorkSession.query.filter_by(user_id=user.id, ended_at=None).first()
    if not ws:
        return jsonify({"error": "No running timer."}), 400
    ws.ended_at = datetime.utcnow()
    ws.status = "completed"
    db.session.commit()
    payload = serialize_session(ws)
    socketio.emit("session_update", payload)
    return jsonify({"ok": True, "session": payload})

@app.route("/api/sessions")
@login_required
def sessions():
    user = current_user()
    query = WorkSession.query
    if user.role != "admin":
        query = query.filter_by(user_id=user.id)
    return jsonify([serialize_session(s) for s in query.order_by(WorkSession.started_at.desc()).limit(100).all()])

@socketio.on("connect")
def on_connect():
    user = current_user()
    if user:
        join_room("admins" if user.role == "admin" else f"user_{user.id}")
        emit("connected", {"message": "Connected to live updates"})

def seed():
    db.create_all()
    if User.query.count() == 0:
        db.session.add_all([
            User(name="Admin User", email="admin@demo.com", password_hash=generate_password_hash("admin123"), role="admin"),
            User(name="Aarav Sharma", email="employee@demo.com", password_hash=generate_password_hash("employee123"), role="employee")
        ])
        db.session.commit()

with app.app_context():
    seed()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///desktime_demo.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="employee")

class WorkSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="working")
    activity = db.Column(db.String(120), default="General work")
    user = db.relationship("User", backref="sessions")

def current_user():
    if "user_id" not in session:
        return None
    return db.session.get(User, session["user_id"])

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("login"))
        if user.role != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper

def serialize_session(ws):
    elapsed = int(((ws.ended_at or datetime.utcnow()) - ws.started_at).total_seconds())
    return {
        "id": ws.id, "employee": ws.user.name, "user_id": ws.user_id,
        "started_at": ws.started_at.isoformat() + "Z",
        "ended_at": ws.ended_at.isoformat() + "Z" if ws.ended_at else None,
        "status": ws.status, "activity": ws.activity, "seconds": max(0, elapsed)
    }

@app.route("/")
def index():
    return redirect(url_for("dashboard") if current_user() else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user())

@app.route("/api/me")
@login_required
def api_me():
    user = current_user()
    active = WorkSession.query.filter_by(user_id=user.id, ended_at=None).order_by(WorkSession.id.desc()).first()
    return jsonify({"id": user.id, "name": user.name, "role": user.role,
                    "active": serialize_session(active) if active else None})

@app.route("/api/summary")
@login_required
def api_summary():
    user = current_user()
    query = WorkSession.query
    if user.role != "admin":
        query = query.filter_by(user_id=user.id)
    sessions = query.order_by(WorkSession.started_at.desc()).limit(100).all()
    today = date.today()
    today_sessions = [s for s in sessions if s.started_at.date() == today]
    total = sum(int(((s.ended_at or datetime.utcnow()) - s.started_at).total_seconds()) for s in today_sessions)
    active_count = WorkSession.query.filter_by(ended_at=None).count()
    return jsonify({
        "total_seconds": max(0, total),
        "active_count": active_count if user.role == "admin" else (1 if any(s.ended_at is None for s in today_sessions) else 0),
        "sessions": [serialize_session(s) for s in sessions],
        "is_admin": user.role == "admin"
    })

@app.route("/api/start", methods=["POST"])
@login_required
def start():
    user = current_user()
    existing = WorkSession.query.filter_by(user_id=user.id, ended_at=None).first()
    if existing:
        return jsonify({"error": "A timer is already running."}), 409
    activity = (request.json or {}).get("activity", "General work")[:120]
    ws = WorkSession(user_id=user.id, activity=activity)
    db.session.add(ws)
    db.session.commit()
    payload = serialize_session(ws)
    socketio.emit("session_update", payload)
    return jsonify({"ok": True, "session": payload})

@app.route("/api/stop", methods=["POST"])
@login_required
def stop():
    user = current_user()
    ws = WorkSession.query.filter_by(user_id=user.id, ended_at=None).first()
    if not ws:
        return jsonify({"error": "No running timer."}), 400
    ws.ended_at = datetime.utcnow()
    ws.status = "completed"
    db.session.commit()
    payload = serialize_session(ws)
    socketio.emit("session_update", payload)
    return jsonify({"ok": True, "session": payload})

@app.route("/api/sessions")
@login_required
def sessions():
    user = current_user()
    query = WorkSession.query
    if user.role != "admin":
        query = query.filter_by(user_id=user.id)
    return jsonify([serialize_session(s) for s in query.order_by(WorkSession.started_at.desc()).limit(100).all()])

@socketio.on("connect")
def on_connect():
    user = current_user()
    if user:
        join_room("admins" if user.role == "admin" else f"user_{user.id}")
        emit("connected", {"message": "Connected to live updates"})

def seed():
    db.create_all()
    if User.query.count() == 0:
        db.session.add_all([
            User(name="Admin User", email="admin@demo.com", password_hash=generate_password_hash("admin123"), role="admin"),
            User(name="Aarav Sharma", email="employee@demo.com", password_hash=generate_password_hash("employee123"), role="employee")
        ])
        db.session.commit()

with app.app_context():
    seed()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
