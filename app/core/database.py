from google.cloud import firestore

def get_firestore_client():
    return firestore.Client()

"""Returns a reference to a Firestore collection"""
def get_collection(collection_name):
    db = get_firestore_client()
    return db.collection(collection_name)

