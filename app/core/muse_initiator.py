# muse_initiator.py
# This handles Muse's internal thought triggers and initiative logic
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from app.config import muse_settings
from app.core.utils import write_system_log
from app.core.time_location_utils import get_quiet_hours_end_today, get_last_user_activity_timestamp, _load_user_location
from app.core.muse_responder import handle_muse_decision
from app.core import prompt_profiles
from app.core.reminders_core import handle_edit, search_for_timely_reminders
from app.core.threads_core import apply_thread_summary
from app.services.openai_client import continuity_openai_client, get_openai_response


# <editor-fold desc="run_whispergate">
async def run_whispergate():
    print("\nWhisperGate: Evaluating...")

    dev_prompt, user_assistant_messages, tool_bundle = prompt_profiles.build_whispergate_prompt()

    print("Prompt built. Sending to model...")

    response = await handle_muse_decision(dev_prompt=dev_prompt, user_assistant_messages=user_assistant_messages, tool_bundle=tool_bundle, client=continuity_openai_client, model=muse_settings.get_section("llm_config").get("OPENAI_WHISPER_MODEL"), source="whispergate")
    #print("WhisperGate prompt:", prompt)
    write_system_log(level="info", module="core", component="initiator", function="run_whispergate",
                           action="whispergate_response", response=response)

    print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

# </editor-fold>




# <editor-fold desc="run_discovery_feeds_gate">
async def run_discoveryfeeds_lookup():
    print("\nWhisperGate: Evaluating...")
    dev_prompt, user_assistant_messages, tool_bundle = prompt_profiles.build_discoveryfeeds_prompt()
    print("Prompt built. Sending to model...")

    response = await handle_muse_decision(dev_prompt=dev_prompt, user_assistant_messages=user_assistant_messages, tool_bundle=tool_bundle, client=continuity_openai_client, model=muse_settings.get_section("llm_config").get("OPENAI_WHISPER_MODEL"), source="discovery")
    #print("WhiserGate prompt:", prompt)

    write_system_log(level="info", module="core", component="initiator", function="run_discoveryfeeds_lookup",
                           action="whispergate_response", response=response)

    print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

# </editor-fold>

# <editor-fold desc="run_check_reminders">
async def run_check_reminders():
    muse_features = muse_settings.get_section("muse_features") or {}
    if not muse_features.get("ENABLE_REMINDERS", True):
        return  # reminders globally disabled
    loc = _load_user_location()
    due_reminders = search_for_timely_reminders()
    if due_reminders:
        print("\nWhisperGate: Evaluating...")
        dev_prompt, user_assistant_messages, tool_bundle = prompt_profiles.build_check_reminders_prompt(due_reminders=due_reminders)
        print("Prompt built. Sending to model...")

        response = await handle_muse_decision(dev_prompt=dev_prompt, user_assistant_messages=user_assistant_messages, tool_bundle=tool_bundle, client=continuity_openai_client, model=muse_settings.get_section("llm_config").get("OPENAI_MODEL"), source="reminder", whispergate_data={"reminders": due_reminders})
        # print("WhisperGate prompt:", prompt)

        write_system_log(level="info", module="core", component="initiator", function="run_check_reminders",
                         action="whispergate_response", response=response)

        print("WhisperGate response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))

        # ---- Update reminder for each reminder fired to add new early_notification calculations----
        base_time = datetime.now(ZoneInfo(loc.timezone)) + timedelta(minutes=2)
        for reminder in due_reminders:
            handle_edit({"id": reminder["id"]}, base_time=base_time)
            print(f"Updated next early_notification for {reminder.get('text', '')} ({reminder['id']})")


# </editor-fold>

# <editor-fold desc="run_thread_summarization">
async def run_thread_summarization(thread_id):
    print("\nThread summarization starting...")

    dev_prompt, user_assistant_messages, tool_bundle, messages_meta = prompt_profiles.build_thread_summarization_prompt(
        allow_summarization=False,
        thread_id=thread_id,
        )

    print("Prompt built. Sending to model...")
    response = await get_openai_response(
        dev_prompt,
        client=continuity_openai_client,
        user_assistant_messages=user_assistant_messages,
        prompt_type="summarizer",
        images=None,
        model=muse_settings.get_section("llm_config").get("OPENAI_WHISPER_MODEL"),
        tools=tool_bundle["tools"],
        tool_choice=tool_bundle["tool_choice"],
        handlers=tool_bundle["handlers"],
        ui_meta=tool_bundle["ui_meta"],
    )


    result = apply_thread_summary(thread_id, response, messages_meta["extended_history"])

    write_system_log(level="info", module="core", component="initiator", function="run_thread_summarization",
                           action="summarizer_response", response=response)

    print("Thread summarization response:", response[:200].replace("\n", " ") + ("..." if len(response) > 200 else ""))
    return result

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

