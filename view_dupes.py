from pymongo import MongoClient

# Config
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "muse_memory"
COLLECTION_NAME = "muse_conversations"
PAIR_LIST_FILE = "dupe_pairs.txt"  # Your export (from the previous script)

client = MongoClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]

def parse_pair_line(line):
    # Expect: <id1> <==> <id2> | distance: <num>
    if "<==>" not in line:
        return None
    parts = line.split()
    if len(parts) < 5:
        return None
    mid1 = parts[0]
    mid2 = parts[2]
    try:
        dist = int(parts[5])
    except Exception:
        dist = None
    return (mid1, mid2, dist)

with open(PAIR_LIST_FILE, "r") as f:
    lines = f.readlines()

pairs = [parse_pair_line(line) for line in lines if parse_pair_line(line)]
print(f"Parsed {len(pairs)} dupe pairs.")

for mid1, mid2, dist in pairs:
    msg1 = collection.find_one({"message_id": mid1})
    msg2 = collection.find_one({"message_id": mid2})
    text1 = (msg1["message"][:200] + "…") if msg1 and msg1.get("message") else "[MISSING]"
    text2 = (msg2["message"][:200] + "…") if msg2 and msg2.get("message") else "[MISSING]"
    print(f"\n---\nPair ({dist}): {mid1} <==> {mid2}\n 1: {repr(text1)}\n 2: {repr(text2)}\n")
