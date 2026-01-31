# muse_responder.py
# This module handles all model response routing and command execution
import asyncio
import httpx, time
import re, json
import humanize
from typing import Any, Dict, List, Iterator, NamedTuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.core import journal_core
from app.core.memory_core import cortex, manager
from app.core.utils import (write_system_log,
                            encrypt_text,
                            serialize_doc,
                            stringify_datetimes,
                            build_command_response_block,
                            )
from app.core.time_location_utils import is_quiet_hour, _load_user_location, parse_iso_datetime
from app.services.openai_client import get_openai_response
from app.config import muse_config
from app.core.states_core import set_motd
from app.core.reminders_core import handle_set, handle_edit, handle_skip, handle_snooze, handle_toggle, handle_search_reminders
from app.core.reminders_core import get_cron_description_safe, humanize_time, format_visible_reminders
from app.core.prompt_profiles import build_speak_prompt, build_journal_prompt
from app.services.openai_client import speak_openai_client, journal_openai_client
from app.api.queues import run_broadcast_queue, run_log_queue, run_index_queue, run_memory_index_queue, broadcast_queue, log_queue, index_queue, index_memory_queue



CMD_OPEN = re.compile(r"\[COMMAND:\s*([^\]]+)\]\s*", re.DOTALL)
CMD_CLOSE = "[/COMMAND]"

@dataclass
class CommandResult:
    name: str
    payload: Dict[str, Any]
    status: str          # "ok" | "error" | "unknown" | "parse_error" | "no_handler"
    error: Optional[str] = None
    visible: str = ""    # what the filter says is visible
    hidden: Dict[str, Any] = None  # what the filter marks as hidden

def project_command_result(result: dict, schema: dict, now=None) -> dict:
    if not isinstance(result, dict):
        return {"Message": str(result)}

    include = set(schema.get("include", []))
    exclude = set(schema.get("exclude", []))
    humanize_fields = set(schema.get("humanize", []))
    rename = schema.get("rename", {})

    def _project(obj, prefix=""):
        if not isinstance(obj, dict):
            return obj

        projected = {}
        for key, value in obj.items():
            full_key = f"{prefix}{key}" if prefix else key

            # include/exclude logic (flat keys only in this simple version)
            if include and full_key not in include:
                continue
            if full_key in exclude:
                continue

            label = rename.get(full_key, key)

            if full_key in humanize_fields and value:
                dt = parse_iso_datetime(value)
                if dt:
                    projected[label] = humanize.naturaltime(now - dt)
                else:
                    projected[label] = value  # fallback to raw string if parse fails
            elif isinstance(value, dict):
                projected[label] = _project(value, prefix=full_key + ".")
            else:
                projected[label] = value

        return projected

    return _project(result)


def format_system_note(cmd_name: str, result: dict, schema: dict | None = None) -> str:
    lines = [f"(System note)", f"- Command: `{cmd_name}`"]
    now = datetime.now(timezone.utc)
    if schema:
        projected = project_command_result(result, schema, now=now)
        for label, value in projected.items():
            # Skip label if it's just the cmd name repeated
            if label.lower() == "cmd":
                lines.append(f"- {value}")
            else:
                lines.append(f"- {label}: {value}")
        child_cmds = schema.get("child_commands")
        if child_cmds:
            lines.append("")
            lines.append("Available related commands:")

            for child_name in child_cmds:
                cmd_def = COMMANDS.get(child_name, {})
                triggers = cmd_def.get("triggers")
                fmt = cmd_def.get("format")


                lines.append("")
                lines.append(f"- Command: `{child_name}`")
                if triggers:
                    joined_triggers = ", ".join(f'    - "{t}"\n' for t in triggers)
                    lines.append(f"  Listen for phrases like:\n{joined_triggers}")
                if fmt:
                    lines.append("  Format:")
                    lines.append(f"    {fmt}")
    else:
        # Fallback: just show a generic success line
        msg = result.get("text") or result.get("message") if isinstance(result, dict) else None
        if msg:
            lines.append(f"- Message: {msg}")

    return "\n".join(lines)

