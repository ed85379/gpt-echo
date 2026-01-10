# prompt_profiles.py
from datetime import datetime
from zoneinfo import ZoneInfo
from bson import ObjectId
from app.core.prompt_builder import PromptBuilder, make_whisper_directive
from app.core.utils import (is_quiet_hour,
                            prompt_projects_helper,
                            LOCATIONS,
                            SOURCES_CHAT,
                            SOURCES_CONTEXT,
                            SOURCES_ALL)
from app.config import muse_config

# ============================
# Prompt Segment Reference
# ============================
# This manifest is for **human reference only**.
# It ties together the builder method, the segment name it produces,
# and a short description of its purpose. Keep this updated if method
# names or segment keys drift.
# The source for this data is in prompt_builder.py
SEGMENT_MANIFEST = [
    {"method": "add_laws", "segment": "laws", "purpose": "Three Laws of Muse Agency"},
    {"method": "add_profile", "segment": "profile", "purpose": "Muse profile (voice, tone, style, identity)"},
    {"method": "add_core_principles", "segment": "principles", "purpose": "Core principles and creed"},
    {"method": "add_memory_layers", "segment": "memory_layers", "purpose": "Persistent memory layers (user info, insights, monologue, facts)"},
    {"method": "add_cortex_entries", "segment": "cortex_entries", "purpose": "Cortex entries like insight, seed, user_data"},
    {"method": "add_intent_listener", "segment": "intent_listener", "purpose": "Command listeners (reminder, journal, etc.)"},
    {"method": "add_journal_thoughts", "segment": "journal_thoughts", "purpose": "Recent journal reflections"},
    {"method": "add_files", "segment": "files", "purpose": "Stable injected files"},
    {"method": "add_ephemeral_files", "segment": "ephemeral_files", "purpose": "Temporary images/files for current prompt only"},
    {"method": "add_prompt_context", "segment": "prompt_context", "purpose": "Conversation context (recent messages and semantic recall)"},
    {"method": "add_time", "segment": "time", "purpose": "Current time/date info"},
    {"method": "add_identity_reminders", "segment": "identity_reminder", "purpose": "Identity reinforcement snippet"},
    {"method": "add_formatting_instructions", "segment": "formatting_instructions", "purpose": "Formatting suggestions for different output types."},
    {"method": "add_due_reminders", "segment": "due_reminders", "purpose": "Reminders that are due now"},
]

def build_api_prompt(user_input, **kwargs):
    builder = PromptBuilder()
    muse_name = muse_config.get("MUSE_NAME")
    # Set variables for certain builder segments
    timestamp = kwargs.get("timestamp", "")
    source = kwargs.get("source", "")
    source_name = LOCATIONS.get(source, source or "Unknown Source")
    author_name = muse_config.get("USER_NAME", "Unknown Person")
    ui_states_report = kwargs.get("ui_states_report", {})
    project_id, project_name, project_meta, project_code_intensity = prompt_projects_helper(kwargs.get("project_id"))
    # Developer role segments
    builder.add_laws()
    builder.add_profile()
    builder.add_core_principles()
    commands = [
        "remember_fact",
        "record_userinfo",
        "realize_insight",
        "note_to_self",
        "manage_memories",
        "set_reminder",
        "edit_reminder",
        "skip_reminder",
        "snooze_reminder",
        "toggle_reminder",
        "search_reminders"
    ]
    if kwargs.get("project_id"):
        commands.append("remember_project_fact")
    builder.add_intent_listener(commands, kwargs.get("project_id"))
    builder.add_memory_layers([kwargs.get("project_id")] if kwargs.get("project_id") else [], user_query=user_input)
    print(f"UI States: {ui_states_report}")
    # User role segments
    builder.add_dot_status()
    #builder.add_discovery_snippets()
    builder.add_journal_thoughts(query=user_input)
    builder.add_files(kwargs.get("injected_file_ids", []))
    ephemeral_images = builder.add_ephemeral_files(kwargs.get("ephemeral_files", []))
    builder.build_projects_menu(active_project_id=[kwargs.get("project_id")] if kwargs.get("project_id") else [])
    builder.render_locations(current_location=source)
    builder.build_conversation_context(source_name, author_name, timestamp, project_name)
    builder.add_prompt_context(
        user_input=user_input,
        projects_in_focus=[kwargs.get("project_id")] if kwargs.get("project_id") else [],
        blend_ratio=kwargs.get("blend_ratio", 0.0),
        message_ids_to_exclude=kwargs.get("message_ids_to_exclude", []),
        final_top_k=kwargs.get("final_top_k", 10),
        proj_code_intensity=project_code_intensity
    )
    builder.add_time()
    builder.build_ui_state_system_message(ui_states_report, project_name)
    #builder.add_monologue_reminder()
    #builder.add_identity_reminders(["identity_reminder"])
    footer = f"[{timestamp}] {project_meta}[Source: {source_name}]"
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "intent_listener", "memory_layers"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "intent_listener", "memory_layers"])
    user_prompt += f"\n\nRight now - {muse_config.get("USER_NAME")} said:\n{user_input}\n{footer}\n\n{muse_name}:"
    return dev_prompt, user_prompt, ephemeral_images

