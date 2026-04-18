from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from app.config import settings

client = MongoClient(settings.MONGODB_URL)
db = client[settings.DB_NAME]

# Collections
documents_collection = db["documents"]
chunks_collection = db["chunks"]
users_collection = db["users"]          # ← NEW: for JWT authentication

def check_db_connection():
    """Ping MongoDB to verify connection on startup."""
    try:
        client.admin.command("ping")
        print("MongoDB connected successfully!")
    except ConnectionFailure as e:
        print(f"MongoDB connection failed: {e}")
        raise e
