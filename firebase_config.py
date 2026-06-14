# firebase_config.py
import firebase_admin
from firebase_admin import credentials, firestore
import os
import streamlit as st

# Securely initialize the Firebase application instance
if not firebase_admin._apps:
    # 1. First, check if running in the cloud using Streamlit TOML Secrets
    if "firebase" in st.secrets:
        # Streamlit automatically parses TOML sections into a dictionary!
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    # 2. Fallback to local file look-up if running on your PC
    elif os.path.exists("firebase_credentials.json"):
        cred = credentials.Certificate("firebase_credentials.json")
        firebase_admin.initialize_app(cred)
    else:
        raise FileNotFoundError("CRITICAL ERROR: Firebase configuration credentials not found.")

db = firestore.client()

# =====================================================================
# FIRESTORE ADVANCED DATABASE METHODS
# =====================================================================

def save_user_to_firebase(username, fullname, password, provider="Manual"):
    """Records login identity profiles safely into the 'users' cloud collection."""
    try:
        user_ref = db.collection("users").document(username)
        user_ref.set({
            "fullname": fullname,
            "password": password if password else "N/A (Authenticated via Google Security Portal)",
            "auth_provider": provider
        })
        return True
    except Exception as e:
        print(f"Error saving user account profile: {e}")
        return False

def get_user_from_firebase(username):
    """Fetches manual profile profiles to verify login credentials."""
    try:
        user_ref = db.collection("users").document(username).get()
        if user_ref.exists:
            return user_ref.to_dict()
        return None
    except Exception as e:
        print(f"Error reading user records: {e}")
        return None

def log_patient_report(operator_username, patient_name, risk_score, patient_metrics_dict):
    """Generates an explicit document record matching the logged operator and clinical metrics."""
    try:
        clean_metrics = {str(k): str(v) for k, v in patient_metrics_dict.items()}
        report_ref = db.collection("patient_reports").document()
        report_ref.set({
            "operator_username": operator_username,
            "patient_name": patient_name if patient_name else "Anonymous Patient",
            "risk_probability": float(risk_score),
            "clinical_metrics": clean_metrics,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception as e:
        print(f"Error writing clinical report to ledger: {e}")
        return False

def get_operator_reports(operator_username):
    """Queries Firestore to fetch all historical patient diagnostic reports."""
    try:
        reports_list = []
        docs = db.collection("patient_reports").where("operator_username", "==", operator_username).stream()
        for doc in docs:
            data = doc.to_dict()
            metrics = data.get("clinical_metrics", {})
            reports_list.append({
                "Report ID": doc.id,
                "Patient Name": data.get("patient_name", "Anonymous"),
                "Risk Score": f"{data.get('risk_probability', 0.0):.1f}%",
                "Age": metrics.get("Age", "N/A"),
                "Gender": metrics.get("Gender", "N/A"),
                "Cholesterol": metrics.get("chol", "N/A"),
                "Max Heart Rate": metrics.get("thalach", "N/A")
            })
        return reports_list
    except Exception as e:
        print(f"Error querying patient reports: {e}")
        return []

# =====================================================================
# TEMPORAL AUTHENTICATION TRACKING METHODS
# =====================================================================

def log_user_login(username, fullname):
    """Logs a new login session with a server-side timestamp and returns the generated session ID."""
    try:
        session_ref = db.collection("login_history").document()
        session_ref.set({
            "username": username,
            "fullname": fullname,
            "login_time": firestore.SERVER_TIMESTAMP,
            "logout_time": "Active Session"
        })
        return session_ref.id
    except Exception as e:
        print(f"Error writing login session timestamp: {e}")
        return None

def log_user_logout(session_id):
    """Locates the targeted active session entry document and updates the logoff metric."""
    if not session_id:
        return False
    try:
        session_ref = db.collection("login_history").document(session_id)
        session_ref.update({
            "logout_time": firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception as e:
        print(f"Error updating logout timestamp: {e}")
        return False
