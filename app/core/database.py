import firebase_admin
from firebase_admin import credentials, firestore
from app.config import FIREBASE_CREDENTIALS

# Initialize Firebase with service account credentials
cred = credentials.Certificate(FIREBASE_CREDENTIALS)
firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()