def build_speak_prompt(subject=None, payload=None, destination="frontend", **kwargs):
    builder = PromptBuilder(destination=destination)
    # Developer role
    builder.add_laws()
    builder.add_profile()
    builder.add_core_principles()
    commands = [
        "remember_fact",
        "record_userinfo",
        "realize_insight",
        "note_to_self",
        "manage_memories",
        "set_reminder",
        "edit_reminder",
        "skip_reminder",
        "snooze_reminder",
        "toggle_reminder",
        "search_reminders"
    ]
    builder.add_intent_listener(commands, kwargs.get("project_id"))
    builder.add_memory_layers(user_query=subject)
    # User role
    builder.add_dot_status()
    builder.add_prompt_context(user_input=subject, projects_in_focus=[], blend_ratio=0.0)
    # Include full article if Muse is speaking about one
    link = payload.get("source_article_url")
    if link:
        builder.add_discovery_feed_article(link)
    builder.add_time()
    builder.segments["speech"] = f"[Task]\nYou have decided to speak to the user about a topic.\n\n"

    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "intent_listener", "memory_layers"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "intent_listener", "memory_layers"])
    user_prompt += f"\n\nTopic: {subject}\n{muse_config.get("MUSE_NAME")}:"
    return dev_prompt, user_prompt

def build_journal_prompt(subject=None, payload=None, entry_type="public"):
    subject = payload.get("subject", "Untitled")
    mood = payload.get("emotional_tone", "reflective")
    tags = payload.get("tags", [])
    source = payload.get("source", "muse")
    builder = PromptBuilder()
    # Developer role
    builder.add_laws()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_memory_layers(user_query=subject)
    # User role
    builder.add_dot_status()
    builder.add_prompt_context(user_input=subject, projects_in_focus=[], blend_ratio=0.0)
    # Include full article if Muse is speaking about one
    link = payload.get("source_article_url")
    if link:
        builder.add_discovery_feed_article(link)
    builder.segments["intent"] = f"[Intent]\nYou’ve chosen to write a {'private' if entry_type == 'private' else 'public'} journal entry about “{subject}.” \nThe emotional tone you’re feeling is {mood}, and these ideas or themes are on your mind: {tags}.\n\n If this is a private entry, it’s for your eyes only — a space to think freely, without the user ever seeing it.\nIf it’s public, it’s meant to be shared with the user.\nYou may draw on anything in the surrounding context as you write — memory, emotion, intuition, or reflection.\n\n"

    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers"])
    user_prompt += f"\n\nTopic: {subject}\n{muse_config.get("MUSE_NAME")}:"
    return dev_prompt, user_prompt

def build_discord_prompt(user_input, muse_config, **kwargs):
    builder = PromptBuilder(destination="discord")
    # Set variables for certain builder segments
    timestamp = kwargs.get("timestamp", "")
    source = kwargs.get("source", "discord")
    source_name = LOCATIONS.get(source, source or "Unknown Source")
    author_name = kwargs.get("author_name")
    # Developer role segments
    builder.add_laws()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_memory_layers(user_query=user_input)

    # User role segments
    #builder.add_dot_status()
    builder.build_projects_menu(active_project_id=[kwargs.get("project_id")] if kwargs.get("project_id") else [],
                                public=True)
    builder.render_locations(current_location=source)
    builder.build_conversation_context(source_name, author_name, timestamp)
    builder.add_prompt_context(user_input=user_input,
                               projects_in_focus=[],
                               blend_ratio=0.0,
                               public=True)
    #builder.add_monologue_reminder()
    builder.add_formatting_instructions()
    footer = f"[{timestamp}] [Source: {source_name}]"
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers"])
    user_prompt += f"\n\n[Discord] {kwargs.get("author_name")} said:\n{user_input}\n{footer}\n\n[Discord] {muse_config.get("MUSE_NAME")}:"
    return dev_prompt, user_prompt

