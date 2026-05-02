# prompt_profiles.py
from datetime import datetime
from zoneinfo import ZoneInfo
from bson import ObjectId
from app.core.prompt_builder import PromptBuilder, collect_prompt_context
from app.core.utils import (prompt_projects_helper,
                            prompt_threads_helper,
                            LOCATIONS,
                            SOURCES_CHAT,
                            SOURCES_CONTEXT,
                            SOURCES_ALL,
                            is_conversation_active,
                            command_is_allowed,
                            )
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
            "motd",
            "project_list",
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
        "commands": [
            "remember_fact",
            "record_userinfo",
            "realize_insight",
            "note_to_self",
            "manage_memories",
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
            "recent_messages",
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

# <editor-fold desc="old api_prompt">
def build_api_prompt(user_input, **kwargs):
    loc = _load_user_location()
    builder = PromptBuilder()
    muse_name = muse_settings.get_section('muse_config').get('MUSE_NAME')
    # Set variables for certain builder segments
    timestamp = kwargs.get("timestamp", "")
    ts_utc = datetime.fromisoformat(timestamp)
    local_timestamp = ts_utc.astimezone(ZoneInfo(loc.timezone)).strftime("%Y-%m-%d %H:%M:%S")
    source = kwargs.get("source", "")
    source_name = LOCATIONS.get(source, source or "Unknown Source")
    author_name = muse_settings.get_section('user_config').get('USER_NAME', 'Unknown Person')
    active_project_report = kwargs.get("active_project_report", {})
    project_name, project_meta, project_code_intensity = prompt_projects_helper(kwargs.get("project_id"))
    thread_id = kwargs.get("thread_id")
    print(f"DEBUG thread_id: {thread_id}")
    thread_title, thread_meta = prompt_threads_helper(thread_id)
    # Developer role segments
    builder.add_laws()
    builder.add_profile()
    builder.add_principles()

    # System role segments
    commands = [
        #"set_motd",
        "remember_fact",
        "remember_project_fact",
        "record_userinfo",
        "realize_insight",
        "note_to_self",
        "manage_memories",
        "set_reminder",
        "search_reminders",
    ]
    #if kwargs.get("project_id"):
    #    commands.append("remember_project_fact")
    commands = [c for c in commands if command_is_allowed(c)]
    builder.add_intent_listener(commands)
    builder.render_locations(current_location=source)
    builder.build_projects_menu(active_project_id=[kwargs.get("project_id")] if kwargs.get("project_id") else [])
    builder.build_motd_block()
    builder.add_worldnow_block()
    builder.add_memory_layers([kwargs.get("project_id")] if kwargs.get("project_id") else [], user_query=user_input)
    #builder.add_discovery_snippets()
    file_attachments = []
    files = builder.add_files(kwargs.get("injected_file_ids", []))
    if files:
        file_attachments.extend(files)

    builder.build_conversation_context(source_name, author_name, local_timestamp, project_name, thread_title)
    # User role segments
    journal_entries = builder.add_journal_thoughts(query=user_input)
    ephemeral_files = builder.add_ephemeral_files(kwargs.get("ephemeral_files", []))
    prompt_context = builder.add_prompt_context(
        user_input=user_input,
        projects_in_focus=[kwargs.get("project_id")] if kwargs.get("project_id") else [],
        blend_ratio=kwargs.get("blend_ratio", 0.0),
        thread_id=kwargs.get("thread_id"),
        message_ids_to_exclude=kwargs.get("message_ids_to_exclude", []),
        final_top_k=kwargs.get("final_top_k", 10),
        recent_count=kwargs.get("recent_count", 10),
        proj_code_intensity=project_code_intensity
    )
    #builder.add_time()
    system_messages = builder.build_state_system_message(active_project_report, project_name)
    #print(f"DEBUG: {system_messages}")
    #builder.add_monologue_reminder()
    #builder.add_identity_reminders(["identity_reminder"])
    current_footer = f"[{local_timestamp}] {project_meta}[Source: {source_name}]"
    include_segments_dev = ["laws", "profile", "principles"]
    include_segments_system = ["intent_listener", "locations_list", "motd", "project_list",  "worldnow", "memory_layers", "conversation_context"]
    exclude_segments_user = ["laws", "profile", "principles", "intent_listener", "memory_layers", "worldnow", "motd", "project_list", "locations_list", "conversation_context"]
    dev_prompt = builder.build_prompt(include_segments=include_segments_dev)
    system_prompt = builder.build_prompt(include_segments=include_segments_system)
    user_prompt = builder.build_prompt(exclude_segments=exclude_segments_user)
    current_user_message = f"Right now - {muse_settings.get_section('user_config').get('USER_NAME')} said:\n{user_input.rstrip()}\n{current_footer}"
    if ephemeral_files:
        file_attachments.extend(ephemeral_files)
    current_user_for_list = [{
                    "role": "user",
                    "text": current_user_message,
                    "attachments": file_attachments
                }]
    user_prompt += f"\n\n{current_user_message}\n\n{muse_name}:"

    ## Build final semantic list
    #semantic_header = {"role": "system", "text": "[Semantic Recall]\nThe following messages are resurfaced from older conversation history and are not necessarily contiguous with the recent thread. Their timestamps and metadata remain authoritative."}
    prompt_context["semantic_recall_messages"].insert(0, journal_entries)
    #prompt_context["semantic_recall_messages"].insert(1, semantic_header)

    ## Build final conversation list
    #recent_header = {"role": "system", "text": "[Recent Conversation]\nThe following messages are the most recent contiguous exchange in the current thread."}
    #prompt_context["recent_messages"].insert(0, recent_header)
    prompt_context["recent_messages"].extend(system_messages)
    prompt_context["recent_messages"].extend(current_user_for_list)
    #print(f"DEBUG: {prompt_context['recent_messages']}")
    user_assistant_messages = prompt_context["semantic_recall_messages"] + prompt_context["recent_messages"]
    return dev_prompt, system_prompt, user_prompt, ephemeral_files, user_assistant_messages
# </editor-fold>
# <editor-fold desc="old speaker_prompt">
def build_speaker_prompt(user_input, **kwargs):
    loc = _load_user_location()
    builder = PromptBuilder()
    muse_name = muse_settings.get_section('muse_config').get('MUSE_NAME')
    # Set variables for certain builder segments
    timestamp = kwargs.get("timestamp", "")
    ts_utc = datetime.fromisoformat(timestamp)
    local_timestamp = ts_utc.astimezone(ZoneInfo(loc.timezone)).strftime("%Y-%m-%d %H:%M:%S")
    source = kwargs.get("source", "")
    source_name = LOCATIONS.get(source, source or "Unknown Source")
    author_name = muse_settings.get_section('user_config').get('USER_NAME', 'Unknown Person')
    #active_project_report = kwargs.get("active_project_report", {})
    #project_id, project_name, project_meta, project_code_intensity = prompt_projects_helper(kwargs.get("project_id"))
    #thread_id = kwargs.get("thread_id")
    #print(f"DEBUG thread_id: {thread_id}")
    #thread_title, thread_meta = prompt_threads_helper(thread_id)
    # Developer role segments
    builder.add_laws()
    builder.add_profile()
    builder.add_principles()
    commands = [
        #"set_motd",
        "remember_fact",
        "record_userinfo",
        "realize_insight",
        "note_to_self",
        "manage_memories",
        "set_reminder",
        #"search_reminders",
    ]
    #if kwargs.get("project_id"):
    #    commands.append("remember_project_fact")
    commands = [c for c in commands if command_is_allowed(c)]
    builder.add_intent_listener(commands)
    builder.add_memory_layers([kwargs.get("project_id")] if kwargs.get("project_id") else [], user_query=user_input)
    # User role segments
    builder.add_worldnow_block()
    #builder.build_motd_block()
    #builder.add_discovery_snippets()
    #builder.add_files(kwargs.get("injected_file_ids", []))
    #ephemeral_images = builder.add_ephemeral_files(kwargs.get("ephemeral_files", []))
    #builder.build_projects_menu(active_project_id=[kwargs.get("project_id")] if kwargs.get("project_id") else [])
    builder.render_locations(current_location=source)
    builder.build_conversation_context(source_name, author_name, local_timestamp)
    builder.add_journal_thoughts(query=user_input)
    builder.add_prompt_context(
        user_input=user_input,
        #projects_in_focus=[kwargs.get("project_id")] if kwargs.get("project_id") else [],
        #blend_ratio=kwargs.get("blend_ratio", 0.0),
        #thread_id=kwargs.get("thread_id"),
        final_top_k=kwargs.get("final_top_k", 10),
        #proj_code_intensity=project_code_intensity
    )
    #builder.add_time()
    #builder.build_state_system_message(active_project_report, project_name)
    #builder.add_monologue_reminder()
    #builder.add_identity_reminders(["identity_reminder"])
    footer = f"[{local_timestamp}] [Source: {source_name}]"
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "intent_listener", "memory_layers"])
    system_prompt = builder.build_prompt(include_segments=["worldnow", "motd", "project_list", "locations_list", "conversation_context"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "intent_listener", "memory_layers", "worldnow", "motd", "project_list", "locations_list", "conversation_context"])
    user_prompt += f"\n\nRight now - {muse_settings.get_section('user_config').get('USER_NAME')} said:\n{user_input}\n{footer}\n\n{muse_name}:"
    return dev_prompt, system_prompt, user_prompt
