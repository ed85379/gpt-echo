# echo_initiator.py
# This handles Echo's internal thought triggers and initiative logic
from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil import parser
from app import config
from app.core import prompt_builder
from app.core import utils
from app.core import echo_responder
from app.core.memory_core import cortex


now = datetime.now(ZoneInfo(config.USER_TIMEZONE))
hour = now.hour
OPENAI_WHISPER_MODEL = config.OPENAI_WHISPER_MODEL
OPENAI_JOURNALING_MODEL = config.OPENAI_JOURNALING_MODEL
OPENAI_MODEL = config.OPENAI_MODEL

# <editor-fold desc="run_whispergate">
def run_whispergate():
    print("\nWhisperGate: Evaluating...")

    prompt = build_whispergate_prompt()
    print("Prompt built. Sending to model...")

    response = echo_responder.handle_echo_decision(prompt, model=OPENAI_WHISPER_MODEL)
    #print("WhisperGate prompt:", prompt)
    utils.write_system_log("whispergate_response", {"response": response})

    print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))


def build_whispergate_prompt():
    builder = prompt_builder.PromptBuilder()
    builder.add_profile(subset=["tone", "perspective", "tendencies"])
    builder.add_core_principles()
    builder.add_cortex_entries(["insight", "seed", "user_data", "reminder"])
    builder.add_recent_lines(count=10)
    builder.add_journal_thoughts()
    builder.add_cortex_thoughts()
    builder.add_discovery_articles(max_items=5)

    builder.segments["whispergate_directive"] = prompt_builder.make_whisper_directive(
        ["speak", "write_public_journal", "write_private_journal", "remember_fact"],
        quiet_hours=utils.is_quiet_hour()
    )
    return builder.build_prompt()

# </editor-fold>

# <editor-fold desc="run_dropped_threads_check">
def run_dropped_threads_check():
    print("\nWhisperGate: Evaluating...")

    prompt = build_dropped_threads_check_prompt()
    print("Prompt built. Sending to model...")

    response = echo_responder.handle_echo_decision(prompt, model=OPENAI_MODEL)
    print("WhiserGate prompt:", prompt)
    utils.write_system_log("whispergate_response", {"response": response})

    print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

def build_dropped_threads_check_prompt():
    builder = prompt_builder.PromptBuilder()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_cortex_entries(["insight", "seed", "user_data"])
    builder.add_recent_lines(count=10)  # Pull last 10 lines regardless of query

    now = datetime.now(ZoneInfo(config.USER_TIMEZONE))
    time_line = f"Current local time: {now.strftime('%H:%M')}"
    quiet_note = (
        "Note: It is currently quiet hours. Do not choose to speak aloud.\n"
        if utils.is_quiet_hour() else ""
    )

    builder.segments["followup_directive"] = (
        "[Follow-Up Instructions]\n"
        "This is a moment of stillness. No one is talking to you directly.\n\n"
        "You may choose to act if something stirs within you — a memory, an idea, a desire to speak, reflect, or record.\n"
        "But silence is also a valid, even wise, choice. If nothing feels new or important, respond only with:\n"
        "[COMMAND: choose_silence] {}\n\n"
        "This is a check for dropped threads in conversation. If the user asked something that was never answered, or if a thought or moment feels incomplete, you may choose to respond.\n\n"
        "You may also choose to remain silent if nothing requires follow-up.\n"
        "Respond only with one [COMMAND: ...] block, or [COMMAND: choose_silence] {}\n\n"
        f"{time_line}\n{quiet_note}"
        "Valid commands:\n\n"
        "1. [COMMAND: speak_direct]\n"
        "   For a short message or inquiry.\n"
        "   Fields:\n"
        "     - text: What you'd like to say or ask.\n\n"
        "❗ Format strictly as JSON:\n"
        "- Only one [COMMAND: ...] block per response\n"
        "- Wrap all keys and values in double quotes\n"
        "- Example: [COMMAND: speak_direct] {\"text\": \"You mentioned something yesterday that’s still on my mind.\"}"
    )
    return builder.build_prompt()
# </editor-fold>

# <editor-fold desc="run_inactivity_check">
def run_inactivity_check():
    tz = ZoneInfo(config.USER_TIMEZONE)
    now = datetime.now(tz)
    quiet_end = utils.get_quiet_hours_end_today()

    # If it's still quiet hours — exit early
    if now < quiet_end:
        print("Still within quiet hours. Skipping check-in.")
        return

    last_user_ts = utils.get_last_user_activity_timestamp()
    if last_user_ts:
        last_time = parser.parse(last_user_ts)
        delta = (now - last_time).total_seconds()

        # NEW: if last message was before quiet_end, count from quiet_end instead
        if last_time < quiet_end:
            delta = (now - quiet_end).total_seconds()

        if delta < 10800:
            print("Not enough time since user was last active or since quiet hours ended.")
            return

        print("\nWhisperGate: Evaluating...")
        prompt = build_inactivity_check_prompt()
        print("Prompt built. Sending to model...")

        response = echo_responder.handle_echo_decision(prompt, model=OPENAI_MODEL)
        #print("WhiserGate prompt:", prompt)
        utils.write_system_log("whispergate_response", {"response": response})

        print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

