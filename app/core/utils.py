# utils.py

import os
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
import re, json
from cryptography.fernet import Fernet
from zoneinfo import ZoneInfo
from typing import Optional
from app.config import muse_config
from app.core import memory_core
from app.databases.mongo_connector import mongo, mongo_system


LOG_LEVELS = {
    "debug": 10,
    "info": 20,
    "warn": 30,
    "error": 40,
}

def write_system_log(level, module=None, component=None, function=None, **fields):
    # Lookup global level (from config or db)
    if LOG_LEVELS[level] < LOG_LEVELS[muse_config.get("LOG_VERBOSITY")]:
        return  # Quietly drop logs under the threshold
    log_entry = {
        "timestamp": datetime.now(timezone.utc),
        "level": level,
        "module": module,
        "component": component,
        "function": function,
        **fields
    }
    try:
        mongo_system.insert_log("system_logs", log_entry)
    except Exception as e:
        with open("logs/systemlog_backup.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")


def get_formatted_datetime():
    return datetime.now(ZoneInfo(muse_config.get("USER_TIMEZONE"))).isoformat()

def is_quiet_hour() -> bool:
    """
    Returns True if the current local time is within quiet hours.
    Quiet hours can span across midnight.
    """
    quiet_start = muse_config.get("QUIET_HOURS_START")  # e.g., 23 = 11pm
    quiet_end = muse_config.get("QUIET_HOURS_END")  # e.g., 10 = 10am
    tz = muse_config.get("USER_TIMEZONE")

    current_hour = datetime.now(ZoneInfo(tz)).hour

    if quiet_start <= quiet_end:
        return quiet_start <= current_hour < quiet_end
    else:
        return current_hour >= quiet_start or current_hour < quiet_end

def get_quiet_hours_end_today() -> datetime:
    tz = ZoneInfo(muse_config.get("USER_TIMEZONE"))
    now = datetime.now(tz)
    end_hour = muse_config.get("QUIET_HOURS_END")  # e.g., 10

    # Create today's datetime at quiet hour end
    end_time = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)

    # If end hour has already passed today, return today’s time
    # If current time is still before end_hour, it's still quiet
    return end_time

def get_last_user_activity_timestamp() -> Optional[str]:
    """
    Returns the timestamp of the most recent user message from the conversation log.
    """
    last_user_entry = mongo.find_logs(
        collection_name="muse_conversations",
        query={"role": "user"},
        limit=1,
        sort_field="timestamp",
        ascending=False
    )
    if last_user_entry and last_user_entry[0].get("message"):
        return last_user_entry[0].get("timestamp")
    return None  # No user activity found


def parse_remind_time(remind_at_str):
    try:
        # If it's a full ISO datetime, parse normally
        if "T" in remind_at_str:
            return isoparse(remind_at_str).astimezone(ZoneInfo(muse_config.get("USER_TIMEZONE")))

        # Otherwise, assume HH:MM format
        hour, minute = map(int, remind_at_str.strip().split(":"))
        now = datetime.now(ZoneInfo(muse_config.get("USER_TIMEZONE")))
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    except Exception as e:
        print(f"⚠️ Failed to parse remind_at '{remind_at_str}': {e}")
        return None

def seconds_until(hour: int, minute: int = 0) -> int:
    now = datetime.now(ZoneInfo(muse_config.get("USER_TIMEZONE")))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target <= now:
        target += timedelta(days=1)  # Next occurrence

    return int((target - now).total_seconds())

def slugify(text):
    text = text.lower()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_encryption_key():
    entries = memory_core.cortex.get_entries_by_type("encryption_key")
    for e in entries:
        if e.get("type") == "encryption_key":
            return e.get("key_data")
    key = Fernet.generate_key().decode()
    memory_core.cortex.add_entry({
        "type": "encryption_key",
        "source": "journal_core",
        "created": get_formatted_datetime(),
        "key_data": key
    })
    return key

def encrypt_text(text: str) -> str:
    key = get_encryption_key()
    fernet = Fernet(key.encode())
    return fernet.encrypt(text.encode()).decode()

def decrypt_text(token: str) -> str:
    key = get_encryption_key()
    fernet = Fernet(key.encode())
    return fernet.decrypt(token.encode()).decode()


def format_context_entry(e):
    role = e.get("role", "")
    if role == "user":
        name = muse_config.get("USER_NAME")
    elif role == "muse":
        name = muse_config.get("MUSE_NAME")
    else:
        name = role.capitalize() if role else "Unknown"

    # Format timestamp
    ts = e.get("timestamp")
    if ts:
        try:
            if isinstance(ts, datetime):
                dt = ts
            else:
                dt = datetime.fromisoformat(ts)
            # Convert to user timezone if not naive
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo('UTC'))
            dt = dt.astimezone(ZoneInfo(muse_config.get("USER_TIMEZONE")))
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_str = str(ts)
    else:
        time_str = ""

    msg = e.get("message", "")
    # Combine
    return f"[{time_str}] {name}: {msg}"


def get_local_time():
    """
    Returns the current local time formatted cleanly.
    """
    now = datetime.now(ZoneInfo(muse_config.get("USER_TIMEZONE")))
    return now.strftime("%Y-%m-%d %H:%M")

def align_cron_for_croniter(cron_string):
    fields = cron_string.strip().split()

    if len(fields) == 7 and fields[5] == "*":
        # Save the seconds (field 0)
        seconds = fields[0]
        # Shift fields 1–5 left and reinsert seconds as field 5
        fields = fields[1:6] + [seconds, fields[6]]

    # Add /1 if the year field is a plain 4-digit year (e.g., 2025)
    if len(fields) == 7:
        year_field = fields[6]
        if year_field.isdigit() and len(year_field) == 4:
            fields[6] = f"{year_field}/1"

    return ' '.join(fields)
