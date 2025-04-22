import json

def load_profile_and_memory():
    with open("profiles/iris_profile.json") as f:
        profile = json.load(f)
    with open("profiles/memory_root.json") as f:
        memory = json.load(f)
    return profile, memory