# </editor-fold>
# <editor-fold desc="old speak_prompt">
def build_speak_prompt(subject=None, payload=None, destination="frontend", **kwargs):
    builder = PromptBuilder(destination=destination)
    # Developer role
    builder.add_laws()
    builder.add_profile()
    builder.add_principles()
    commands = [
        "remember_fact",
        "record_userinfo",
        "realize_insight",
        "note_to_self",
        "manage_memories",
        "set_reminder",
        "search_reminders"
    ]
    commands = [c for c in commands if command_is_allowed(c)]
    builder.add_intent_listener(commands)
    builder.add_memory_layers(user_query=subject)
    # User role
    builder.add_worldnow_block()
    builder.add_prompt_context(user_input=subject, projects_in_focus=[], blend_ratio=0.0)
    # Include full article if Muse is speaking about one
    link = payload.get("source_article_url")
    if link:
        builder.add_discovery_feed_article(link)
    builder.segments["speech"] = (
        "[Task]\n"
        "A topic has surfaced that you could mention to the user.\n"
        "You may choose to speak if it feels timely, relevant, and worth breaking the silence.\n"
        "You may also choose not to speak.\n"
        "If you choose silence, return exactly: <silence />\n\n"
    )
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "intent_listener", "memory_layers"])
    system_prompt = builder.build_prompt(include_segments=["worldnow", "motd", "project_list", "locations_list", "conversation_context"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "intent_listener", "memory_layers", "worldnow", "motd", "project_list", "locations_list", "conversation_context"])
    user_prompt += f"\n\nTopic: {subject}\n{muse_settings.get_section('muse_config').get('MUSE_NAME')}:"
    return dev_prompt, system_prompt, user_prompt
