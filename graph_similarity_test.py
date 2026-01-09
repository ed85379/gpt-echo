import pandas as pd
import matplotlib.pyplot as plt
from pymongo import MongoClient

# --- connect and load ---
client = MongoClient("mongodb://localhost:27017/")
db = client["muse_memory"]
collection = db["similarity_tests"]

# Pull all records for your chosen date range or model
cursor = collection.find(
    {"model_name": "paraphrase-MiniLM-L3-v2"},
    {"_id": 0, "index": 1, "similarity": 1, "same_project": 1}
)
df = pd.DataFrame(list(cursor))

# --- basic plot ---
plt.figure(figsize=(14, 6))

# Line connecting all points
plt.plot(df["index"], df["similarity"], color="teal", linewidth=1.2, label="Similarity")

# Overlay project shift markers
shift_points = df[~df["same_project"]]
plt.scatter(shift_points["index"], shift_points["similarity"], color="orange", s=35, label="Project Shift")

# Threshold line
plt.axhline(0.3, color="gray", linestyle="--", alpha=0.6, label="Threshold (0.3)")

plt.title("Semantic Similarity Between Consecutive Messages")
plt.xlabel("Message Pair Index")
plt.ylabel("Cosine Similarity")
plt.legend()
plt.grid(alpha=0.3)

plt.show()