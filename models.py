from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='User') # Admin, User, Auditor
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Behavior Profile (Stored as JSON for flexibility)
    behavior_data = db.Column(db.Text, default='{}') 
    
    transactions = db.relationship('Transaction', backref='owner', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    def set_behavior(self, data):
        self.behavior_data = json.dumps(data)
    
    def get_behavior(self):
        return json.loads(self.behavior_data)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    location = db.Column(db.String(100))
    ip_address = db.Column(db.String(45))
    
    # Fraud Detection Fields
    risk_score = db.Column(db.Float, default=0.0) # 0 to 100
    is_anomaly = db.Column(db.Boolean, default=False)
    detection_method = db.Column(db.String(50)) # AI, Rule-based, Hybrid
    
    alerts = db.relationship('Alert', backref='transaction', lazy=True)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    severity = db.Column(db.String(20)) # Low, Medium, High
    status = db.Column(db.String(20), default='Open') # Open, Resolved, Flagged
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    resolution_notes = db.Column(db.Text)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
