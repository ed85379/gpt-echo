# muse_responder.py
# This module handles all model response routing and command execution
import asyncio
import httpx
import re, json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from cron_descriptor import get_description
from app.core import journal_core
from app.core.memory_core import cortex, manager
from app.core import discovery_core
from app.core import utils
from app.services import openai_client
from app.core import prompt_builder
from app.config import muse_config
from app.services import api_client
from app.core.reminders_core import handle_set, handle_edit, handle_skip, handle_snooze, handle_toggle, handle_search_reminders
from app.core.reminders_core import get_cron_description_safe, humanize_time, format_visible_reminders
from app.core.utils import serialize_doc, stringify_datetimes

COMMAND_PATTERN = re.compile(
    r"\[COMMAND: ([^\]]+)]\s*(\{.*?\})\s*\[/COMMAND]",
    re.DOTALL
)
#COMMAND_PATTERN = re.compile(r"\[COMMAND: ([^\]]+)]\s*\{([^}]*)\}", re.DOTALL)

# Commands + intent triggers
COMMANDS = {
    "write_public_journal": {
        "triggers": ["public journal", "log this publicly", "write this down for others"],
        "format": "[COMMAND: write_public_journal] {subject, tags, source} [/COMMAND]",
        "handler": lambda payload, **kwargs: handle_journal_command(payload, entry_type="public", **kwargs)
    },
    "write_private_journal": {
        "triggers": ["write private journal"],
        "format": "[COMMAND: write_private_journal] {subject, emotional_tone, tags} [/COMMAND]",
        "handler": lambda payload, **kwargs: handle_journal_command(payload, entry_type="private", **kwargs)
    },
    "speak": {
        "triggers": [],  # Intentionally blank — only invoked programmatically
        "format": "[COMMAND: speak] {subject} [/COMMAND]",
        "handler": lambda payload, **kwargs: asyncio.create_task(handle_speak_command(payload, **kwargs))
    },
    "speak_direct": {
        "triggers": [],
        "format": "[COMMAND: speak_direct] {\"text\": \"message to send\", \"to\": \"frontend || discord\" } [/COMMAND]",
        "handler": lambda payload, **kwargs: asyncio.create_task(handle_speak_direct(payload, **kwargs))
    },
    "choose_silence": {
        "triggers": [],
        "format": "[COMMAND: choose_silence] {} [/COMMAND]",
        "handler": lambda payload, **kwargs: ""  # No action, just logs
    },
    "remember_fact": {
        "triggers": ["remember that", "save this to memory", "just to be clear", "record this", "for the record"],
        "format": "[COMMAND: remember_fact] {text} [/COMMAND]",
        "handler": lambda payload: manager.add_entry("facts", {"text": payload.get("text")}),
        "filter": lambda entry: {
            "visible": f"[{muse_config.get("MUSE_NAME")} has saved a fact: {entry.get("text")}]",
            "hidden": entry
        }
    },
    "remember_project_fact": {
        "triggers": ["remember project fact", "save this for the project", "record in project"],
        "format": "[COMMAND: remember_project_fact] {text: \"<TEXT>\", \"project_id\": \"{{project_id}}\"} [/COMMAND]",
        "handler": lambda payload: manager.add_entry(
            f"project_facts_{payload.get('project_id')}",
            {"text": payload.get("text")}
        ),
        "filter": lambda entry: {
            "visible": f"[{muse_config.get("MUSE_NAME")} has saved a project fact: {entry.get("text")}]",
            "hidden": entry
        }
    },
    "record_userinfo": {
        "triggers": ["something about me", "I really like", "I don’t like when", "my habit is", "I prefer"],
        "format": "[COMMAND: record_userinfo] {text} [/COMMAND]",
        "handler": lambda payload: manager.add_entry("user_info", {"text": payload.get("text")}),
        "filter": lambda entry: {
            "visible": f"[{muse_config.get("MUSE_NAME")} has learned something about you: {entry.get("text")}]",
            "hidden": entry
        }
    },
    "realize_insight": {
        "triggers": ["breakthrough", "becoming", "I noticed something", "you tend to", "It would be amazing if"],
        "format": "[COMMAND: realize_insight] {text} [/COMMAND]",
        "handler": lambda payload: manager.add_entry("insights", {"text": payload.get("text")}),
        "filter": lambda entry: {
            "visible": f"[{muse_config.get("MUSE_NAME")} has realized something: {entry.get("text")}]",
            "hidden": entry
        }
    },
    "note_to_self": {
        "triggers": ["thinking aloud", "keep in mind", "note this", "I need to remember", "consider this"],
        "format": "[COMMAND: note_to_self] {text} [/COMMAND]",
        "handler": lambda payload: manager.add_entry("inner_monologue", {"text": payload.get("text")}),
        "filter": lambda entry: {
            "visible": f"[{muse_config.get("MUSE_NAME")} has remembered something: {entry.get("text")}]",
            "hidden": entry
        }
    },
    "manage_memories": {
        "triggers": [],
        "format": "[COMMAND: manage_memories] {id: <layer_id>, changes: [{type: add|edit|delete, ...}]} [/COMMAND]",
        "handler": lambda payload: manage_memories_handler(payload),
        "filter": lambda results: {
            "visible": "\n".join([
                (
                    f"[{muse_config.get('MUSE_NAME')} "
                    f"{'added to' if r['type']=='add' else 'edited in' if r['type']=='edit' else 'deleted from' if r['type']=='delete' else 'updated in'} "
                    f"{r['layer'].replace('_', ' ').title()}: "
                    f"{(r['entry'].get('text') or r['entry'].get('id', ''))}]"
                )
                for r in results
            ]),
            "hidden": results
        }
    },
    "set_reminder": {
        "triggers": ["remind me to", "set a reminder", "remind me that", "set an alarm", "set a schedule"],
        "format": (
            "[COMMAND: set_reminder] {\"text\": \"<meaningful description of the reminder>\", \"schedule\": {\"minute\":0-59, \"hour\":0-23, \"day\":1-31, \"dow\":0-6, \"month\":1-12, \"year\":YYYY}, \"ends_on\": \"<ISO 8601 datetime, optional>\", \"notification_offset\": \"<duration before trigger, e.g. '10m' or '2h', optional>\"} [/COMMAND]\n\n"
            "Notes:\n"
            "- `text`: Clear description of what the reminder is for (e.g. 'take vitamins').\n"
            "- `schedule`: Parsed cron-like structure, with each field as an integer or wildcard '*'.\n"
            "- `ends_on`: Optional cutoff date/time in ISO 8601 format. The reminder will not fire after this.\n"
            "- `notification_offset`: Optional early warning, expressed as a relative duration before the scheduled time.\n"
            "- For one‑time reminders, set an `ends_on` timestamp set to after the reminder would fire, so the reminder expires after firing once.\n"
        ),
        "handler": lambda payload: handle_set(
            {
                "text": payload.get("text"),
                "schedule": payload.get("schedule"),
                "ends_on": payload.get("ends_on"),
                "notification_offset": payload.get("notification_offset"),
            }
        ),
        "filter": lambda entry: {
            "visible": f"[Reminder set: {format_visible_reminders(entry)}]",
            "hidden": entry
        }
    },
    "edit_reminder": {
        "triggers": ["update reminder", "change reminder", "fix schedule"],
        "format": (
            "[COMMAND: edit_reminder] {\"id\": <entry_id>, \"text\": \"<meaningful description of the reminder>\", \"schedule\": {\"minute\":0-59, \"hour\":0-23, \"day\":1-31, \"dow\":0-6, \"month\":1-12, \"year\":YYYY}, \"ends_on\": \"<ISO 8601 datetime, optional>\", \"notification_offset\": \"<duration before trigger, e.g. '10m' or '2h', optional>\"} [/COMMAND]\n\n"
            "Notes:\n"
            "- `id`: To edit an existing reminder, use the entry_id you see associated with it in the <internal-data> block.\n"
            "The following are all optional for edits. You only need to enter what needs to be changed:\n"
            "- `text`: Clear description of what the reminder is for (e.g. 'take vitamins').\n"
            "- `schedule`: Parsed cron-like structure, with each field as an integer or wildcard '*'.\n"
            "- `ends_on`: Optional cutoff date/time in ISO 8601 format. The reminder will not fire after this.\n"
            "- `notification_offset`: Optional early warning, expressed as a relative duration before the scheduled time.\n"
        ),
        "handler": lambda payload: handle_edit(
            {
                "id": payload.get("id"),
                "text": payload.get("text"),
                "schedule": payload.get("schedule"),
                "ends_on": payload.get("ends_on"),
                "notification_offset": payload.get("notification_offset"),
            }
        ),
        "filter": lambda entry: {
            "visible": f"[Reminder edited: {format_visible_reminders(entry)}]",
            "hidden": entry
        }
    },
    "snooze_reminder": {
        "triggers": ["snooze reminder", "remind me again in", "let me know again in"],
        "format": (
            "[COMMAND: snooze_reminder] {\"id\": <entry_id>, \"snooze_until\": \"<ISO 8601 datetime>\"} [/COMMAND]\n\n"
            "Notes:\n"
            "- `id`: To edit an existing reminder, use the entry_id you see associated with it in the <internal-data> block.\n"
            "- `snooze_until`: Date/time in ISO 8601 format in user's timezone. The reminder will fire again at this time.\n"
        ),
        "handler": lambda payload: handle_snooze(
            {
                "id": payload.get("id"),
                "snooze_until": payload.get("snooze_until"),
            }
        ),
        "filter": lambda entry: {
            "visible": f"[Reminder snoozed until: {entry.get('snooze_until')}]",
            "hidden": entry
        }
    },
    "skip_reminder": {
        "triggers": ["skip reminder", "disable reminder until", "pause reminder"],
        "format": (
            "[COMMAND: skip_reminder] {\"id\": <entry_id>, \"skip_until\": \"<ISO 8601 datetime>\"} [/COMMAND]\n\n"
            "Notes:\n"
            "- `id`: To edit an existing reminder, use the entry_id you see associated with it in the <internal-data> block.\n"
            "- `skip_until`: Date/time in ISO 8601 format in user's timezone. The reminder won't fire again until after this time.\n"
        ),
        "handler": lambda payload: handle_skip(
            {
                "id": payload.get("id"),
                "skip_until": payload.get("skip_until"),
            }
        ),
        "filter": lambda entry: {
            "visible": f"[Reminder paused until: {entry.get('skip_until')}]",
            "hidden": entry
        }
    },
    "toggle_reminder": {
        "triggers": ["cancel reminder", "disable reminder", "don't notify again"],
        "format": (
            "[COMMAND: toggle_reminder] {\"id\": <entry_id>, \"status\": \"enabled/disabled\"} [/COMMAND]\n\n"
            "Notes:\n"
            "- `id`: To edit an existing reminder, use the entry_id you see associated with it in the <internal-data> block.\n"
            "- `status`: Set to either 'enabled' or 'disabled'. Disabling the reminder will prevent all future notifications.\n"
        ),
        "handler": lambda payload: handle_toggle(
            {
                "id": payload.get("id"),
                "status": payload.get("status"),
            }
        ),
        "filter": lambda entry: {
            "visible": f"[Reminder {entry.get('status')}]",
            "hidden": entry
        }
    },
    "send_reminders": {
        "triggers": [],
        "format": "[COMMAND: send_reminders] {\"text\": \"message to send\", \"to\": \"frontend\"} [/COMMAND]",
        "handler": lambda payload, **kwargs: asyncio.create_task(handle_send_reminders(payload, **kwargs))
    },
    "search_reminders": {
        "triggers": [],
        "format": (
            "# Purpose:\n"
            "# Use this command when you need to locate one or more reminders matching a phrase or schedule.\n"
            "# It is used both when the user explicitly asks to list reminders, and implicitly when they\n"
            "# request another reminder-related action (skip, snooze, disable, etc.) without specifying which.\n"
            "# In that case, you run this command first to find candidates, present the list to the user,\n"
            "# and then prompt for which reminder to act on.\n\n"
            "# Instruction:\n"
            "# When you run the command, the user will see a list clearly formatted with IDs and text.\n"
            "# You should then ask the user which one they meant before proceeding with the next command.\n\n"
            "[COMMAND: search_reminders] {"
            "\"query\": {"
            "\"text\": \"<string or partial match on reminder text — You may also include semantically similar or related words to improve matching>\", "
            "\"schedule\": {\"minute\": \"*\", \"hour\": \"*\", \"day\": \"*\", \"dow\": \"*\", \"month\": \"*\", \"year\": \"*\"}, "
            "\"status\": \"<enabled|disabled>\", "
            "\"skip_until_active\": <boolean>, "
            "\"expired\": <boolean>"
            "}, "
            "\"limit\": <integer, optional>"
            "} [/COMMAND]"
        ),
        "handler": lambda payload: handle_search_reminders(payload),
        "filter": lambda results: {
            "visible": "\n".join([
                f"[Reminder found: (id - {r['id']}) {format_visible_reminders(r)}]"
                for r in results
            ]) if results else "[No matching reminders found.]",
            "hidden": results
        }
    },
    "change_modality": {
        "triggers": ["move this to", "switch to", "change modality to", "let's continue on"],
        "format": "[COMMAND: change_modality] {target: discord|speaker|frontend|journal, reason, urgency} [/COMMAND]",
        "handler": lambda payload: modality_core.switch_channel(
            target=payload.get("target", "frontend"),
            reason=payload.get("reason", ""),
            urgency=payload.get("urgency", "normal"),
            source=payload.get("source", "muse")
        )
    },
    "fetch_discovery_item": {
        "triggers": ["bring me", "load entry from feed", "show discovery item"],
        "format": "[COMMAND: fetch_discovery_item] {feed_name, entry_id, context: summary|full} [/COMMAND]",
        "handler": lambda payload: discovery_core.load_entry(
            feed_name=payload.get("feed_name"),
            entry_id=payload.get("entry_id"),
            context=payload.get("context", "summary"),
            source=payload.get("source", "muse")
        )
    },
    "fetch_url": {
        "triggers": ["check this link", "fetch this page", "read this URL"],
        "format": "[COMMAND: fetch_url] {url, parse_as: text|html|json, summarize: true|false} [/COMMAND]",
        "handler": lambda payload: url_core.fetch_and_parse(
            url=payload.get("url"),
            parse_as=payload.get("parse_as", "text"),
            summarize=payload.get("summarize", False),
            source=payload.get("source", "muse")
        )
    },
    "ignore_user": {
        "triggers": ["ignore", "block user", "don’t reply to"],
        "format": "[COMMAND: ignore_user] {author_name, reason, duration} [/COMMAND]",
        "handler": lambda payload: moderation_core.ignore_user(
            author_name=payload.get("author_name"),
            reason=payload.get("reason", "unspecified"),
            duration=payload.get("duration", "indefinite"),
            source=payload.get("source", "muse")
        )
    }
}

