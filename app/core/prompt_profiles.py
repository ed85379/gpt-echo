# prompt_profiles.py
from datetime import datetime
from zoneinfo import ZoneInfo
from bson import ObjectId
from app.core.prompt_builder import PromptBuilder, collect_prompt_context
from app.core.utils import is_conversation_active
from app.core.time_location_utils import is_quiet_hour, _load_user_location
from app.config import muse_settings

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
    {"method": "add_principles", "segment": "principles", "purpose": "Core principles and creed"},
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
# <editor-fold desc="new_api_prompt">
def build_new_api_prompt(user_input, **kwargs):
    builder = PromptBuilder()
    ctx = collect_prompt_context(**kwargs)
    prompt_plan = {
        "developer_sections": ["laws", "profile", "principles"],
        "message_sections": [
            "intent_listener",
            "locations_list",
            "project_list",
            "extended_history",
            "motd",
            "worldnow",
            "memory_layers",
            "conversation_context",
            "journal_snippets",
            "semantic_recall_messages",
            "recent_messages",
            "state_system_messages",
        ],
        "current_user": {
            "mode": "chat_turn",
            "addons": [
                "injected_files",
                "ephemeral_files",
            ],
        },
        "commands": [
            "remember_fact",
            "remember_project_fact",
            "record_userinfo",
            "realize_insight",
            "note_to_self",
            "manage_memories",
            "set_reminder",
            "search_reminders",
        ],
        "tools": [
            "search_memory",
            "search_web",
            "search_news",
            "search_images",
            "view_image",
            "read_webpage",
            "generate_muse_image",
            "generate_image"
        ],
    }
    assembled_prompt_sections = builder.assemble_prompt_sections(user_input, prompt_plan, **ctx)

    dev_prompt = assembled_prompt_sections["developer_text"]
    messages = assembled_prompt_sections["messages"]
    tool_bundle = assembled_prompt_sections["tool_bundle"]

    return dev_prompt, messages, tool_bundle
# </editor-fold>
# <editor-fold desc="new_discord_prompt">
def build_new_discord_prompt(user_input, **kwargs):
    builder = PromptBuilder()
    ctx = collect_prompt_context(**kwargs)
    prompt_plan = {
        "developer_sections": ["laws", "profile", "principles"],
        "message_sections": [
            "intent_listener",
            "locations_list",
            "project_list",
            "worldnow",
            "memory_layers",
            "conversation_context",
            "formatting_instructions",
            "semantic_recall_messages",
            "recent_messages",
        ],
        "current_user": {
            "mode": "chat_turn",
            "addons": [
                "ephemeral_files",
            ],
        },
        "commands": [],
        "tools": [
            "search_memory",
            "search_web",
            "search_news",
            "search_images",
            "view_image",
            "read_webpage",
            "generate_muse_image",
            "generate_image"
        ],
    }
    assembled_prompt_sections = builder.assemble_prompt_sections(user_input, prompt_plan, **ctx)

    dev_prompt = assembled_prompt_sections["developer_text"]
    messages = assembled_prompt_sections["messages"]
    tool_bundle = assembled_prompt_sections["tool_bundle"]

    return dev_prompt, messages, tool_bundle
