import datetime

def log_message(message):
    timestamp = datetime.datetime.utcnow().isoformat()
    with open("logs/echo_log.jsonl", "a") as f:
        f.write(f"{{\"timestamp\": \"{timestamp}\", \"message\": \"{message}\"}}\n")
