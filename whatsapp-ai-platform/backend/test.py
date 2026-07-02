import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Read MongoDB URI from environment
uri = os.getenv("MONGO_URI")

if not uri:
    raise ValueError("MONGO_URI not found. Please set it in your .env 
file.")

client = MongoClient(uri)

try:
    client.admin.command("ping")
    print("✅ Successfully connected to MongoDB Atlas!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
