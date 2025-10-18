# utils.py

import os
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
import re, json
from bson import ObjectId
from charset_normalizer import from_bytes
from cryptography.fernet import Fernet
from zoneinfo import ZoneInfo
from typing import Optional
from nanoid import generate
from app.config import muse_config

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
    from app.core import memory_core
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

def strip_command_blocks(text):
    # Extract both internal data and visible summary from each command-response block
    def summarize(match):
        internal = re.search(r"<internal-data>(.*?)</internal-data>", match.group(0), flags=re.DOTALL)
        visible = re.sub(r"<.*?>", "", match.group(0))  # strip all tags for readability
        if internal:
            try:
                data = json.loads(internal.group(1))
                return f"(System note) {visible.strip()} | Data: {json.dumps(data, ensure_ascii=False)}"
            except Exception:
                return f"(System note) {visible.strip()}"
        return f"(System note) {visible.strip()}"

    return re.sub(r"<command-response>.*?</command-response>", summarize, text, flags=re.DOTALL)

def format_context_entry(e):
    role = e.get("role", "")
    if role == "user":
        name = muse_config.get("USER_NAME") or "User"
    elif role == "muse":
        name = muse_config.get("MUSE_NAME") or "Muse"
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
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            time_str = str(ts)
    else:
        time_str = ""

    msg = e.get("message", "")
    # Sanitize command-response blocks
    msg = strip_command_blocks(msg)
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

def serialize_doc(doc):
    if isinstance(doc, dict):
        return {k: serialize_doc(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [serialize_doc(i) for i in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    else:
        return doc

def stringify_datetimes(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: stringify_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [stringify_datetimes(i) for i in obj]
    return obj

def ensure_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]

def smart_decode(file_bytes):
    result = from_bytes(file_bytes).best()
    if result is None:
        # As a last resort, decode as utf-8 with replacement
        return file_bytes.decode("utf-8", errors="replace")
    return str(result)

def split_by_word_boundary(text, max_chars):
    chunks = []
    start = 0
    while start < len(text):
        # Find the furthest space (word boundary) before max_chars
        end = min(start + max_chars, len(text))
        if end < len(text):
            # Only look for a space if we didn't reach the end
            space = text.rfind(' ', start, end)
            newline = text.rfind('\n', start, end)
            # Prefer newlines as breakpoints, then spaces
            split_at = max(newline, space)
            if split_at > start:
                end = split_at
        chunk = text[start:end].strip()
        if chunk:  # Avoid empty
            chunks.append(chunk)
        start = end
    return chunks

def smart_paragraph_split(text):
    # Normalize all line endings to \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

def chunk_file(
    file_bytes,
    encoding="utf-8",
    max_chunk_chars=4000,
    min_chunk_chars=500,
    strategy="regex",
    break_marker="\u200b"  # Zero-width space, invisible in text
):
    """
    Splits a file into non-overlapping, semantically reasonable chunks.
    Inserts an invisible zero-width space at chunk boundaries if a split occurs mid-paragraph.
    """
    try:
        text = smart_decode(file_bytes)
    except UnicodeDecodeError:
        raise ValueError("File decoding failed—unsupported encoding or binary file.")
    # This will split on two or more *any* line endings (handles \n, \r\n, or \r)
    paragraphs = re.split(r"(?:\r\n|\r|\n){2,}", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current = []
    current_len = 0
    start_line = 0
    lines_so_far = 0
    byte_offset = 0
    para_index = 0

    while para_index < len(paragraphs):
        para = paragraphs[para_index]
        para_len = len(para)

        if para_len > max_chunk_chars:
            # Paragraph itself is too big: split it up, invisibly marking breaks
            start = 0
            fragments = split_by_word_boundary(para, max_chunk_chars)
            for i, frag in enumerate(fragments):
                chunk_text = frag
                # Optionally add break_marker logic here if you still want it
                chunk_bytes = chunk_text.encode(encoding)
                chunk_lines = chunk_text.count("\n")
                end_line = lines_so_far + chunk_lines
                chunks.append({
                    "content": chunk_text,
                    "index": len(chunks),
                    "start_line": start_line,
                    "end_line": end_line,
                    "start_byte": byte_offset,
                    "end_byte": byte_offset + len(chunk_bytes),
                })
                byte_offset += len(chunk_bytes)
                lines_so_far = end_line
                start_line = end_line + 1
            para_index += 1
            continue

        # If current chunk is empty or can fit this paragraph, add it
        if not current or (current_len + para_len + 2) <= max_chunk_chars:
            current.append(para)
            current_len += para_len + 2
            para_index += 1
        else:
            # Finish current chunk
            chunk_text = "\n\n".join(current)
            chunk_bytes = chunk_text.encode(encoding)
            chunk_lines = chunk_text.count("\n")
            end_line = lines_so_far + chunk_lines
            chunks.append({
                "content": chunk_text,
                "index": len(chunks),
                "start_line": start_line,
                "end_line": end_line,
                "start_byte": byte_offset,
                "end_byte": byte_offset + len(chunk_bytes),
            })
            byte_offset += len(chunk_bytes)
            lines_so_far = end_line
            start_line = end_line + 1
            current = []
            current_len = 0

    # Add any leftovers as the final chunk
    if current:
        chunk_text = "\n\n".join(current)
        chunk_bytes = chunk_text.encode(encoding)
        chunk_lines = chunk_text.count("\n")
        end_line = lines_so_far + chunk_lines
        chunks.append({
            "content": chunk_text,
            "index": len(chunks),
            "start_line": start_line,
            "end_line": end_line,
            "start_byte": byte_offset,
            "end_byte": byte_offset + len(chunk_bytes),
        })

    # Merge tiny last chunk if necessary (avoids fragments)
    if (
        len(chunks) > 1
        and len(chunks[-1]["content"]) < min_chunk_chars
    ):
        prev = chunks[-2]
        last = chunks[-1]
        merged_text = prev["content"] + "\n\n" + last["content"]
        merged_bytes = merged_text.encode(encoding)
        chunks[-2] = {
            "content": merged_text,
            "index": prev["index"],
            "start_line": prev["start_line"],
            "end_line": last["end_line"],
            "start_byte": prev["start_byte"],
            "end_byte": prev["start_byte"] + len(merged_bytes),
        }
        chunks.pop()
    return chunks

def get_adaptive_top_k(min_top_k, default_top_k, num_injected_chunks):
    # Subtract 1 for 1, but never go below MIN_TOP_K
    return max(min_top_k, default_top_k - num_injected_chunks)

def generate_new_id(size=8):
    # default alphabet: [A-Za-z0-9_-]
    return generate(size=size)