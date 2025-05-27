# utils.py

import os
from datetime import datetime, timedelta
from dateutil.parser import isoparse
import re
import hashlib
from cryptography.fernet import Fernet
from zoneinfo import ZoneInfo
from typing import Optional
from app import config
from app.core import memory_core
from app.databases.mongo_connector import mongo



USER_TIMEZONE = config.USER_TIMEZONE
SYSTEM_LOGS_DIR = config.SYSTEM_LOGS_DIR
QUIET_HOURS_START = config.QUIET_HOURS_START
QUIET_HOURS_END = config.QUIET_HOURS_END
USER_NAME = config.USER_NAME
MUSE_NAME = config.MUSE_NAME

os.makedirs(SYSTEM_LOGS_DIR, exist_ok=True)

def write_system_log(entry_type, data):
    now = datetime.now(ZoneInfo(USER_TIMEZONE))
    timestamp = now.isoformat(timespec="milliseconds")
    log_entry = {
        "timestamp": timestamp,
        "type": entry_type,
        "data": data
    }

    date_str = now.strftime("%Y-%m-%d")
    filename = os.path.join(SYSTEM_LOGS_DIR, f"systemlog_{date_str}.jsonl")

    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{log_entry}\n")

def get_formatted_datetime():
    return datetime.now(ZoneInfo(USER_TIMEZONE)).isoformat()

def is_quiet_hour() -> bool:
    """
    Returns True if the current local time is within quiet hours.
    Quiet hours can span across midnight.
    """
    quiet_start = getattr(config, "QUIET_HOURS_START", 23)  # e.g., 23 = 11pm
    quiet_end = getattr(config, "QUIET_HOURS_END", 10)  # e.g., 10 = 10am
    tz = getattr(config, "USER_TIMEZONE", "UTC")

    current_hour = datetime.now(ZoneInfo(tz)).hour

    if quiet_start <= quiet_end:
        return quiet_start <= current_hour < quiet_end
    else:
        return current_hour >= quiet_start or current_hour < quiet_end

def get_quiet_hours_end_today() -> datetime:
    tz = ZoneInfo(config.USER_TIMEZONE)
    now = datetime.now(tz)
    end_hour = config.QUIET_HOURS_END  # e.g., 10

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
            return isoparse(remind_at_str).astimezone(ZoneInfo(config.USER_TIMEZONE))

        # Otherwise, assume HH:MM format
        hour, minute = map(int, remind_at_str.strip().split(":"))
        now = datetime.now(ZoneInfo(config.USER_TIMEZONE))
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    except Exception as e:
        print(f"⚠️ Failed to parse remind_at '{remind_at_str}': {e}")
        return None

def seconds_until(hour: int, minute: int = 0) -> int:
    now = datetime.now(ZoneInfo(config.USER_TIMEZONE))
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
        name = USER_NAME
    elif role == "muse":
        name = MUSE_NAME
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
            dt = dt.astimezone(ZoneInfo(USER_TIMEZONE))
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
    now = datetime.now(ZoneInfo(USER_TIMEZONE))
    return now.strftime("%Y-%m-%d %H:%M")

def align_cron_for_croniter(cron_string):
    fields = cron_string.strip().split()
    if len(fields) == 7 and fields[5] == "*":
        # Save the seconds (field 0)
        seconds = fields[0]
        # Shift fields 1–5 left
        fields = fields[1:6] + [seconds, fields[6]]
    return ' '.join(fields)