from app.prompt_builder import build_prompt
from app.dispatcher import dispatch_message
from app.memory_store import load_profile_and_memory
from app.log_utils import log_message
from app.chatgpt_api import get_openai_response

def should_speak():
    return True  # Placeholder logic

def run_echo_loop():
    profile, memory = load_profile_and_memory()
    prompt = build_prompt(profile, memory)
    response = get_openai_response(prompt)
    dispatch_message(response)
    log_message(response)

if __name__ == "__main__":
    run_echo_loop()
