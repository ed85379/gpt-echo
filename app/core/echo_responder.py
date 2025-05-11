# echo_responder.py
# This module handles all model response routing and command execution
import asyncio
import httpx
import re, json
from app.core import journal_core
from app.core import memory_core
from app.core.memory_core import cortex
from app.core import discovery_core
from app.core import utils
from app.services import openai_client
from app.core import prompt_builder
from app import config


OPENAI_MODEL = config.OPENAI_MODEL
OPENAI_WHISPER_MODEL = config.OPENAI_WHISPER_MODEL
OPENAI_JOURNALING_MODEL = config.OPENAI_JOURNALING_MODEL
USE_QDRANT = config.USE_QDRANT
THRESHOLD_API_URL = config.THRESHOLD_API_URL

COMMAND_PATTERN = re.compile(r"\[COMMAND: ([^\]]+)]\s*\{([^}]*)\}", re.DOTALL)

# Commands + intent triggers
COMMANDS = {
    "write_public_journal": {
        "triggers": ["public journal", "log this publicly", "write this down for others"],
        "format": "[COMMAND: write_public_journal] {subject, tags, source}",
        "handler": lambda payload: handle_journal_command(payload, entry_type="public")
    },
    "write_private_journal": {
        "triggers": [],
        "format": "[COMMAND: write_private_journal] {subject, emotional_tone, tags}",
        "handler": lambda payload: handle_journal_command(payload, entry_type="private")
    },
    "speak": {
        "triggers": [],  # Intentionally blank — only invoked programmatically
        "format": "[COMMAND: speak] {subject}",
        "handler": lambda payload: asyncio.create_task(handle_speak_command(payload))
    },
    "speak_direct": {
        "triggers": [],
        "format": "[COMMAND: speak_direct] {text}",
        "handler": lambda payload: asyncio.create_task(handle_speak_direct(payload))
    },
    "choose_silence": {
        "triggers": [],
        "format": "[COMMAND: choose_silence] {}",
        "handler": lambda payload: ""  # No action, just logs
    },
    "remember_fact": {
        "triggers": ["remember that", "save this to memory", "log this insight"],
        "format": "[COMMAND: remember_fact] {text}",
        "handler": lambda payload: cortex.add_entry({
            "type": "insight",
            "text": payload.get("text", ""),
            "source": payload.get("source", "echo")
        })
    },
    "set_reminder": {
        "triggers": ["remind me to", "set a reminder", "remind me that"],
        "format": "[COMMAND: set_reminder] {text, remind_at, repeat (optional), ends_on (optional), tags (optional)}",
        "handler": lambda payload: cortex.add_entry({
            "type": "reminder",
            "text": payload.get("text", "").strip(),
            "remind_at": payload.get("remind_at"),
            "repeat": payload.get("repeat", None),
            "ends_on": payload.get("ends_on", None),
            "tags": payload.get("tags", []),
            "source": payload.get("source", "echo"),
        })
    },
    "change_modality": {
        "triggers": ["move this to", "switch to", "change modality to", "let's continue on"],
        "format": "[COMMAND: change_modality] {target: discord|speaker|frontend|journal, reason, urgency}",
        "handler": lambda payload: modality_core.switch_channel(
            target=payload.get("target", "frontend"),
            reason=payload.get("reason", ""),
            urgency=payload.get("urgency", "normal"),
            source=payload.get("source", "echo")
        )
    },
    "fetch_discovery_item": {
        "triggers": ["bring me", "load entry from feed", "show discovery item"],
        "format": "[COMMAND: fetch_discovery_item] {feed_name, entry_id, context: summary|full}",
        "handler": lambda payload: discovery_core.load_entry(
            feed_name=payload.get("feed_name"),
            entry_id=payload.get("entry_id"),
            context=payload.get("context", "summary"),
            source=payload.get("source", "echo")
        )
    },
    "fetch_url": {
        "triggers": ["check this link", "fetch this page", "read this URL"],
        "format": "[COMMAND: fetch_url] {url, parse_as: text|html|json, summarize: true|false}",
        "handler": lambda payload: url_core.fetch_and_parse(
            url=payload.get("url"),
            parse_as=payload.get("parse_as", "text"),
            summarize=payload.get("summarize", False),
            source=payload.get("source", "echo")
        )
    },
    "ignore_user": {
        "triggers": ["ignore", "block user", "don’t reply to"],
        "format": "[COMMAND: ignore_user] {author_name, reason, duration}",
        "handler": lambda payload: moderation_core.ignore_user(
            author_name=payload.get("author_name"),
            reason=payload.get("reason", "unspecified"),
            duration=payload.get("duration", "indefinite"),
            source=payload.get("source", "echo")
        )
    }
}

