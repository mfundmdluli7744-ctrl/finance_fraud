import numpy as np
from sklearn.ensemble import IsolationForest
import pandas as pd
from datetime import datetime, timedelta
import json

class FraudEngine:
    def __init__(self, db_session, models):
        self.db = db_session
        self.models = models

    def calculate_risk_score(self, transaction, user):
        """
        Calculates a risk score based on Office of the Auditor General (Eswatini) standards.
        """
        score = 0
        reasons = []

        # 1. Procurement Thresholds (Auditor General Mbabane Standards)
        if transaction.amount > 100000:
            score += 60
            reasons.append(f"Exceeds Mbabane Tender Board approval threshold (E100k+)")
        elif transaction.amount > 15000:
            score += 30
            reasons.append(f"Significant procurement: Requires 3 competitive quotes")

        # 2. Duplicate Transaction Detection (Double Billing Check)
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        duplicates = [t for t in user.transactions if t.id != transaction.id 
                     and t.amount == transaction.amount 
                     and t.type == transaction.type
                     and t.timestamp > one_day_ago]
        if duplicates:
            score += 40
            reasons.append(f"Potential duplicate payment (Same amount/type within 24h)")

        # 3. Behavioral Outliers (Deviation from Historical Spending)
        history = [t.amount for t in user.transactions if t.id != transaction.id]
        if len(history) > 5:
            avg = np.mean(history)
            std = np.std(history)
            if transaction.amount > (avg + 3 * std):
                score += 35
                reasons.append("Extreme statistical outlier compared to department history")

        # 4. Elevated Frequency (Policy Compliance)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_txs = [t for t in user.transactions if t.timestamp > one_hour_ago]
        if len(recent_txs) > 5:
            score += 20
            reasons.append("Unusual frequency of manual data entry")

        # Normalize score to 100
        final_score = min(max(score, 0), 100)
        
        # Determine Severity
        severity = "Low"
        if final_score > 70:
            severity = "High"
        elif final_score > 30:
            severity = "Medium"

        return final_score, reasons, severity

    def get_geo_risk(self, ip_address):
        """
        Simulated Geo-location risk detection.
        In a real app, this would use a GeoIP API.
        """
        # Mock high-risk IP ranges or countries
        high_risk_prefixes = ['192.168.100', '10.0.99'] 
        for prefix in high_risk_prefixes:
            if ip_address.startswith(prefix):
                return 30, "Transaction initiated from high-risk subnet"
        return 0, None

    def generate_alerts(self, transaction, user):
        risk_score, reasons, severity = self.calculate_risk_score(transaction, user)
        geo_score, geo_reason = self.get_geo_risk(transaction.ip_address)
        
        if geo_score > 0:
            risk_score = min(risk_score + geo_score, 100)
            reasons.append(geo_reason)
            if risk_score > 70: severity = "High"

        alerts = []
        if risk_score > 30:
            for reason in reasons:
                alert = self.models.Alert(
                    transaction_id=transaction.id,
                    reason=reason,
                    severity=severity,
                    status='Open'
                )
                alerts.append(alert)
        
        return risk_score, alerts