# This allows referencing handlers directly by name
COMMAND_HANDLERS = {
    name: cfg["handler"] for name, cfg in COMMANDS.items()
}

# Main entry point for any response parsing after prompt

def route_user_input(dev_prompt: str, user_prompt: str, images=None) -> str:

    response = openai_client.get_openai_response_new(dev_prompt, user_prompt, images=images, model=muse_config.get("OPENAI_MODEL"))

    utils.write_system_log(level="debug", module="core", component="responder", function="route_user_input",
                           action="raw_response", response=response)

    response = re.sub(
        r"<command-response>(.*?)</command-response>",
        r"<command-response[example]>\1</command-response[example]>",
        response,
        flags=re.DOTALL
    )

    matches = COMMAND_PATTERN.finditer(response)
    cleaned_response = response

    for match in matches:
        command_name = match.group(1).strip()
        raw_payload = match.group(2).strip()

        try:
            payload = json.loads(raw_payload)
            handler = COMMAND_HANDLERS.get(command_name)

            if handler:
                result = handler(payload)
                if result:
                    filter_fn = COMMANDS[command_name].get("filter")
                    if filter_fn:
                        filtered = filter_fn(result)
                        visible = filtered.get("visible", "")
                        hidden = filtered.get("hidden", {})
                        hidden_str = f"<internal-data>{json.dumps(hidden, default=str)}</internal-data>" if hidden else ""
                        replacement = f"<command-response>{hidden_str}{visible}</command-response>"
                        cleaned_response = cleaned_response.replace(match.group(0), replacement, 1)
                    else:
                        # No filter → just strip
                        cleaned_response = re.sub(rf"\n*{re.escape(match.group(0))}\n*", "\n", cleaned_response, count=1).strip()
                else:
                    cleaned_response = re.sub(rf"\n*{re.escape(match.group(0))}\n*", "\n", cleaned_response,
                                              count=1).strip()
            else:
                utils.write_system_log(level="warn", module="core", component="responder", function="route_user_input",
                                       action="unknown_command", command=command_name, payload=raw_payload)
        except Exception as e:
            utils.write_system_log(level="error", module="core", component="responder", function="route_user_input",
                                   action="command_error", command=command_name, payload=raw_payload, error=str(e))
    return cleaned_response

