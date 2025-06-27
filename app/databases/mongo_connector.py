# app/databases/mongo_connector.py

from pymongo import MongoClient, ASCENDING
from datetime import datetime

MONGO_URI = "mongodb://localhost:27017/"

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

    def find_documents(self, collection_name, query=None, projection=None, sort=None, sort_field=None, limit=None):
        cursor = self.db[collection_name].find(query or {}, projection)
        if sort_field:
            cursor = cursor.sort(sort_field, sort if sort is not None else 1)  # 1=ASC, -1=DESC
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    def find_one_document(self, collection_name, query=None, projection=None):
        return self.db[collection_name].find_one(query or {}, projection)

    def update_one_document(self, collection_name, filter_query, update_data):
        # Returns the updated document after the change
        return self.db[collection_name].find_one_and_update(
            filter_query,
            {"$set": update_data},
            return_document=True  # pymongo.ReturnDocument.AFTER
        )

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

    # Add more as needed


mongo = MongoConnector(uri=MONGO_URI, db_name="muse_memory")
mongo_system = MongoConnector(uri=MONGO_URI, db_name="muse_system")
