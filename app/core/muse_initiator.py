# muse_initiator.py
# This handles Muse's internal thought triggers and initiative logic
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dateutil import parser
from croniter import croniter
from app.config import muse_config
from app.core import utils
from app.core import muse_responder
from app.core.memory_core import cortex
from app.core import prompt_profiles


# <editor-fold desc="run_whispergate">
def run_whispergate():
    print("\nWhisperGate: Evaluating...")

    dev_prompt, user_prompt = prompt_profiles.build_whispergate_prompt()
    print("Prompt built. Sending to model...")

    response = muse_responder.handle_muse_decision(dev_prompt, user_prompt, model=muse_config.get("OPENAI_WHISPER_MODEL"), source="frontend")
    #print("WhisperGate prompt:", prompt)
    utils.write_system_log(level="info", module="core", component="initiator", function="run_whispergate",
                           action="whispergate_response", response=response)

    print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

# </editor-fold>

# <editor-fold desc="run_dropped_threads_check">
def run_dropped_threads_check():
    print("\nWhisperGate: Evaluating...")

    dev_prompt, user_prompt = prompt_profiles.build_dropped_threads_check_prompt(muse_config)
    print("Prompt built. Sending to model...")

    response = muse_responder.handle_muse_decision(dev_prompt, user_prompt, model=muse_config.get("OPENAI_MODEL"))
    #print("WhiserGate prompt:", prompt)
    utils.write_system_log(level="info", module="core", component="initiator", function="run_dropped_threads_check",
                           action="whispergate_response", response=response)

    print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

# </editor-fold>

# <editor-fold desc="run_inactivity_check">
def run_inactivity_check():
    # Get all times in UTC for consistent comparison
    now_utc = datetime.now(timezone.utc)

    # Get quiet_end in user timezone, convert to UTC
    quiet_end_local = utils.get_quiet_hours_end_today()
    quiet_end_utc = quiet_end_local.astimezone(ZoneInfo("UTC"))

    # If it's still quiet hours — exit early
    if now_utc < quiet_end_utc:
        print("Still within quiet hours. Skipping check-in.")
        return

    last_user_ts = utils.get_last_user_activity_timestamp()
    if last_user_ts:
        last_time = last_user_ts
        # Always ensure UTC timezone
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=ZoneInfo("UTC"))
        else:
            last_time = last_time.astimezone(ZoneInfo("UTC"))

        delta = (now_utc - last_time).total_seconds()

        # NEW: if last message was before quiet_end, count from quiet_end instead
        if last_time < quiet_end_utc:
            delta = (now_utc - quiet_end_utc).total_seconds()

        if delta < 10800:  # 3 hours
            print("Not enough time since user was last active or since quiet hours ended.")
            return

        print("\nWhisperGate: Evaluating...")
        dev_prompt, user_prompt = prompt_profiles.build_inactivity_check_prompt(muse_config)
        print("Prompt built. Sending to model...")

        response = muse_responder.handle_muse_decision(dev_prompt, user_prompt, model=muse_config.get("OPENAI_MODEL"), source="inactivity_checker")
        utils.write_system_log(level="info", module="core", component="initiator", function="run_inactivity_check",
                         action="whispergate_response", response=response)

        print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

# </editor-fold>

# <editor-fold desc="run_discovery_feeds_gate">
def run_discoveryfeeds_lookup():
    print("\nWhisperGate: Evaluating...")
    dev_prompt, user_prompt = prompt_profiles.build_discoveryfeeds_lookup_prompt()
    print("Prompt built. Sending to model...")

    response = muse_responder.handle_muse_decision(dev_prompt, user_prompt, model=muse_config.get("OPENAI_WHISPER_MODEL"), source="discovery")
    #print("WhiserGate prompt:", prompt)

    utils.write_system_log(level="info", module="core", component="initiator", function="run_discoveryfeeds_lookup",
                           action="whispergate_response", response=response)

    print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

# </editor-fold>

# <editor-fold desc="run_check_reminders">
from datetime import datetime
from zoneinfo import ZoneInfo

def run_check_reminders():
    reminders = cortex.search_cortex_for_timely_reminders()
    if reminders:
        print("\nWhisperGate: Evaluating...")
        dev_prompt, user_prompt = prompt_profiles.build_check_reminders_prompt()
        print("Prompt built. Sending to model...")

        response = muse_responder.handle_muse_decision(dev_prompt, user_prompt, model=muse_config.get("OPENAI_MODEL"), source="reminder")
        # print("WhisperGate prompt:", prompt)

        utils.write_system_log(level="info", module="core", component="initiator", function="run_check_reminders",
                         action="whispergate_response", response=response)

        print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

        # ---- Update last_triggered for each reminder fired ----
        now_str = datetime.now(ZoneInfo(muse_config.get("USER_TIMEZONE"))).isoformat()
        for reminder in reminders:
            cortex.edit_entry(reminder["_id"], {"last_triggered": now_str})
            print(f"Updated last_triggered for reminder {reminder.get('text', '')} ({reminder['_id']})")

# </editor-fold>



# <editor-fold desc="run_dream_gate">
def run_dream_gate():
    # Just like journaling, but goes to a separate index, and the contents are encouraged to be dream-like or fictional.
    return ""

# </editor-fold>

# <editor-fold desc="run_introspection_engine">
def run_introspection_engine():
    # Look at muse_thoughts
    # If over 7 days old and not referenced in journal/convo, delete
    # If repeated theme, promote
    # If encrypted but never used, archive
    return ""

# </editor-fold>

# <editor-fold desc="run_modality_manager">


# </editor-fold>

