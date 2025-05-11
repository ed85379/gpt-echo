from flask import Flask, request, render_template, redirect, url_for, jsonify
import requests
from urllib.parse import urljoin
from app import config

THRESHOLD_API_URL = config.THRESHOLD_API_URL

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

# Redirect home "/" to /chat
@app.route("/")
def home():
    return redirect(url_for('chat_page'))

# CHAT
@app.route("/chat", methods=["GET"])
def chat_page():
    return render_template("chat.html", api_url=THRESHOLD_API_URL)

@app.route("/chat", methods=["POST"])
def chat_send():
    user_input = request.form.get("prompt", "")
    if not user_input:
        return jsonify({"error": "No prompt provided"}), 400

    try:
        api_response = requests.post(
            urljoin(THRESHOLD_API_URL, "/api/talk"),
            json={"prompt": user_input}
        )
        api_response.raise_for_status()
        assistant_response = api_response.json().get("response", "")
    except Exception as e:
        print(f"Error contacting Threshold API: {e}")
        assistant_response = "Error reaching Threshold."

    return jsonify({"response": assistant_response})

# MEMORY
@app.route("/memory-store")
def memory_store_page():
    return render_template("memory-store.html", api_url=THRESHOLD_API_URL)

# SETTINGS
@app.route("/settings")
def settings_page():
    return render_template("settings.html")

# PROFILE
@app.route("/profile")
def profile_page():
    return render_template("profile.html")

# STATUS
@app.route("/status")
def status_page():
    return render_template("status.html")