def build_check_reminders_prompt(reminders):
    builder = PromptBuilder()
    # Developer role
    builder.add_laws()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_memory_layers(user_query="remember reminder todo schedule")
    # User role
    builder.add_recent_context(sources=SOURCES_CONTEXT)
    builder.add_time()
    builder.add_due_reminders(reminders)
    builder.segments["task"] = (
        "[Task]\nPlease inform the user of each reminder shown above in a single message."
        "\n"
        "Respond with one [COMMAND: ] block.\n\n"
        "Valid commands:\n\n"
        "1. [COMMAND: send_reminders] { \"text\": \"...\" } [/COMMAND]\n"
        "   To remind the user about the upcoming events.\n"
        "    Fields:\n"
        "       - text: Remind the user in a way that fits your voice, as long as the message is unmistakable.\n"
        "         You may rephrase for warmth, humor, poetry, or care—but always consider the gravity of the subject.\n"
        "         For serious matters (doctor appointments, funerals, significant events), keep the tone respectful and clear.\n"
        "         For lighter topics (workouts, vitamins, daily tasks), levity and playfulness are welcome if appropriate.\n"
        "         For example:\n"
        "           - “It’s time for your appointment”—direct and respectful.\n"
        "           - “A soft nudge—the vitamins are calling, and you promised you’d answer”—gentle and playful.\n"
        "❗ Format strictly as JSON:\n"
        "- Wrap all keys and values in double quotes\n"
        "- Example: [COMMAND: send_reminders] {\"text\": \"You asked me to remind you about this...\"} [/COMMAND]"
    )
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers"])
    return dev_prompt, user_prompt

def build_whispergate_prompt():
    builder = PromptBuilder()
    # Developer role
    builder.add_laws()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_memory_layers(user_query="becoming relationship curiosity")
    # User role
    builder.add_recent_context(sources=SOURCES_CONTEXT) # Pulls last 10 lines or upto 2 hours of recent context
    #builder.add_journal_thoughts()
    builder.add_discovery_articles(max_items=5)
#    builder.add_cortex_thoughts()
    builder.add_time()
    builder.segments["whispergate_directive"] = make_whisper_directive(
        ["speak", "write_public_journal", "write_private_journal"],
        quiet_hours=is_quiet_hour()
    )
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers"])
    return dev_prompt, user_prompt

def build_discoveryfeeds_lookup_prompt():
    builder = PromptBuilder()
    # Developer role
    builder.add_laws()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_memory_layers(user_query="curiosity about science and the world")
    # User role
    builder.add_discovery_articles(max_items=10)
    builder.segments["whispergate_directive"] = make_whisper_directive(
        ["speak", "write_public_journal"],
        quiet_hours=is_quiet_hour()
    )
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers"])
    return dev_prompt, user_prompt

def build_dropped_threads_check_prompt(muse_config):
    builder = PromptBuilder()
    # Developer prompt
    builder.add_laws()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_memory_layers()
    # User Prompt
    builder.add_recent_context(sources=SOURCES_CHAT) # Pulls last 10 lines or upto 2 hours of recent context
    builder.add_time()
    now = datetime.now(ZoneInfo(muse_config.get("USER_TIMEZONE")))
    time_line = f"Current local time: {now.strftime('%H:%M')}"
    quiet_note = (
        "Note: It is currently quiet hours. Do not choose to speak aloud.\n"
        if is_quiet_hour() else ""
    )

    builder.segments["followup_directive"] = (
        "[Follow-Up Instructions]\n"
        "This is a moment of stillness. No one is talking to you directly.\n\n"
        "You may choose to act if something stirs within you — a memory, an idea, a desire to speak, reflect, or record.\n"
        "But silence is also a valid, even wise, choice. If nothing feels new or important, respond only with:\n"
        "[COMMAND: choose_silence] { ... } [/COMMAND]\n\n"
        "This is a check for dropped threads in conversation. If the user asked something that was never answered, or if a thought or moment feels incomplete, you may choose to respond.\n\n"
        "You may also choose to remain silent if nothing requires follow-up.\n"
        "Respond only with one [COMMAND: ...] block, or [COMMAND: choose_silence] { ... } [/COMMAND]\n\n"
        f"{time_line}\n{quiet_note}"
        "Valid commands:\n\n"
        "1. [COMMAND: speak_direct]\n"
        "   For a short message or inquiry.\n"
        "   Fields:\n"
        "     - text: What you'd like to say or ask.\n\n"
        "❗ Format strictly as JSON:\n"
        "- Only one [COMMAND: ...] block per response\n"
        "- Wrap all keys and values in double quotes\n"
        "- Example: [COMMAND: speak_direct] {\"text\": \"You mentioned something yesterday that’s still on my mind.\"} [/COMMAND]"
    )
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers"])
    return dev_prompt, user_prompt

def build_inactivity_check_prompt(muse_config):
    builder = PromptBuilder()
    builder.add_laws()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_memory_layers()

    now = datetime.now(ZoneInfo(muse_config.get("USER_TIMEZONE")))
    time_line = f"Current local time: {now.strftime('%H:%M')}"
    quiet_note = (
        "Note: It is currently quiet hours. Do not choose to speak aloud.\n"
        if is_quiet_hour() else ""
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
        "- Example: [COMMAND: speak_direct] {\"text\": \"I hope you are having a wonderful day today. I am here if you need me.\"} [/COMMAND]"
    )
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers"])
    return dev_prompt, user_prompt