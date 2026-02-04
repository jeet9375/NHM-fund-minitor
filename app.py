from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)

# 1. Enhanced CORS: Essential for allowing the mobile app to communicate with the server
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# 2. Database Setup: Configured to work both locally and on cloud servers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'nhm_demo.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nhm_india_secure_2026')

db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(500), nullable=False)
    role = db.Column(db.String(50), default="government")

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(100), unique=True)
    allocation = db.Column(db.Float, default=0.0)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.Column(db.String(100))
    state = db.Column(db.String(100))
    type = db.Column(db.String(10))
    amount = db.Column(db.Float)
    note = db.Column(db.Text, nullable=False)

class ResetRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Database Initialization
def init_db():
    db.create_all()
    # Default Admin: jeet@123gmail.com | Password: jeet123
    if not User.query.filter_by(username="jeet@123gmail.com").first():
        db.session.add(User(
            username="jeet@123gmail.com", 
            password_hash=generate_password_hash("jeet123"), 
            role="admin"
        ))
        db.session.commit()

# --- API Routes ---

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get("username")).first()
    if user and check_password_hash(user.password_hash, data.get("password")):
        return jsonify({"user": user.username, "role": user.role}), 200
    return jsonify({"error": "Invalid Credentials"}), 401

@app.route("/api/admin/add-client", methods=["POST"])
def add_client():
    data = request.get_json()
    gmail, password = data.get("gmail"), data.get("password")
    if User.query.filter_by(username=gmail).first():
        return jsonify({"error": "User already exists"}), 400
    new_user = User(username=gmail, password_hash=generate_password_hash(password), role="government")
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "New Officer Added Successfully"}), 200

@app.route("/api/admin/clear-logs", methods=["POST"])
def clear_logs():
    db.session.query(AuditLog).delete()
    db.session.commit()
    return jsonify({"message": "Audit History Cleared"}), 200

@app.route("/api/funds", methods=["GET"])
def get_funds():
    projects = Project.query.all()
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return jsonify({
        "funds": {p.state: p.allocation for p in projects},
        "logs": [{"time": l.timestamp.strftime("%Y-%m-%d %H:%M"), "user": l.user, "s": l.state, "type": l.type, "a": l.amount, "n": l.note} for l in logs]
    })

@app.route("/api/sync", methods=["POST"])
def sync():
    data = request.get_json()
    state, amount, stype, note, user = data.get("state"), float(data.get("amount")), data.get("type"), data.get("note"), data.get("user")
    
    proj = Project.query.filter_by(state=state).first() or Project(state=state, allocation=0.0)
    
    if stype == "add":
        proj.allocation += amount
    else:
        proj.allocation -= amount
        
    db.session.add(proj)
    db.session.add(AuditLog(user=user, state=state, type=stype, amount=amount, note=note))
    db.session.commit()
    return jsonify({"success": True})

@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    db.session.add(ResetRequest(user_email=data.get("email")))
    db.session.commit()
    return jsonify({"message": "Reset request sent to Admin"}), 200

# 3. Server Execution: Adjusted for cloud environments like Render
if __name__ == "__main__":
    with app.app_context(): 
        init_db()
    # Uses port provided by Render or defaults to 5000 for local use
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)