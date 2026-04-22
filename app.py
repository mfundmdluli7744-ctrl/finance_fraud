import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Transaction, Alert, AuditLog
from utils.fraud import FraudEngine
from utils.ocr import OCRScanner
from datetime import datetime, timedelta
import random
import csv
import io
from flask import Response

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_DATA_PATH'] = 'sqlite:///database.db' # Will actually use database.db in current dir
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Global Fraud Engine
fraud_engine = FraudEngine(db.session, __import__('models'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def log_audit(user_id, action, details=""):
    audit = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()

# --- Routes ---

@app.route('/')
@login_required
def index():
    # Statistics
    total_vol = db.session.query(db.func.sum(Transaction.amount)).scalar() or 0
    active_alerts = Alert.query.filter_by(status='Open').count()
    total_txs = Transaction.query.count()
    
    # AI Risk Distribution (Chart Data)
    risk_data = {
        'Low': Transaction.query.filter(Transaction.risk_score < 30).count(),
        'Medium': Transaction.query.filter(Transaction.risk_score.between(30, 70)).count(),
        'High': Transaction.query.filter(Transaction.risk_score > 70).count()
    }

    # Recent Transactions
    transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(10).all()
    
    # Recent Alerts
    alerts = Alert.query.order_by(Alert.timestamp.desc()).limit(5).all()
    
    return render_template('index.html', 
                           stats={'total_volume': total_vol, 'active_alerts': active_alerts, 'total_txs': total_txs},
                           risk_data=risk_data,
                           transactions=transactions,
                           alerts=alerts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            log_audit(user.id, "User Login", f"Successful login for {user.username}")
            return redirect(url_for('index'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password_hash=hashed_password,
            role=request.form.get('role', 'User')
        )
        db.session.add(user)
        db.session.commit()
        log_audit(user.id, "User Registered", f"Account created for {user.username}")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    log_audit(current_user.id, "User Logout")
    logout_user()
    return redirect(url_for('login'))

@app.route('/process_transaction', methods=['POST'])
@login_required
def process_transaction():
    amount = float(request.form['amount'])
    t_type = request.form['type']
    location = request.form.get('location', 'Online')
    
    tx = Transaction(
        user_id=current_user.id,
        amount=amount,
        type=t_type,
        location=location,
        ip_address=request.remote_addr,
        detection_method='AI/Hybrid'
    )
    db.session.add(tx)
    db.session.flush() # Get tx.id
    
    # Run Fraud Engine
    risk_score, alerts = fraud_engine.generate_alerts(tx, current_user)
    tx.risk_score = risk_score
    if risk_score > 70: tx.is_anomaly = True
    
    for alert in alerts:
        db.session.add(alert)
    
    db.session.commit()
    log_audit(current_user.id, "Process Transaction", f"TX #{tx.id} - Risk Score: {risk_score}")
    
    flash(f"Transaction processed. Risk Score: {risk_score}", 'info')
    return redirect(url_for('index'))

@app.route('/scan_receipt', methods=['POST'])
@login_required
def scan_receipt():
    # In a real app, handle file upload here. 
    # For simulation, we just trigger the OCR scanner.
    scan_result = OCRScanner.scan_receipt("dummy_path.jpg")
    if scan_result:
        # Create a transaction from the scan
        tx_data = scan_result['data']
        flash(f"OCR Scan Successful! Merchant: {tx_data['merchant']}, Amount: ${tx_data['amount']}", 'success')
        # Redirect to index to show flash, or auto-add
        return redirect(url_for('index'))
    return "Scan failed", 400

@app.route('/audit_logs')
@login_required
def audit_view():
    if current_user.role != 'Admin':
        return "Access Denied", 403
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('audit_logs.html', logs=logs)

@app.route('/generate_report')
@login_required
def generate_report():
    """
    Objective: Automated Report Generation
    Exports a comprehensive audit report of all transactions and flagged anomalies.
    """
    if current_user.role not in ['Admin', 'Auditor']:
        flash('Unauthorized: Only Auditors or Administrators can generate reports.', 'error')
        return redirect(url_for('index'))

    try:
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Audit ID', 'Timestamp', 'Amount (E)', 'Type', 'Location', 'Risk Score', 'Is Anomaly', 'Alerts Found'])
        
        # Data
        transactions = Transaction.query.all()
        for tx in transactions:
            alerts = ", ".join([a.reason for a in tx.alerts])
            # Ensure risk_score is handled safely if it's None
            risk_val = tx.risk_score if tx.risk_score is not None else 0.0
            
            writer.writerow([
                tx.id, 
                tx.timestamp.strftime('%Y-%m-%d %H:%M:%S') if tx.timestamp else 'N/A', 
                tx.amount, 
                tx.type, 
                tx.location, 
                f"{risk_val:.1f}%", 
                "YES" if tx.is_anomaly else "No",
                alerts
            ])
        
        log_audit(current_user.id, "Generate Audit Report", f"Exported {len(transactions)} records")
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-disposition": f"attachment; filename=OAG_Audit_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        flash(f"Error generating report: {str(e)}", 'error')
        return redirect(url_for('index'))

# --- DB Initialization ---

@app.cli.command("init-db")
def init_db():
    db.create_all()
    # Create default Admin
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@guard.ai',
            password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
            role='Admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("Database initialized with Admin user.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Seed admin if needed
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@guard.ai',
                password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                role='Admin'
            )
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True, port=5001)