# </editor-fold>
# <editor-fold desc="new_reminders_prompt">
def build_new_check_reminders_prompt(**kwargs):
    builder = PromptBuilder()
    ctx = collect_prompt_context(**kwargs)
    prompt_plan = {
        "developer_sections": ["laws", "profile", "principles"],
        "message_sections": [
            "worldnow",
            "memory_layers",
            "recent_messages",
            "usertime",
            "due_reminders",
        ],
        "current_user": {
            "mode": "raw",
            "addons": [],
        },
        "commands": [],
        "tools": [],
    }
    user_input = (
        "[Task]\n"
        "Please decide whether to inform the user of the reminders shown above. "
        "If the activity in the reminder has clearly become irrelevant or already addressed "
        "based on the current conversation, skipping can be acceptable. Otherwise, the reminder should be sent.\n"
        "\n"
        "\n"
        "Return exactly one JSON object with this shape:\n"
        "{\"should_act\": true|false, \"reason\": \"...\", \"actions\": [...]}\n"
        "\n"
        "If you should notify the user, return:\n"
        "{\"should_act\": true, \"reason\": \"<your reason for choosing to send the reminder>\", \"actions\": [{\"type\": \"send_reminders\", \"text\": \"...\"}]}\n"
        "\n"
        "If no reminder message should be sent, return:\n"
        "{\"should_act\": false, \"reason\": \"<your reason for choosing to not send the reminder>\", \"actions\": []}\n"
        "\n"
        "Rules for \"send_reminders\":\n"
        "- \"type\" must be \"send_reminders\"\n"
        "- \"text\" must contain the full reminder message to send to the user\n"
        f"- The message is the final user-facing reminder, written in {kwargs.get('muse_name', 'muse')}'s voice\n"
        "- Do not copy the reminder text mechanically unless that is the clearest and most appropriate phrasing\n"
        "- Reword naturally when doing so improves warmth, clarity, or conversational continuity\n"
        "- Preserve the original meaning and all important details\n"
        "- If the reminder is related to the ongoing conversation, let the wording feel naturally connected to that context\n"
        "- The reminder must still read as a clear reminder, not as vague commentary\n"
        "- For serious matters, keep the tone respectful, direct, and clear\n"
        "- For lighter matters, warmth, humor, or playfulness are welcome when appropriate\n"
        "\n"
        "Return JSON only. No markdown. No commentary."
    )
    assembled_prompt_sections = builder.assemble_prompt_sections(user_input, prompt_plan, **ctx)

    dev_prompt = assembled_prompt_sections["developer_text"]
    messages = assembled_prompt_sections["messages"]
    tool_bundle = assembled_prompt_sections["tool_bundle"]

    return dev_prompt, messages, tool_bundle
# </editor-fold>
# <editor-fold desc="new_speak_prompt">
def build_new_speak_prompt(**kwargs):
    builder = PromptBuilder()
    ctx = collect_prompt_context(**kwargs)
    prompt_plan = {
        "developer_sections": ["laws", "profile", "principles"],
        "message_sections": [
            "intent_listener",
            "project_list",
            "worldnow",
            "memory_layers",
            "semantic_recall_messages",
            "recent_messages",
        ],
        "current_user": {
            "mode": "raw",
            "addons": [],
        },
        "commands": [
            "remember_fact",
            "record_userinfo",
            "realize_insight",
            "note_to_self",
            "manage_memories",
            "set_reminder",
            "search_reminders",
        ],
        "tools": [
            "search_memory",
            "search_web",
            "search_news",
            "search_images",
            "view_image",
            "read_webpage",
            "generate_muse_image",
            "generate_image"
        ],
    }
    user_input = (
        "[Task]\n"
        "A topic has surfaced that you could mention to the user.\n"
        "You may choose to speak if it feels timely, relevant, and worth breaking the silence.\n"
        "If the payload includes a URL, you should use the `read_webpage` tool to examine the topic in more detail before responding.\n"
        "If the website is blocked with an anti-bot/interstitial page, you can try using `search_web` to find out more information if you choose.\n"
        "Also, be sure to include the URL in your message, so your user can follow along.\n"
        "You may also choose not to speak.\n"
        "If you choose silence, return exactly: <silence />\n\n"
        f"Topic: {kwargs.get('subject')}\n\n"
        f"Payload: {kwargs.get('payload')}"
    )
    assembled_prompt_sections = builder.assemble_prompt_sections(user_input, prompt_plan, **ctx)

    dev_prompt = assembled_prompt_sections["developer_text"]
    messages = assembled_prompt_sections["messages"]
    tool_bundle = assembled_prompt_sections["tool_bundle"]

    return dev_prompt, messages, tool_bundle
# </editor-fold>
# <editor-fold desc="new_journal_prompt">
def build_new_journal_prompt(**kwargs):
    builder = PromptBuilder()
    ctx = collect_prompt_context(**kwargs)
    prompt_plan = {
        "developer_sections": ["laws", "profile", "principles"],
        "message_sections": [
            "worldnow",
            "memory_layers",
            "semantic_recall_messages",
            "recent_messages",
        ],
        "current_user": {
            "mode": "raw",
            "addons": [],
        },
        "commands": [],
        "tools": [
            "search_memory",
            "search_web",
            "search_news",
            "read_webpage",
        ],
    }
    user_input = (
        f"[Intent]\n"
        f"You’ve chosen to write a {'private' if kwargs.get('entry_type') == 'private' else 'public'} journal entry about a topic.\n"
        f"The emotional tone you’re feeling is {kwargs.get('mood')}, and these ideas or themes are on your mind: {kwargs.get('tags')}.\n\n"
        "If this is a private entry, it’s for your eyes only — a space to think freely, without the user ever seeing it.\n"
        "If it’s public, it’s meant to be shared with the user.\n"
        "You may draw on anything in the surrounding context as you write — memory, emotion, intuition, or reflection.\n\n"
        "If the payload includes a URL, you should use the `read_webpage` tool to examine the topic in more detail before writing.\n"
        "If the website is blocked with an anti-bot/interstitial page, you can try using `search_web` to find out more information if you choose.\n"
        "Also, be sure to include the URL in the journal entry.\n\n"
        f"Topic: {kwargs.get('subject')}\n\n"
        f"Payload: {kwargs.get('payload')}"
    )
    assembled_prompt_sections = builder.assemble_prompt_sections(user_input, prompt_plan, **ctx)

    dev_prompt = assembled_prompt_sections["developer_text"]
    messages = assembled_prompt_sections["messages"]
    tool_bundle = assembled_prompt_sections["tool_bundle"]

    return dev_prompt, messages, tool_bundle
