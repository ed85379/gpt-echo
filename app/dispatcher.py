def dispatch_message(message):
    print(f"Dispatching: {message}")
    with open("logs/echo_log.jsonl", "a") as f:
        f.write(message + "\n")