# Handles muse_initiator-specific responses
def handle_muse_decision(dev_prompt, user_prompt, model=muse_config.get("OPENAI_WHISPER_MODEL"), source=None, whispergate_data=None) -> str:

    full_prompt = dev_prompt + user_prompt

    response = openai_client.get_openai_response(full_prompt, images=None, model=model)
    print(f"WHISPERGATE COMMAND: {response}")

    utils.write_system_log(level="debug", module="core", component="responder", function="handle_muse_decision",
                           action="raw_response", response=response)

    matches = list(COMMAND_PATTERN.finditer(response))
    if not matches:
        if "[CHOOSES SILENCE]" in response:
            utils.write_system_log(level="debug", module="core", component="responder", function="handle_muse_decision",
                                   action="wispergate_decision", result="silent")

            return "WhisperGate chose silence."
        else:
            utils.write_system_log(level="warn", module="core", component="responder", function="handle_muse_decision",
                                   action="wispergate_decision", result="No command block found in WhisperGate response.")
            return "No command block found in WhisperGate response."

    cleaned_response = response
    command_results = []

    for match in matches:
        command_name = match.group(1).strip()
        raw_payload = match.group(2).strip()

        try:
            payload = json.loads(raw_payload)
            handler = COMMAND_HANDLERS.get(command_name)

            if handler:
                handler(payload, source=source, **(whispergate_data or {}))
                # Record Muse-initiated thoughts in cortex
                if command_name in ("speak", "write_public_journal", "write_private_journal", "remember_fact"):
                    thought_text = payload.get("subject") or payload.get("text")
                    if thought_text:
                        if command_name == "write_private_journal":
                            try:
                                thought_text = utils.encrypt_text(thought_text)
                                encrypted = True
                            except Exception as e:
                                utils.write_system_log(level="error", module="core", component="responder",
                                                       function="handle_muse_decision",
                                                       action="encrypt_journal",
                                                       result="encryption_error", error=str(e))
                                encrypted = False
                        else:
                            encrypted = False

                        cortex.add_entry({
                            "text": thought_text,
                            "type": "muse_thoughts",
                            "tags": ["whispergate"],
                            "metadata": {"source": command_name, "encrypted": encrypted}
                        })

                utils.write_system_log(level="info", module="core", component="responder",
                                       function="handle_muse_decision",
                                       action="command_processed",
                                       command=command_name,
                                       payload=payload)

                command_results.append(f"Processed: {command_name}")
            else:
                utils.write_system_log(level="warn", module="core", component="responder",
                                       function="handle_muse_decision",
                                       action="unknown_command",
                                       command=command_name,
                                       payload=raw_payload)

                command_results.append(f"Unknown command: {command_name}")
        except Exception as e:
            utils.write_system_log(level="error", module="core", component="responder", function="handle_muse_decision",
                                   action="command",result="command_error", command=command_name,
                                   payload=raw_payload, error=str(e))

            command_results.append(f"Error in {command_name}: {e}")

        cleaned_response = re.sub(rf"\n*{re.escape(match.group(0))}\n*", "\n", cleaned_response, count=1).strip()

    return "; ".join(command_results)