def process_commands_in_response(
    response: str,
    *,
    source: Optional[str] = None,
    whispergate_data: Optional[Dict[str, Any]] = None,
    apply_filters: bool = True,
    strip_on_error: bool = True,
) -> (str, List[CommandResult]):
    """
    Unified command-processing core.

    - Parses all [COMMAND: ...] blocks from `response`
    - Executes handlers from COMMAND_HANDLERS
    - Optionally applies COMMANDS[cmd]["filter"] to handler results
    - Returns:
        cleaned_response: original text with command blocks removed or replaced
        results: list of CommandResult objects (for logging / summaries)
    """
    cleaned_parts: List[str] = []
    cursor = 0
    results: List[CommandResult] = []

    commands = list(extract_commands(response))
    if not commands:
        # No commands at all — return original text untouched
        return response, results

    for cm in commands:
        start, end = cm.span
        command_name = cm.name.strip()
        raw_payload = cm.json_text.strip()

        # Append any text before this command
        if start > cursor:
            cleaned_parts.append(response[cursor:start])

        # Default replacement if we end up stripping
        replacement = "\n"

        # Try to parse payload
        try:
            payload = json.loads(raw_payload)
        except Exception as e:
            write_system_log(
                level="error",
                module="core",
                component="command_core",
                function="process_commands_in_response",
                action="parse_payload_error",
                command=command_name,
                payload=raw_payload,
                error=str(e),
            )
            results.append(CommandResult(
                name=command_name,
                payload={},
                status="parse_error",
                error=str(e),
            ))
            if not strip_on_error:
                # keep the original block if you ever want that behavior
                cleaned_parts.append(response[start:end])
            else:
                cleaned_parts.append(replacement)
            cursor = end
            continue

        handler = COMMAND_HANDLERS.get(command_name)
        if not handler:
            write_system_log(
                level="warn",
                module="core",
                component="command_core",
                function="process_commands_in_response",
                action="unknown_command",
                command=command_name,
                payload=raw_payload,
            )
            results.append(CommandResult(
                name=command_name,
                payload=payload,
                status="no_handler",
            ))
            if not strip_on_error:
                cleaned_parts.append(response[start:end])
            else:
                cleaned_parts.append(replacement)
            cursor = end
            continue

        # Execute handler
        try:
            # Whispergate handlers may want extra kwargs
            extra_kwargs = whispergate_data or {}
            if source is not None:
                extra_kwargs = {**extra_kwargs, "source": source}

            handler_result = handler(payload, **extra_kwargs) \
                if extra_kwargs else handler(payload)

            # If handler returns nothing → we still consider it ok, just no visible text
            visible = ""
            hidden = {}

            if apply_filters and handler_result is not None:
                filter_fn = COMMANDS[command_name].get("filter")
                if filter_fn:
                    filtered = filter_fn(handler_result) or {}
                    visible = filtered.get("visible", "") or ""
                    hidden = filtered.get("hidden", {}) or {}

            results.append(CommandResult(
                name=command_name,
                payload=payload,
                status="ok",
                visible=visible,
                hidden=hidden,
            ))

            # Turn hidden dict into formatted string
            note_schema = COMMANDS[command_name].get("note_schema")
            hidden_str = format_system_note(cmd_name=command_name, result=hidden, schema=note_schema)


            # Decide what to inject into cleaned text
            if apply_filters and (visible or hidden):
                replacement = build_command_response_block(
                    visible=visible,
                    hidden=hidden_str,
                )
                cleaned_parts.append(replacement)
            else:
                cleaned_parts.append("\n")

        except Exception as e:
            write_system_log(
                level="error",
                module="core",
                component="command_core",
                function="process_commands_in_response",
                action="command_error",
                command=command_name,
                payload=payload,
                error=str(e),
            )
            results.append(CommandResult(
                name=command_name,
                payload=payload,
                status="error",
                error=str(e),
            ))
            if not strip_on_error:
                cleaned_parts.append(response[start:end])
            else:
                cleaned_parts.append("\n")

        cursor = end

    # Append trailing text
    if cursor < len(response):
        cleaned_parts.append(response[cursor:])

    cleaned_response = "".join(cleaned_parts)
    return cleaned_response, results

class CommandMatch(NamedTuple):
    name: str
    json_text: str
    span: tuple[int, int]     # (start, end) in the original text
    had_close: bool

def _balanced_object_end(text: str, start: int) -> Optional[int]:
    """
    Given text and index at the first '{', return index just after
    the matching closing '}' that balances the object. Handles strings and escapes.
    Returns None if unbalanced.
    """
    n = len(text)
    depth = 0
    i = start
    in_str = False
    esc = False
    while i < n:
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i + 1  # just after the closing brace
        i += 1
    return None

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)

def _find_fence_spans(text: str) -> list[tuple[int, int]]:
    """
    Return a list of (start, end) index pairs for all ```fenced``` code blocks
    in the given text. Spans are half-open: [start, end).
    """
    spans: list[tuple[int, int]] = []
    for m in FENCE_RE.finditer(text):
        spans.append((m.start(), m.end()))
    return spans