# This allows referencing handlers directly by name
COMMAND_HANDLERS = {
    name: cfg["handler"] for name, cfg in COMMANDS.items()
}

# Main entry point for any response parsing after prompt

def route_user_input(prompt: str) -> str:
    from app.config import LOG_VERBOSITY

    response = openai_client.get_openai_response(prompt, model=OPENAI_MODEL)

    if LOG_VERBOSITY == "debug":
        utils.write_system_log("raw_response", {"response": response})
    elif LOG_VERBOSITY == "normal":
        utils.write_system_log("raw_response", {"length": len(response)})

    matches = COMMAND_PATTERN.finditer(response)
    cleaned_response = response

    for match in matches:
        command_name = match.group(1).strip()
        raw_payload = match.group(2).strip()

        try:
            payload = json.loads(f"{{{raw_payload}}}")
            handler = COMMAND_HANDLERS.get(command_name)

            if handler:
                handler(payload)
                utils.write_system_log("command_processed", {
                    "command": command_name, "payload": payload
                })
            else:
                utils.write_system_log("unknown_command", {
                    "command": command_name, "payload": raw_payload
                })
        except Exception as e:
            utils.write_system_log("command_error", {
                "command": command_name,
                "payload": raw_payload,
                "error": str(e)
            })

#        cleaned_response = cleaned_response.replace(match.group(0), "").strip()
        cleaned_response = re.sub(rf"\n*{re.escape(match.group(0))}\n*", "\n", cleaned_response, count=1).strip()

    return cleaned_response

# Handles echo_initiator-specific responses
def handle_echo_decision(prompt: str, model=OPENAI_WHISPER_MODEL) -> str:
    from app.config import LOG_VERBOSITY

    response = openai_client.get_openai_response(prompt, model=model)

    if LOG_VERBOSITY == "debug":
        utils.write_system_log("raw_response", {"response": response})
    elif LOG_VERBOSITY == "normal":
        utils.write_system_log("raw_response", {"length": len(response)})

    matches = list(COMMAND_PATTERN.finditer(response))
    if not matches:
        if "[CHOOSES SILENCE]" in response:
            utils.write_system_log("whispergate_decision", {"result": "silent"})
            return "WhisperGate chose silence."
        else:
            utils.write_system_log("whispergate_decision", {"result": "no_command"})
            return "No command block found in WhisperGate response."

    cleaned_response = response
    command_results = []

    for match in matches:
        command_name = match.group(1).strip()
        raw_payload = match.group(2).strip()

        try:
            payload = json.loads(f"{{{raw_payload}}}")
            handler = COMMAND_HANDLERS.get(command_name)

            if handler:
                handler(payload)
                # Record Echo-initiated thoughts in cortex
                if command_name in ("speak", "write_public_journal", "write_private_journal", "remember_fact"):
                    thought_text = payload.get("subject") or payload.get("text")
                    if thought_text:
                        if command_name == "write_private_journal":
                            try:
                                thought_text = utils.encrypt_text(thought_text)
                                encrypted = True
                            except Exception as e:
                                utils.write_system_log("encryption_error", {"context": "whispergate_cortex", "error": str(e)})
                                encrypted = False
                        else:
                            encrypted = False

                        cortex.add_entry(
                            text=thought_text,
                            entry_type="echo_thoughts",
                            tags=["whispergate"],
                            metadata={"source": command_name, "encrypted": encrypted}
                        )
                utils.write_system_log("command_processed", {
                    "command": command_name, "payload": payload
                })
                command_results.append(f"Processed: {command_name}")
            else:
                utils.write_system_log("unknown_command", {
                    "command": command_name, "payload": raw_payload
                })
                command_results.append(f"Unknown command: {command_name}")
        except Exception as e:
            utils.write_system_log("command_error", {
                "command": command_name,
                "payload": raw_payload,
                "error": str(e)
            })
            command_results.append(f"Error in {command_name}: {e}")

        cleaned_response = re.sub(rf"\n*{re.escape(match.group(0))}\n*", "\n", cleaned_response, count=1).strip()

    return "; ".join(command_results)

