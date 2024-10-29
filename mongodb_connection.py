from pymongo.mongo_client import MongoClient
import certifi

uri = "mongodb+srv://oliverostojic:903TL6h24xAYGHSX@healthcare-db.llehg.mongodb.net/?retryWrites=true&w=majority&appName=healthcare-db"
client = MongoClient(uri, tlsCAFile=certifi.where())
db = client["healthcare-db"]
users_collection = db["users"]


def test_connection():
    try:
        client.admin.command("ping")
        print("Pinged your deployment. Successfully connected to MongoDB!")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