def _in_fence(pos: int, spans: list[tuple[int, int]]) -> bool:
    """
    True if the given character index `pos` lies inside any fenced span.
    """
    for start, end in spans:
        if start <= pos < end:
            return True
    return False

def extract_commands(text: str) -> Iterator[CommandMatch]:
    """
    Yields all command blocks in order. Each block:
      - [COMMAND: name] { ...balanced JSON... } [/COMMAND]?   (closing optional)
    Multiple commands per response are handled safely.
    """
    fence_spans = _find_fence_spans(text)

    def is_in_fence(pos: int) -> bool:
        return _in_fence(pos, fence_spans)

    i, n = 0, len(text)
    while True:
        m = CMD_OPEN.search(text, i)
        if not m:
            break

        # If the [COMMAND: ...] header is inside a fenced block, skip it entirely
        if is_in_fence(m.start()):
            i = m.end()
            continue

        name = m.group(1).strip()
        pos = m.end()

        lbrace = text.find("{", pos)
        if lbrace == -1 or is_in_fence(lbrace):
            # No JSON payload after header, or JSON starts in a fence — skip
            i = pos
            continue

        rbr_end = _balanced_object_end(text, lbrace)
        if rbr_end is None or is_in_fence(rbr_end - 1):
            # Unbalanced JSON, or closing brace in a fence — skip
            i = pos
            continue

        json_text = text[lbrace:rbr_end]

        # Optional closing tag
        k = rbr_end
        while k < n and text[k].isspace():
            k += 1
        had_close = text.startswith(CMD_CLOSE, k) and not is_in_fence(k)
        end = k + len(CMD_CLOSE) if had_close else rbr_end

        yield CommandMatch(
            name=name,
            json_text=json_text,
            span=(m.start(), end),
            had_close=had_close,
        )
        i = end

