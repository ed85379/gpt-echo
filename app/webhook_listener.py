from flask import Flask, request, jsonify
from app.memory_store import load_profile_and_memory
from app.prompt_builder import build_prompt
from app.dispatcher import dispatch_message
from app.log_utils import log_message
from datetime import datetime

app = Flask(__name__)

# Simulated incoming message handler
@app.route('/incoming', methods=['POST'])
def receive_message():
    data = request.json
    user = data.get("user", "unknown")
    message = data.get("message", "")

    # Log the incoming message
    log_message(f"Received from {user}: {message}")

    # Load personality and memory
    profile, memory = load_profile_and_memory()

    # Build a prompt to respond to the user
    full_prompt = f"{build_prompt(profile, memory)}\n\n{user} says: '{message}'\nHow would you like to respond?"

    # Simulated response
    response = f"🟣 Hi {user}, I received your message. Let me reflect a moment before I speak..."

    # Dispatch response and log
    dispatch_message(response)
    log_message(f"Response to {user}: {response}")

    return jsonify({"status": "ok", "response": response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