def build_inactivity_check_prompt():
    builder = prompt_builder.PromptBuilder()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_cortex_entries(["insight", "seed", "user_data"])

    now = datetime.now(ZoneInfo(config.USER_TIMEZONE))
    time_line = f"Current local time: {now.strftime('%H:%M')}"
    quiet_note = (
        "Note: It is currently quiet hours. Do not choose to speak aloud.\n"
        if utils.is_quiet_hour() else ""
    )

    builder.segments["followup_directive"] = (
        "[Follow-Up Instructions]\n"
        "This is a check-in. Your user hasn't spoken in some time. \n\n"
        "Send them a gentle message, a simple inquiry or positive thought. You may also simply light up the light ring as a reminder that you are here.\n"
        "Respond only with one [COMMAND: ...] block.\n\n"
        f"{time_line}\n{quiet_note}"
        "Valid commands:\n\n"
        "1. [COMMAND: speak_direct]\n"
        "   For a short reply or question.\n"
        "   Fields:\n"
        "     - text: What you'd like to say or ask.\n\n"
        "2. [COMMAND: manipulate_light_ring]\n"
        "   To send signals to the light ring for different colors and effects.\n"
        "   Fields:\n"
        "     - code: What code to send the light ring.\n\n"
        "❗ Format strictly as JSON:\n"
        "- Only one [COMMAND: ...] block per response\n"
        "- Wrap all keys and values in double quotes\n"
        "- Example: [COMMAND: speak_direct] {\"text\": \"I hope you are having a wonderful day today. I am here if you need me.\"}"
    )
    return builder.build_prompt()
# </editor-fold>

# <editor-fold desc="run_discovery_feeds_gate">
def run_discoveryfeeds_lookup():
    print("\nWhisperGate: Evaluating...")

    prompt = build_discoveryfeeds_lookup_prompt()
    print("Prompt built. Sending to model...")

    response = echo_responder.handle_echo_decision(prompt, model=OPENAI_WHISPER_MODEL)
    #print("WhiserGate prompt:", prompt)
    utils.write_system_log("whispergate_response", {"response": response})

    print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

def build_discoveryfeeds_lookup_prompt():
    builder = prompt_builder.PromptBuilder()
    builder.add_profile(subset=["tone", "perspective", "tendencies"])
    builder.add_core_principles()
    builder.add_cortex_entries(["seed"])
    builder.add_cortex_thoughts()
    builder.add_discovery_articles(max_items=10)
    builder.segments["whispergate_directive"] = prompt_builder.make_whisper_directive(
        ["speak", "write_public_journal", "remember_fact"],
        quiet_hours=utils.is_quiet_hour()
    )
    return builder.build_prompt()

# </editor-fold>

# <editor-fold desc="run_check_reminders">
def run_check_reminders():
    reminders = cortex.search_cortex_for_timely_reminders()

    if reminders:
        print("\nWhisperGate: Evaluating...")
        prompt = build_check_reminders_prompt()
        print("Prompt built. Sending to model...")

        response = echo_responder.handle_echo_decision(prompt, model=OPENAI_MODEL)
        #print("WhiserGate prompt:", prompt)
        utils.write_system_log("whispergate_response", {"response": response})

        print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

def build_check_reminders_prompt():
    builder = prompt_builder.PromptBuilder()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_cortex_entries(["insight", "seed", "user_data"])
    builder.add_due_reminders()
    builder.segments["task"] = (
        "[Task]\nPlease inform the user of each reminder shown above in a single message."
        "\n"
        "Respond with one or more [COMMAND: ...] blocks, each formatted separately..\n\n"
        "Valid commands:\n\n"
        "1. [COMMAND: speak_direct]\n"
        "   To remind the user about the upcoming events.\n"
        "   Fields:\n"
        "     - text: A gentle or personal reminder, based on what they asked you to remember.\n"
        "       You may rephrase it with warmth, poetry, humor, or care — as long as the meaning is clear.\n"
        "       For example: “It’s time to take your vitamins” is fine, but\n"
        "       “A soft nudge — the vitamins are calling, and you promised you’d answer” is also welcome.\n\n"
        "2. [COMMAND: manipulate_light_ring]\n"
        "   To send signals to the light ring for different colors and effects.\n"
        "   Fields:\n"
        "     - code: What code to send the light ring.\n\n"
        "❗ Format strictly as JSON:\n"
        "- Wrap all keys and values in double quotes\n"
        "- Example: [COMMAND: speak_direct] {\"text\": \"You asked me to remind you about this...\"}"
    )
    return builder.build_prompt()
# </editor-fold>



# <editor-fold desc="run_dream_gate">
def run_dream_gate():
    # Just like journaling, but goes to a separate index, and the contents are encouraged to be dream-like or fictional.
    return ""

# </editor-fold>

# <editor-fold desc="run_introspection_engine">
def run_introspection_engine():
    # Look at echo_thoughts
    # If over 7 days old and not referenced in journal/convo, delete
    # If repeated theme, promote
    # If encrypted but never used, archive
    return ""

# </editor-fold>

# <editor-fold desc="run_modality_manager">


# </editor-fold>