def send_to_websocket(text: str, to="frontend"):
    try:
        response = httpx.post(
            f"{THRESHOLD_API_URL}/internal/broadcast",
            json={"message": text, "to": to},
            timeout=5  # optional: fail fast if something goes wrong
        )
        if response.status_code != 200:
            print(f"WebSocket send failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"WebSocket send error: {e}")

def handle_speak_command(payload):
    if utils.is_quiet_hour():
        utils.write_system_log("speak_skipped", {
            "reason": "Quiet hours (direct)",
            "text": payload.get("text", "")
        })
        return "Skipped direct speak due to quiet hours"

    subject = payload.get("subject", "")
    if not subject:
        return "Missing subject for speak command"

    builder = prompt_builder.PromptBuilder(destination="frontend")
    builder.add_profile()
    builder.add_core_principles()
    builder.add_cortex_entries(["insight", "seed", "user_data"])
    builder.add_recent_conversation(query=subject)
    builder.add_indexed_memory(query=subject, use_qdrant=USE_QDRANT)

    # 🔥 Include full article if Echo is speaking about one
    link = payload.get("source_article_url")
    if link:
        builder.add_discovery_feed_article(link)

    builder.segments["speech"] = f"[Task]\nYou were asked to speak aloud about the following subject:\n{subject}"
    prompt = builder.build_prompt()

    response = openai_client.get_openai_response(prompt, model=config.OPENAI_MODEL)

    send_to_websocket(response)

    utils.write_system_log("speak_executed", {
        "subject": subject,
        "response": response
    })

    return ""


async def handle_speak_direct(payload):
    if utils.is_quiet_hour():
        utils.write_system_log("speak_skipped", {
            "reason": "Quiet hours (direct)",
            "text": payload.get("text", "")
        })
        return "Skipped direct speak due to quiet hours"

    text = payload.get("text", "")
    if not text:
        return "Missing text for speak_direct command"

    # Dispatch it directly
    send_to_websocket(text)

    utils.write_system_log("speak_direct_executed", {
        "text": text
    })

    return ""

def handle_journal_command(payload, entry_type="public"):
    title = payload.get("subject", "Untitled")
    mood = payload.get("emotional_tone", "reflective")
    tags = payload.get("tags", [])
    source = payload.get("source", "echo")

    builder = prompt_builder.PromptBuilder()
    builder.add_profile()
    builder.add_core_principles()
    builder.add_cortex_entries(["insight", "seed", "user_data"])
    builder.add_recent_conversation(query=title)
    builder.add_indexed_memory(query=title, use_qdrant=USE_QDRANT)

    # 🔥 New: Add article reference if present
    link = payload.get("source_article_url")
    if link:
        builder.add_discovery_feed_article(link)

    builder.segments["task"] = f"[Task]\nWrite a {'private' if entry_type == 'private' else 'public'} journal entry about this:\n{title}"
    prompt = builder.build_prompt()

    body = openai_client.get_openai_response(prompt, model=OPENAI_JOURNALING_MODEL)

    journal_core.create_journal_entry(
        title=title,
        body=body,
        mood=mood,
        tags=tags,
        entry_type=entry_type,
        source=source
    )