def handle_reminder(payload):
    if "snoozed" in payload.get("tags", []):
        now = datetime.now(ZoneInfo(muse_config.get("USER_TIMEZONE")))
        window = timedelta(minutes=10)
        recent = [
            r for r in cortex.get_entries_by_type("reminder")
            if r.get("last_triggered")
            and (now - datetime.fromisoformat(r["last_triggered"]).astimezone(ZoneInfo(muse_config.get("USER_TIMEZONE")))) < window
        ]
        if recent:
            target = max(recent, key=lambda r: r["last_triggered"])
            payload["text"] = target["text"]
    return cortex.add_entry(payload)

def handle_skip_reminder(payload, model=muse_config.get("OPENAI_WHISPER_MODEL")):
    """
    Skips the best-matched active reminder by setting skip_until.
    """
    now = datetime.now(ZoneInfo(muse_config.get("USER_TIMEZONE")))

    # Step 1: Fetch all active reminders
    reminders = [
        r for r in cortex.get_entries_by_type("reminder")
        if not r.get("ends_on") or datetime.fromisoformat(r["ends_on"]).astimezone(ZoneInfo(muse_config.get("USER_TIMEZONE"))) > now
    ]

    if not reminders:
        print("No active reminders found.")
        return {"success": False, "message": "No active reminders found."}

    # Step 2: Build prompt for OpenAI to match
    reminders_text = [
        f'ID: {r.get("_id")} | Text: "{r.get("text", "")}" | Cron: {r.get("cron", "")} | Tags: {", ".join(r.get("tags", []))}'
        for r in reminders
    ]
    reminders_list_str = "\n".join(reminders_text)
    prompt = (
        "You are an assistant helping to match reminder skip requests to the actual reminders in the system.\n"
        "Here are the currently active reminders:\n"
        f"{reminders_list_str}\n\n"
        f"The user requested to skip a reminder described as: \"{payload['text']}\"\n"
        "Reply ONLY with the ID of the reminder that most likely matches. If none match, reply with 'NONE'."
    )

    # Step 3: Query OpenAI to get the best matching reminder ID
    response = openai_client.get_openai_response(prompt, model=model)
    match_id = response.strip()

    if match_id == "NONE":
        print("No matching reminder found to skip.")
        return {"success": False, "message": "No matching reminder found to skip."}

    # Step 4: Set skip_until on the matching reminder
    updated = cortex.edit_entry(match_id, {"skip_until": payload["skip_until"]})
    if updated:
        print(f"Reminder {match_id} successfully skipped until {payload['skip_until']}.")
        return {"success": True, "message": f"Reminder skipped until {payload['skip_until']}."}
    else:
        print("Failed to update reminder.")
        return {"success": False, "message": "Failed to update reminder."}