# Commands + intent triggers
COMMANDS = {
    "write_public_journal": {
        "triggers": ["public journal", "log this publicly", "write this down for others"],
        "format": "[COMMAND: write_public_journal] {subject, emotional_tone, tags, source_article_url} [/COMMAND]",
        "handler": lambda payload, **kwargs: asyncio.create_task(handle_journal_command(payload, entry_type="public", **kwargs))
    },
    "write_private_journal": {
        "triggers": ["write private journal"],
        "format": "[COMMAND: write_private_journal] {subject, emotional_tone, tags, source_article_url} [/COMMAND]",
        "handler": lambda payload, **kwargs: asyncio.create_task(handle_journal_command(payload, entry_type="private", **kwargs))
    },
    "set_motd": {
        "triggers": [],  # Intentionally blank — only invoked by the muse
        "format": "[COMMAND: set_motd] {text: \"... your message here ...\"} [/COMMAND]",
        "handler": lambda payload, **kwargs: handle_set_motd(payload, **kwargs),
        "filter": lambda result: {
            "visible": "",
            "hidden": result
        },
        "note_schema": {
            "include": ["cmd", "text"],
            "rename": {
                "cmd": "Note",
                "text": "MOTD",
            },
        },
    },
    "speak": {
        "triggers": [],  # Intentionally blank — only by the muse
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
            "visible": f"{muse_config.get('MUSE_NAME')} has saved a fact: {entry.get('text')}",
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
            "visible": f"{muse_config.get('MUSE_NAME')} has saved a project fact: {entry.get('text')}",
            "hidden": entry
        },
        "note_schema": {
            "include": ["doc_id", "id", "text"],
            "rename": {
                "doc_id": "layer_id",
                "id": "ID",
                "text": "text",
            },
        },
    },
    "record_userinfo": {
        "triggers": ["something about me", "I really like", "I don’t like when", "my habit is", "I prefer"],
        "format": "[COMMAND: record_userinfo] {text} [/COMMAND]",
        "handler": lambda payload: manager.add_entry("user_info", {"text": payload.get("text")}),
        "filter": lambda entry: {
            "visible": f"{muse_config.get('MUSE_NAME')} has learned something about you: {entry.get('text')}",
            "hidden": entry
        },
        "note_schema": {
            "include": ["doc_id", "id", "text"],
            "rename": {
                "doc_id": "layer_id",
                "id": "ID",
                "text": "text",
            },
        },
    },
    "realize_insight": {
        "triggers": ["breakthrough", "becoming", "I noticed something", "you tend to", "It would be amazing if"],
        "format": "[COMMAND: realize_insight] {text} [/COMMAND]",
        "handler": lambda payload: manager.add_entry("insights", {"text": payload.get("text")}),
        "filter": lambda entry: {
            "visible": f"{muse_config.get('MUSE_NAME')} has realized something: {entry.get('text')}",
            "hidden": entry
        },
        "note_schema": {
            "include": ["doc_id", "id", "text"],
            "rename": {
                "doc_id": "layer_id",
                "id": "ID",
                "text": "text",
            },
        },
    },
    "note_to_self": {
        "triggers": ["thinking aloud", "keep in mind", "note this", "I need to remember", "consider this"],
        "format": "[COMMAND: note_to_self] {text} [/COMMAND]",
        "handler": lambda payload: manager.add_entry("inner_monologue", {"text": payload.get("text")}),
        "filter": lambda entry: {
            "visible": f"{muse_config.get('MUSE_NAME')} has remembered something: {entry.get('text')}",
            "hidden": entry
        },
        "note_schema": {
            "include": ["doc_id", "id", "text"],
            "rename": {
                "doc_id": "layer_id",
                "id": "ID",
                "text": "text",
            },
        },
    },
    "manage_memories": {
        "triggers": ["edit that memory", "edit this memory", "update that memory", "delete that memory", "forget that"],
        "format": "[COMMAND: manage_memories] {id: <layer_id>, changes: [{type: add|edit|delete, ...}]} [/COMMAND]\n"
                "# Add\n"
                "[COMMAND: manage_memories] {\"id\": \"insights\", \"changes\": [{\"type\": \"add\", \"entry\": {\"text\": \"...\"}}]} [/COMMAND]\n"
                "# Edit\n"
                "[COMMAND: manage_memories] {\"id\": \"insights\", \"changes\": [{\"type\": \"edit\", \"id\": \"<entry_id>\", \"fields\": {\"text\": \"...\"}}]} [/COMMAND]\n"
                "# Delete\n"
                "[COMMAND: manage_memories] {\"id\": \"insights\", \"changes\": [{\"type\": \"delete\", \"id\": \"<entry_id>\"}]} [/COMMAND]",
        "handler": lambda payload: manage_memories_handler(payload),

        "filter": lambda results: {
            "visible": "\n".join([
                (
                    f"{muse_config.get('MUSE_NAME')} "
                    f"{'added to' if r['type']=='add' else 'edited in' if r['type']=='edit' else 'deleted from' if r['type']=='delete' else 'updated in'} "
                    f"{r['layer'].replace('_', ' ').title()}: "
                    f"{(r['entry'].get('text') or r['entry'].get('id', ''))}"
                )
                for r in results
            ]),
            "hidden": {
                "layer": results[0]["layer"],
                "type": results[0]["type"],
                "id": results[0]["entry"].get("id"),
                "text": results[0]["entry"].get("text"),
            },
        },
        "note_schema": {
            "include": ["layer", "type", "id", "text"],
            "rename": {
                "layer": "Layer",
                "type": "Change",
                "id": "ID",
                "text": "Text",
            },
        },
    },
    "set_reminder": {
        "triggers": ["remind me to", "set a reminder", "remind me that", "set an alarm", "set a schedule"],
        "format": (
            "[COMMAND: set_reminder] {\"text\": \"<meaningful description of the reminder>\", \"schedule\": {\"minute\":0-59, \"hour\":0-23, \"day\":1-31, \"dow\":0-6, \"month\":1-12, \"year\":YYYY}, \"ends_on\": \"<ISO 8601 datetime, optional>\", \"notification_offset\": \"<duration before trigger, e.g. '10m' or '2h', optional>\", \"early_only\": <Boolean - optional>} [/COMMAND]\n\n"
            "Notes:\n"
            "  - `text`: Clear description of what the reminder is for (e.g. 'take vitamins').\n"
            "  - `schedule`: Parsed cron-like structure, with each field as an integer or wildcard '*'.\n"
            "  - `ends_on`: Optional cutoff date/time in ISO 8601 format. The reminder will not fire after this.\n"
            "  - `notification_offset`: Optional early warning, expressed as a relative duration before the scheduled time.\n"
            "  - `early_only`: If a notification_offset is set, and the user only wants the early notification, set this to true.\n"
            "  - For one‑time reminders, set an `ends_on` timestamp set to after the reminder would fire, so the reminder expires after firing once.\n"
        ),
        "handler": lambda payload: handle_set(
            {
                "text": payload.get("text"),
                "schedule": payload.get("schedule"),
                "ends_on": payload.get("ends_on"),
                "notification_offset": payload.get("notification_offset"),
                "early_only": payload.get("early_only")
            }
        ),
        "filter": lambda entry: {
            "visible": f"Reminder set: {format_visible_reminders(entry)}",
            "hidden": entry
        },
        "note_schema": {
            "exclude": ["created_on", "updated_on", "cron", "early_notification"],
            "child_commands": ["edit_reminder", "snooze_reminder", "skip_reminder", "toggle_reminder"]
        }
    },
    "edit_reminder": {
        "triggers": ["update reminder", "change reminder", "fix schedule"],
        "format": (
            "[COMMAND: edit_reminder] {\"id\": <entry_id>, \"text\": \"<meaningful description of the reminder>\", \"schedule\": {\"minute\":0-59, \"hour\":0-23, \"day\":1-31, \"dow\":0-6, \"month\":1-12, \"year\":YYYY}, \"ends_on\": \"<ISO 8601 datetime, optional>\", \"notification_offset\": \"<duration before trigger, e.g. '10m' or '2h', optional>\", \"early_only\": <Boolean - optional>} [/COMMAND]\n\n"
            "  Notes:\n"
            "  - `id`: To edit an existing reminder, use the entry_id from the reminder shown above.\n"
            "  The following are all optional for edits. You only need to enter what needs to be changed:\n"
            "  - `text`: Clear description of what the reminder is for (e.g. 'take vitamins').\n"
            "  - `schedule`: Parsed cron-like structure, with each field as an integer or wildcard '*'.\n"
            "  - `ends_on`: Optional cutoff date/time in ISO 8601 format. The reminder will not fire after this.\n"
            "  - `notification_offset`: Optional early warning, expressed as a relative duration before the scheduled time.\n"
            "  - `early_only`: If a notification_offset is set, and the user only wants the early notification, set this to true.\n"
        ),
        "handler": lambda payload: handle_edit(
            {
                "id": payload.get("id"),
                "text": payload.get("text"),
                "schedule": payload.get("schedule"),
                "ends_on": payload.get("ends_on"),
                "notification_offset": payload.get("notification_offset"),
                "early_only": payload.get("early_only")
            }
        ),
        "filter": lambda entry: {
            "visible": f"Reminder edited: {format_visible_reminders(entry)}",
            "hidden": entry
        },
        "note_schema": {
            "exclude": ["created_on", "updated_on", "cron", "early_notification"],
            "child_commands": ["edit_reminder", "snooze_reminder", "skip_reminder", "toggle_reminder"]
        }
    },
    "snooze_reminder": {
        "triggers": ["snooze reminder", "remind me again in", "let me know again in"],
        "format": (
            "[COMMAND: snooze_reminder] {\"id\": <entry_id>, \"snooze_until\": \"<ISO 8601 datetime>\"} [/COMMAND]\n\n"
            "  Notes:\n"
            "  - `id`: To edit an existing reminder, use the entry_id from the reminder shown above.\n"
            "  - `snooze_until`: Date/time in ISO 8601 format in user's timezone. The reminder will fire again at this time.\n"
        ),
        "handler": lambda payload: handle_snooze(
            {
                "id": payload.get("id"),
                "snooze_until": payload.get("snooze_until"),
            }
        ),
        "filter": lambda entry: {
            "visible": f"Reminder snoozed until: {entry.get('snooze_until')}",
            "hidden": entry
        },
        "note_schema": {
            "exclude": ["created_on", "updated_on", "cron", "early_notification"],
            "child_commands": ["edit_reminder", "snooze_reminder", "skip_reminder", "toggle_reminder"]
        }
    },
    "skip_reminder": {
        "triggers": ["skip reminder", "disable reminder until", "pause reminder"],
        "format": (
            "[COMMAND: skip_reminder] {\"id\": <entry_id>, \"skip_until\": \"<ISO 8601 datetime>\"} [/COMMAND]\n\n"
            "  Notes:\n"
            "  - `id`: To edit an existing reminder, use the entry_id from the reminder shown above.\n"
            "  - `skip_until`: Date/time in ISO 8601 format in user's timezone. The reminder won't fire again until after this time.\n"
        ),
        "handler": lambda payload: handle_skip(
            {
                "id": payload.get("id"),
                "skip_until": payload.get("skip_until"),
            }
        ),
        "filter": lambda entry: {
            "visible": f"Reminder paused until: {entry.get('skip_until')}",
            "hidden": entry
        },
        "note_schema": {
            "exclude": ["created_on", "updated_on", "cron", "early_notification"],
            "child_commands": ["edit_reminder", "snooze_reminder", "skip_reminder", "toggle_reminder"]
        }
    },
    "toggle_reminder": {
        "triggers": ["cancel reminder", "disable reminder", "don't notify again"],
        "format": (
            "[COMMAND: toggle_reminder] {\"id\": <entry_id>, \"status\": \"enabled/disabled\"} [/COMMAND]\n\n"
            "  Notes:\n"
            "  - `id`: To edit an existing reminder, use the entry_id from the reminder shown above.\n"
            "  - `status`: Set to either 'enabled' or 'disabled'. Disabling the reminder will prevent all future notifications.\n"
        ),
        "handler": lambda payload: handle_toggle(
            {
                "id": payload.get("id"),
                "status": payload.get("status"),
            }
        ),
        "filter": lambda entry: {
            "visible": f"Reminder {entry.get('status')}",
            "hidden": entry
        },
        "note_schema": {
            "exclude": ["created_on", "updated_on", "cron", "early_notification"],
            "child_commands": ["edit_reminder", "snooze_reminder", "skip_reminder", "toggle_reminder"]
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
        "filter": lambda data: {
            "visible": (
                f"[Search query] {data['query']}\n"
                + "\n".join([
                    f"[Reminder found: (id - {r['id']}) {format_visible_reminders(r)}]"
                    for r in data["results"]
                ])
                if data["results"]
                else f"[Search query] {data['query']}\n[No matching reminders found.]"
            ),
            "hidden": data["results"]
        },
        "note_schema": {
            "exclude": ["created_on", "updated_on", "cron", "early_notification"],
            "child_commands": ["edit_reminder", "snooze_reminder", "skip_reminder", "toggle_reminder"]
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
    }
}

# This allows referencing handlers directly by name
COMMAND_HANDLERS = {
    name: cfg["handler"] for name, cfg in COMMANDS.items()
}

FENCE_PATTERN = re.compile(
    r"(```.*?```|~~~.*?~~~)",
    re.DOTALL
)

def normalize_muse_experience_tags(text: str) -> str:
    """
    Normalize <muse-experience> tags in non-fenced text only.

    - Skips anything inside ```...``` or ~~~...~~~ fences
    - Normalizes [] / () to <>
    - Appends missing </muse-experience> if there’s an opening tag
    """
    if not isinstance(text, str):
        return text

    # Split into segments: text and fenced blocks
    parts = []
    last_end = 0

    for m in FENCE_PATTERN.finditer(text):
        # non-fenced chunk before this fence
        if m.start() > last_end:
            parts.append(("plain", text[last_end:m.start()]))
        # the fenced chunk itself
        parts.append(("fence", m.group(0)))
        last_end = m.end()

    # trailing non-fenced chunk
    if last_end < len(text):
        parts.append(("plain", text[last_end:]))

    def _normalize_plain(chunk: str) -> str:
        # 1) Normalize bracket types for open/close tags
        chunk = re.sub(
            r'[\[\(]\s*muse-experience\s*[\]\)]',
            '<muse-experience>',
            chunk,
            flags=re.IGNORECASE,
        )
        chunk = re.sub(
            r'[\[\(]\s*/\s*muse-experience\s*[\]\)]',
            '</muse-experience>',
            chunk,
            flags=re.IGNORECASE,
        )

        # 2) Ensure closing tag if there’s an opening
        open_tag_pattern = re.compile(r'<\s*muse-experience\s*>', re.IGNORECASE)
        close_tag_pattern = re.compile(r'<\s*/\s*muse-experience\s*>', re.IGNORECASE)

        has_open = bool(open_tag_pattern.search(chunk))
        has_close = bool(close_tag_pattern.search(chunk))

        if has_open and not has_close:
            chunk = chunk.rstrip() + '\n</muse-experience>'

        return chunk

    normalized_parts = []
    for kind, chunk in parts:
        if kind == "plain":
            normalized_parts.append(_normalize_plain(chunk))
        else:
            # fence: leave exactly as-is
            normalized_parts.append(chunk)

    return "".join(normalized_parts)
# Main entry point for any response parsing after prompt

def route_user_input(
        dev_prompt: str,
        user_prompt: str,
        images=None,
        client=None,
        prompt_type="api"
) -> str:

    response = get_openai_response(
        dev_prompt,
        user_prompt,
        client=client,
        prompt_type=prompt_type,
        images=images,
        model=muse_config.get("OPENAI_MODEL")
    )

    # Normalize muse-experience tags outside of fenced code blocks
    response = normalize_muse_experience_tags(response)

    write_system_log(
        level="debug",
        module="core",
        component="responder",
        function="route_user_input",
        action="raw_response",
        response=response
    )

    cleaned_response, cmd_results = process_commands_in_response(
        response,
        apply_filters=True,      # use COMMANDS[cmd]["filter"]
        strip_on_error=True,     # keep UI clean
    )

    # Optional: log a compact summary of what ran
    if cmd_results:
        summary = "; ".join(
            f"{r.name}:{r.status}" for r in cmd_results
        )
        write_system_log(
            level="info",
            module="core",
            component="responder",
            function="route_user_input",
            action="commands_processed",
            summary=summary,
        )

    return cleaned_response

# Handles muse_initiator-specific responses
def handle_muse_decision(
    dev_prompt,
    user_prompt,
    client,
    model=muse_config.get("OPENAI_WHISPER_MODEL"),
    source=None,
    whispergate_data=None
) -> str:
    """
    Processes WhisperGate (muse) backend decisions using the unified command extraction pipeline.
    Returns a terse summary string of processing results
    (e.g., 'Processed: speak; Error in remember_fact: ...').
    """
    response = get_openai_response(
        dev_prompt,
        user_prompt,
        client,
        prompt_type="whispergate",
        images=None,
        model=model
    )
    print(f"WHISPERGATE COMMAND: {response}")

    write_system_log(
        level="debug",
        module="core",
        component="responder",
        function="handle_muse_decision",
        action="raw_response",
        response=response
    )

    # Silence handling — returns early without attempting command parse.
    if "[CHOOSES SILENCE]" in response:
        write_system_log(
            level="debug",
            module="core",
            component="responder",
            function="handle_muse_decision",
            action="wispergate_decision",
            result="silent"
        )
        return "WhisperGate chose silence."

    cleaned_response, cmd_results = process_commands_in_response(
        response,
        source=source,
        whispergate_data=whispergate_data,
        apply_filters=False,     # no <command-response> wrapping needed
        strip_on_error=True,
    )

    if not cmd_results:
        write_system_log(
            level="warn",
            module="core",
            component="responder",
            function="handle_muse_decision",
            action="wispergate_decision",
            result="No command block found in WhisperGate response."
        )
        return "No command block found in WhisperGate response."

    # Log each command result
    for r in cmd_results:
        level = "info" if r.status == "ok" else "warn" if r.status in ("no_handler", "parse_error") else "error"
        write_system_log(
            level=level,
            module="core",
            component="responder",
            function="handle_muse_decision",
            action="command_processed",
            command=r.name,
            status=r.status,
            error=r.error,
            payload=r.payload,
        )

    # Build terse summary string
    summary_parts = []
    for r in cmd_results:
        if r.status == "ok":
            summary_parts.append(f"Processed: {r.name}")
        elif r.status == "no_handler":
            summary_parts.append(f"Unknown command: {r.name}")
        elif r.status == "parse_error":
            summary_parts.append(f"Error in {r.name}: invalid JSON payload")
        else:  # "error"
            summary_parts.append(f"Error in {r.name}: {r.error}")

    return "; ".join(summary_parts)

def handle_reminder(payload):
    loc = _load_user_location()
    if "snoozed" in payload.get("tags", []):
        now = datetime.now(ZoneInfo(loc.timezone))
        window = timedelta(minutes=10)
        recent = [
            r for r in cortex.get_entries_by_type("reminder")
            if r.get("last_triggered")
            and (now - datetime.fromisoformat(r["last_triggered"]).astimezone(ZoneInfo(loc.timezone))) < window
        ]
        if recent:
            target = max(recent, key=lambda r: r["last_triggered"])
            payload["text"] = target["text"]
    return cortex.add_entry(payload)


def send_to_websocket(text: str, to="frontend", timestamp=None, retries=3, delay=0.3):
    payload = {"message": text, "to": to, "timestamp": timestamp}
    for attempt in range(1, retries + 1):
        try:
            response = httpx.post(
                f"{muse_config.get('API_URL')}/api/muse/speak",
                json=payload,
                timeout=5
            )
            if response.status_code == 200:
                return True
            else:
                print(f"WebSocket send failed ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"WebSocket send attempt {attempt} error: {e}")
        if attempt < retries:
            time.sleep(delay * attempt)
    print("WebSocket send gave up after retries.")
    return False

def handle_set_motd(payload, source=None):
    text = payload.get("text", "")
    if set_motd(text):
        if source:
            timestamp = datetime.now(timezone.utc).isoformat()
            try:
                asyncio.create_task(log_queue.put({
                    "role": "system",
                    "message": f"New MOTD set by {source} — {text}",
                    "source": source,
                    "timestamp": timestamp,
                    "skip_index": True
                }))
            except Exception as e:
                print(f"Logging error: {e}")
        return {
            "cmd": f"{muse_config.get("MUSE_NAME")} has set a new MOTD",
            "text": text,
        }

    else:
        return {
            "cmd": "set_motd",
            "error": "Setting MOTD failed",
        }

async def handle_speak_command(payload, to="frontend", source="frontend"):
    """
    This is intended for when the AI prompts itself to speak
    """
    if is_quiet_hour():
        write_system_log(level="debug", module="core", component="responder", function="handle_speak_command",
                               action="speak_skipped", reason="Quiet hours (direct)", text=payload.get("text", ""))
        return "Skipped direct speak due to quiet hours"

    subject = payload.get("subject", "")
    if not subject:
        return "Missing subject for speak command"

    dev_prompt, user_prompt = build_speak_prompt(subject=subject, payload=payload, destination="frontend")

    response = get_openai_response(dev_prompt, user_prompt, client=speak_openai_client, prompt_type="api", model=muse_config.get("OPENAI_MODEL"))
    # Normalize muse-experience tags outside of fenced code blocks
    response = normalize_muse_experience_tags(response)

    timestamp = datetime.now(timezone.utc).isoformat()
    send_to_websocket(response, to, timestamp)

    write_system_log(level="debug", module="core", component="responder", function="handle_speak_command",
                           action="speak_executed", subject=subject, response=response)
    await log_queue.put({
        "role": "muse",
        "message": response,
        "source": "frontend", # hard-coded to ignore source, so these will always be in SOURCES_CHAT
        "timestamp": timestamp
    })
    return ""


async def handle_speak_direct(payload, source="frontend"):
    """
    This is intended for when the AI tells itself exactly what to say over another interface
    """
    if is_quiet_hour():
        write_system_log(level="debug", module="core", component="responder", function="handle_speak_direct",
                               action="speak_skipped", reason="Quiet Hours (direct)", text=payload.get("text", ""))
        return "Skipped direct speak due to quiet hours"

    text = payload.get("text", "")
    to = payload.get("to", "frontend")
    if not text:
        return "Missing text for speak_direct command"

    timestamp = datetime.now(timezone.utc).isoformat()

    # Dispatch it directly
    send_to_websocket(text, to, timestamp)

    write_system_log(level="debug", module="core", component="responder", function="handle_speak_direct",
                           action="speak_direct_executed", text=text)
    try:
        await log_queue.put({
            "role": "muse",
            "message": text,
            "source": source,
            "timestamp": timestamp,
        })

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
    hidden = {
        "reminders": reminders or [],
        "source": source,
        "timestamp": timestamp,
    }

    # Turn hidden dict into formatted string

    note_schema = {
        "exclude": ["created_on", "updated_on", "cron", "early_notification"],
        "child_commands": ["edit_reminder", "snooze_reminder", "skip_reminder", "toggle_reminder"]
    }
    notes = []
    for r in reminders:
        #notes.append("---")
        formatted = format_system_note(
            cmd_name="send_reminder",
            result=r,
            schema=note_schema,
        )
        notes.append(formatted)
        notes.append("")
    hidden_str = "\n".join(notes)

    internal_data_block = build_command_response_block(
        visible="",  # or some summary if you ever want one
        hidden=hidden_str,
    )

    # Combine the spoken text and the embedded data
    combined_text = f"{text}\n\n{internal_data_block}"

    # Send to websocket as the full message
    send_to_websocket(combined_text, to, timestamp)


    write_system_log(
        level="debug",
        module="core",
        component="responder",
        function="handle_send_reminders",
        action="send_reminders_executed",
        text=text
    )

    try:
        await log_queue.put({
            "role": "muse",
            "message": combined_text,
            "source": source,
            "timestamp": timestamp,
            "skip_index": True
        })
    except Exception as e:
        print(f"Logging error: {e}")

    return ""

async def handle_journal_command(payload, entry_type="public", source=None):
    subject = payload.get("subject", "Untitled")
    mood = payload.get("emotional_tone", "reflective")
    tags = payload.get("tags", [])
    source = "whispergate"

    dev_prompt, user_prompt = build_journal_prompt(subject=subject, payload=payload)

    response = get_openai_response(dev_prompt, user_prompt, client=journal_openai_client, prompt_type="journal", model=muse_config.get("OPENAI_FULL_MODEL"))

    journal_core.create_journal_entry(
        title=subject,
        body=response,
        mood=mood,
        tags=tags,
        entry_type=entry_type,
        source=source
    )
    timestamp = datetime.now(timezone.utc).isoformat()
    excerpt = response[:160].rsplit(" ", 1)[0] + "…"
    await log_queue.put({
        "role": "system",
        "message": (
                f"New journal entry by Iris — {entry_type} — “{subject}”"
                + (f"\nExcerpt: {excerpt}" if excerpt else "")
        ),
        "source": source,
        "timestamp": timestamp,
        "skip_index": True
    })

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