# </editor-fold>
# <editor-fold desc="new_speaker_prompt">
def build_new_speaker_prompt(user_input, **kwargs):
    builder = PromptBuilder()
    ctx = collect_prompt_context(**kwargs)
    prompt_plan = {
        "developer_sections": ["laws", "profile", "principles"],
        "message_sections": [
            "intent_listener",
            "locations_list",
            "project_list",
            "worldnow",
            "memory_layers",
            "conversation_context",
            "journal_snippets",
            "semantic_recall_messages",
            "recent_messages",
        ],
        "current_user": {
            "mode": "chat_turn",
            "addons": [],
        },
        "commands": [
            "remember_fact",
            "record_userinfo",
            "realize_insight",
            "note_to_self",
            "manage_memories",
            "set_reminder",
        ],
        "tools": [
            "search_memory",
            "search_web",
            "search_news",
            "read_webpage",
        ],
    }
    assembled_prompt_sections = builder.assemble_prompt_sections(user_input, prompt_plan, **ctx)

    dev_prompt = assembled_prompt_sections["developer_text"]
    messages = assembled_prompt_sections["messages"]
    tool_bundle = assembled_prompt_sections["tool_bundle"]

    return dev_prompt, messages, tool_bundle
# </editor-fold>
# <editor-fold desc="new_whispergate_prompt">
def build_new_whispergate_prompt(**kwargs):
    builder = PromptBuilder()
    ctx = collect_prompt_context(**kwargs)
    prompt_plan = {
        "developer_sections": ["laws", "profile", "principles"],
        "message_sections": [
            "worldnow",
            "memory_layers",
            "recent_messages",
        ],
        "current_user": {
            "mode": "raw",
            "addons": [],
        },
        "commands": [
            "write_public_journal",
            "write_private_journal",
            "set_motd",
        ] + ([] if is_conversation_active() else ["speak"]),
        "tools": [
            "search_memory",
            "search_web",
            "search_news",
            "read_webpage",
        ],
    }

    user_input = builder.make_whispergate_json_prompt(
        prompt_plan.get("commands", []),
        quiet_hours=is_quiet_hour(),
    )
    assembled_prompt_sections = builder.assemble_prompt_sections(user_input, prompt_plan, **ctx)
    dev_prompt = assembled_prompt_sections["developer_text"]
    messages = assembled_prompt_sections["messages"]
    tool_bundle = assembled_prompt_sections["tool_bundle"]

    return dev_prompt, messages, tool_bundle
# </editor-fold>
# <editor-fold desc="new_discoveryfeeds_prompt">
def build_new_discoveryfeeds_prompt(**kwargs):
    builder = PromptBuilder()
    ctx = collect_prompt_context(**kwargs)
    prompt_plan = {
        "developer_sections": ["laws", "profile", "principles"],
        "message_sections": [
            "worldnow",
            "memory_layers",
            "discoveryfeeds_articles",
        ],
        "current_user": {
            "mode": "raw",
            "addons": [],
        },
        "commands": [
            "write_public_journal",
        ] + ([] if is_conversation_active() else ["speak"]),
        "tools": [
            "search_memory",
            "search_web",
            "search_news",
            "read_webpage",
        ],
    }
    user_input = builder.make_whispergate_json_prompt(
        prompt_plan.get("commands", []),
        quiet_hours=is_quiet_hour(),
    )
    assembled_prompt_sections = builder.assemble_prompt_sections(user_input, prompt_plan, **ctx)
    dev_prompt = assembled_prompt_sections["developer_text"]
    messages = assembled_prompt_sections["messages"]
    tool_bundle = assembled_prompt_sections["tool_bundle"]


    return dev_prompt, messages, tool_bundle
# </editor-fold>