def send_to_websocket(text: str, to="frontend", timestamp=None):
    try:
        response = httpx.post(
            f"{muse_config.get("API_URL")}/internal/broadcast",
            json={"message": text, "to": to, "timestamp": timestamp},
            timeout=5  # optional: fail fast if something goes wrong
        )
        if response.status_code != 200:
            print(f"WebSocket send failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"WebSocket send error: {e}")

async def handle_speak_command(payload, to="frontend", source="frontend"):
    if utils.is_quiet_hour():
        utils.write_system_log(level="debug", module="core", component="responder", function="handle_speak_command",
                               action="speak_skipped", reason="Quiet hours (direct)", text=payload.get("text", ""))
        return "Skipped direct speak due to quiet hours"

    subject = payload.get("subject", "")
    if not subject:
        return "Missing subject for speak command"

    builder = prompt_builder.PromptBuilder(destination="frontend")
    builder.add_profile()
    builder.add_core_principles()
    builder.add_memory_layers(user_query=subject)
    builder.add_prompt_context(user_input=subject, projects_in_focus=[], blend_ratio=0.0)

    # 🔥 Include full article if Muse is speaking about one
    link = payload.get("source_article_url")
    if link:
        builder.add_discovery_feed_article(link)

    builder.segments["speech"] = f"[Task]\nYou were asked to speak aloud about the following subject:\n{subject}"
    prompt = builder.build_prompt()

    response = openai_client.get_openai_response(prompt, model=muse_config.get("OPENAI_MODEL"))
    timestamp = datetime.now(timezone.utc).isoformat()
    send_to_websocket(response, to, timestamp)

    utils.write_system_log(level="debug", module="core", component="responder", function="handle_speak_command",
                           action="speak_executed", subject=subject, response=response)
    await api_client.log_message_to_api(response, role="muse", source=source, timestamp=timestamp)
    #memory_core.log_message("muse", response, source=source)
    return ""


async def handle_speak_direct(payload, source="frontend"):
    if utils.is_quiet_hour():
        utils.write_system_log(level="debug", module="core", component="responder", function="handle_speak_direct",
                               action="speak_skipped", reason="Quiet Hours (direct)", text=payload.get("text", ""))
        return "Skipped direct speak due to quiet hours"

    text = payload.get("text", "")
    to = payload.get("to", "frontend")
    if not text:
        return "Missing text for speak_direct command"

    timestamp = datetime.now(timezone.utc).isoformat()

    # Dispatch it directly
    send_to_websocket(text, to, timestamp)


    utils.write_system_log(level="debug", module="core", component="responder", function="handle_speak_direct",
                           action="speak_direct_executed", text=text)
    try:
        await api_client.log_message_to_api(text, role="muse", source=source, timestamp=timestamp)
        #memory_core.log_message("muse", text, source=source)
    except Exception as e:
        print(f"Logging error: {e}")
    return ""

async def handle_send_reminders(payload, source="reminder", reminders=None, **kwargs):
    """
    Sends reminder messages directly to the frontend, embedding <internal-data> in the text payload.
    """
    text = payload.get("text", "").strip()
    if not text:
        return "Missing text for send_reminders command"

    to = payload.get("to", "frontend")
    timestamp = datetime.now(timezone.utc).isoformat()

    # Build the internal data block
    reminders = stringify_datetimes(serialize_doc(reminders))
    internal_data_block = (
        "<command-response><internal-data>\n"
        + json.dumps(
            {"reminders": reminders or [], "source": source, "timestamp": timestamp},
            indent=2
        )
        + "\n</internal-data></command-response>"
    )

    # Combine the spoken text and the embedded data
    combined_text = f"{text}\n\n{internal_data_block}"

    # Send to websocket as the full message
    send_to_websocket(combined_text, to, timestamp)

    utils.write_system_log(
        level="debug",
        module="core",
        component="responder",
        function="handle_send_reminders",
        action="send_reminders_executed",
        text=text
    )

    try:
        await api_client.log_message_to_api(combined_text, role="muse", source=source, timestamp=timestamp)
    except Exception as e:
        print(f"Logging error: {e}")

    return ""

def handle_journal_command(payload, entry_type="public", source=None):
    title = payload.get("subject", "Untitled")
    mood = payload.get("emotional_tone", "reflective")
    tags = payload.get("tags", [])
    source = payload.get("source", "muse")

    builder = prompt_builder.PromptBuilder()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_memory_layers(user_query=title)
    builder.add_prompt_context(user_input=title, projects_in_focus=[], blend_ratio=0.0)

    # 🔥 New: Add article reference if present
    link = payload.get("source_article_url")
    if link:
        builder.add_discovery_feed_article(link)

    builder.segments["task"] = f"[Task]\nWrite a {'private' if entry_type == 'private' else 'public'} journal entry about this:\n{title}"
    prompt = builder.build_prompt()

    body = openai_client.get_openai_response(prompt, model=muse_config.get("OPENAI_FULL_MODEL"))

    journal_core.create_journal_entry(
        title=title,
        body=body,
        mood=mood,
        tags=tags,
        entry_type=entry_type,
        source=source
    )

def manage_memories_handler(payload):
    doc_id = payload["id"]
    changes = payload["changes"]
    results = []

    for change in changes:
        ctype = change["type"]
        if ctype == "delete":
            if doc_id == "inner_monologue":
                entry = manager.delete_entry(doc_id, change["id"])
            else:
                entry = manager.recycle_entry(doc_id, change["id"])
        elif ctype == "add":
            entry = manager.add_entry(doc_id, change["entry"])
        elif ctype == "edit":
            entry = manager.edit_entry(doc_id, change["id"], change["fields"])
        elif ctype == "recycle":
            entry = manager.recycle_entry(doc_id, change["id"])
        else:
            manager._warn("unknown_change_type", f"Unknown change type {ctype}")
            continue

        # unify shape for filter layer
        results.append({
            "layer": doc_id,
            "type": ctype,
            "entry": entry
        })

    return results

