# app/databases/mongo_connector.py

from pymongo import MongoClient, ASCENDING
from datetime import datetime
from app import config
from app.core import utils

class MongoConnector:
    def __init__(self, uri, db_name="muse_memory"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        # Example: self.db['muse_log']

    def get_collection(self, collection_name):
        return self.db[collection_name]

    def ensure_index(self, collection_name, field):
        self.db[collection_name].create_index([(field, ASCENDING)])

    def insert_log(self, collection_name, log_entry):
        self.db[collection_name].insert_one(log_entry)

    def insert_logs_bulk(self, collection_name, log_entries):
        self.db[collection_name].insert_many(log_entries)

    def find_logs(self, collection_name, query=None, limit=100, sort_field="timestamp", ascending=True):
        cursor = self.db[collection_name].find(query or {})
        if ascending:
            cursor = cursor.sort(sort_field, ASCENDING)
        else:
            cursor = cursor.sort(sort_field, -1)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    def update_logs(self, collection_name, filter_query, update_data):
        return self.db[collection_name].update_many(filter_query, {"$set": update_data})

    def move_logs(self, from_collection, to_collection, filter_query):
        docs = list(self.db[from_collection].find(filter_query))
        if docs:
            self.db[to_collection].insert_many(docs)
            self.db[from_collection].delete_many(filter_query)
        return len(docs)

    def count_logs(self, collection_name, filter_query=None):
        return self.db[collection_name].count_documents(filter_query or {})

    # Add more as needed!

# For use in your app
from app import config  # or wherever your Mongo settings are

mongo = MongoConnector(
    uri=config.MONGO_URI,
    db_name=config.MONGO_DBNAME if hasattr(config, "MONGO_DBNAME") else "muse_memory"
)