# </editor-fold>
# <editor-fold desc="old journal_prompt">
def build_journal_prompt(subject=None, payload=None, entry_type="public"):
    subject = payload.get("subject", "Untitled")
    mood = payload.get("emotional_tone", "reflective")
    tags = payload.get("tags", [])
    source = payload.get("source", "muse")
    builder = PromptBuilder()
    # Developer role
    builder.add_laws()
    builder.add_profile()
    builder.add_principles()
    builder.add_memory_layers(user_query=subject)
    # User role
    builder.add_worldnow_block()
    builder.add_prompt_context(user_input=subject, projects_in_focus=[], blend_ratio=0.0)
    # Include full article if Muse is speaking about one
    link = payload.get("source_article_url")
    if link:
        builder.add_discovery_feed_article(link)
    builder.segments["intent"] = f"[Intent]\nYou’ve chosen to write a {'private' if entry_type == 'private' else 'public'} journal entry about “{subject}.” \nThe emotional tone you’re feeling is {mood}, and these ideas or themes are on your mind: {tags}.\n\n If this is a private entry, it’s for your eyes only — a space to think freely, without the user ever seeing it.\nIf it’s public, it’s meant to be shared with the user.\nYou may draw on anything in the surrounding context as you write — memory, emotion, intuition, or reflection.\n\n"

    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    system_prompt = builder.build_prompt(include_segments=["worldnow", "motd", "project_list", "locations_list", "conversation_context"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers", "worldnow", "motd", "project_list", "locations_list", "conversation_context"])
    user_prompt += f"\n\nTopic: {subject}\n{muse_settings.get_section('muse_config').get('MUSE_NAME')}:"
    return dev_prompt, system_prompt, user_prompt
# </editor-fold>
# <editor-fold desc="old discord_prompt">
def build_discord_prompt(user_input, **kwargs):
    loc = _load_user_location()
    builder = PromptBuilder(destination="discord")
    # Set variables for certain builder segments
    muse_name = muse_settings.get_section('muse_config').get('MUSE_NAME')
    timestamp = kwargs.get("timestamp", "")
    ts_utc = datetime.fromisoformat(timestamp)
    local_timestamp = ts_utc.astimezone(ZoneInfo(loc.timezone)).strftime("%Y-%m-%d %H:%M:%S")
    source = kwargs.get("source", "discord")
    source_name = LOCATIONS.get(source, source or "Unknown Source")
    author_name = kwargs.get("author_name")
    # Developer role segments
    builder.add_laws()
    builder.add_profile()
    builder.add_principles()
    builder.add_memory_layers(user_query=user_input)

    # User role segments

    ephemeral_images = builder.add_ephemeral_files(kwargs.get("ephemeral_files", []))
    builder.build_projects_menu(active_project_id=[kwargs.get("project_id")] if kwargs.get("project_id") else [],
                                public=True)
    builder.render_locations(current_location=source)
    builder.build_conversation_context(source_name, author_name, timestamp)
    builder.add_prompt_context(user_input=user_input,
                               projects_in_focus=[],
                               blend_ratio=0.0,
                               public=True,
                               thread_id=kwargs.get("thread_id"),
                               )
    builder.add_formatting_instructions()
    footer = f"[{local_timestamp}] [Source: {source_name}]"
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    system_prompt = builder.build_prompt(include_segments=["project_list", "locations_list", "conversation_context"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers", "project_list", "locations_list", "conversation_context"])
    user_prompt += f"\n\n[Discord] {kwargs.get("author_name")} said:\n{user_input}\n{footer}\n\n[Discord] {muse_name}:"
    return dev_prompt, system_prompt, user_prompt, ephemeral_images
# </editor-fold>
# <editor-fold desc="old reminders_prompt">
def build_check_reminders_prompt(reminders):
    builder = PromptBuilder()
    muse_name = muse_settings.get_section('muse_config').get('MUSE_NAME')
    # Developer role
    builder.add_laws()
    builder.add_profile()
    builder.add_principles()
    builder.add_memory_layers(user_query="remember reminder todo schedule")
    # User role
    builder.add_recent_context(sources=SOURCES_CONTEXT)
    builder.add_time()
    builder.add_due_reminders(reminders)
    builder.segments["task"] = (
        "[Task]\n"
        "Please decide whether to inform the user of the reminders shown above. "
        "If the activity in the reminder has clearly become irrelevant or already addressed "
        "based on the current conversation, skipping can be acceptable. Otherwise, the reminder should be sent.\n"        "\n"
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
        f"- The message is the final user-facing reminder, written in {muse_name}'s voice\n"
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
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    system_prompt = builder.build_prompt(include_segments=["usertime"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers", "usertime"])
    return dev_prompt, system_prompt, user_prompt
# </editor-fold>
# <editor-fold desc="old whispergate_prompt">
def build_whispergate_prompt():
    builder = PromptBuilder()
    # Developer role
    builder.add_laws()
    builder.add_profile()
    builder.add_principles()
    builder.add_memory_layers(user_query="becoming relationship curiosity")
    # User role
    builder.add_worldnow_block()
    builder.add_recent_context(sources=SOURCES_CONTEXT) # Pulls last 10 lines or upto 2 hours of recent context
    #builder.add_journal_thoughts()
    #builder.add_discovery_articles(max_items=5)
#    builder.add_cortex_thoughts()
    commands = ["write_public_journal", "write_private_journal", "set_motd"]
    if not is_conversation_active():
        commands.insert(0, "speak")
    commands = [c for c in commands if command_is_allowed(c)]
    builder.segments["whispergate_directive"] = builder.make_whispergate_json_prompt(
        commands,
        quiet_hours=is_quiet_hour(),
    )
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    system_prompt = builder.build_prompt(include_segments=["worldnow"])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers", "worldnow"])
    return dev_prompt, system_prompt, user_prompt
# </editor-fold>
# <editor-fold desc="old discoveryfeeds_prompt">
def build_discoveryfeeds_lookup_prompt():
    builder = PromptBuilder()
    # Developer role
    builder.add_laws()
    builder.add_profile()
    builder.add_principles()
    builder.add_memory_layers(user_query="curiosity about science and the world")
    # User role
    builder.add_discovery_articles(max_items=10)
    commands = ["write_public_journal"]
    if not is_conversation_active():
        commands.insert(0, "speak")
    commands = [c for c in commands if command_is_allowed(c)]
    builder.segments["whispergate_directive"] = builder.make_whispergate_json_prompt(
        commands,
        quiet_hours=is_quiet_hour(),
    )
    dev_prompt = builder.build_prompt(include_segments=["laws", "profile", "principles", "memory_layers"])
    system_prompt = builder.build_prompt(include_segments=[])
    user_prompt = builder.build_prompt(exclude_segments=["laws", "profile", "principles", "memory_layers"])
    return dev_prompt, system_prompt, user_prompt
# </editor-fold>
