from pymongo import MongoClient
from decouple import config

# Establish MongoDB connection using settings
client = MongoClient(config("MONGODB_URI"))
db = client[config("MONGODB_NAME")]


def get_collection(collection_name):
    
    return db[collection_name]

