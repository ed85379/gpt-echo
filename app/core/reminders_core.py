# reminders_core.py
from datetime import timedelta, datetime, timezone
import re
from pytimeparse2 import parse
from croniter import croniter
from zoneinfo import ZoneInfo
from cron_descriptor import get_description
from app.core.memory_core import manager, cortex
from app.config import muse_config
from app.core.utils import serialize_doc

def user_tz():
    return ZoneInfo(muse_config.get("USER_TIMEZONE"))

def format_visible_reminders(entry: dict) -> str:
    parts = [f"{entry['text']} — {humanize_time(get_cron_description_safe(entry['cron']))}"]

    if entry.get("notification_offset"):
        parts.append(f"(early: {entry['notification_offset']})")

    if entry.get("ends_on"):
        parts.append(f"(ends: {entry['ends_on']})")

    return " ".join(parts)

def humanize_time(desc: str) -> str:
    # Look for hh:mm patterns and convert to 12-hour with AM/PM
    return re.sub(r"\b(\d{1,2}):(\d{2})\b",
                  lambda m: datetime.strptime(m.group(0), "%H:%M").strftime("%I:%M %p"),
                  desc)

def get_cron_description_safe(cron_str: str) -> str:
    # cron_descriptor expects 5 fields, so drop extras
    fields = cron_str.split()
    if len(fields) > 5:
        fields = fields[:5]
    trimmed = " ".join(fields)
    return get_description(trimmed)

def normalize_dt(dt) -> datetime:
    """
    Ensure a datetime is tz-aware in the user timezone.
    Accepts ISO strings, naive datetimes, or already-aware datetimes.
    Converts stored UTC times to local.
    """
    tz = user_tz()
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if dt.tzinfo is None:
        # Stored in UTC → make aware as UTC first
        dt = dt.replace(tzinfo=timezone.utc)
    # Then convert everything to user zone
    return dt.astimezone(tz)

def schedule_to_cron(schedule: dict) -> str:
    """
    Convert a schedule JSON object into a valid cron string for croniter.
    Uses 5 fields by default (minute, hour, day, month, dow),
    and adds seconds/year only if year is explicitly defined.
    """
    minute = str(schedule.get("minute", "*"))
    hour   = str(schedule.get("hour", "*"))
    day    = str(schedule.get("day", "*"))
    month  = str(schedule.get("month", "*"))
    dow    = str(schedule.get("dow", "*"))
    year   = schedule.get("year")

    # base 5-field cron
    cron_str = f"{minute} {hour} {day} {month} {dow}"

    if year and year != "*":
        # enforce croniter’s 7‑field format: add seconds + normalized year
        if isinstance(year, int) or (isinstance(year, str) and year.isdigit()):
            year = f"{year}/1"  # turn single year into a valid range
        cron_str = f"{cron_str} 0 {year}"

    return cron_str

def cron_to_schedule(cron_str: str) -> dict:
    """
    Convert a cron string (5 or 7 fields) into a schedule dict.
    Expected orders:
      - 5-field: minute hour day month dow
      - 7-field: minute hour day month dow sec year
    The 6th field (seconds) is ignored if present.
    """
    parts = cron_str.split()

    if len(parts) == 5:
        minute, hour, day, month, dow = parts
        year = "*"
    elif len(parts) == 7:
        minute, hour, day, month, dow, _, year = parts
        # normalize single-year formats like "2025/1" → "2025"
        if "/1" in year:
            year = year.split("/")[0]
    else:
        raise ValueError("Cron string must have 5 or 7 fields.")

    return {
        "minute": minute,
        "hour": hour,
        "day": day,
        "month": month,
        "dow": dow,
        "year": year,
    }


def calc_early(event_time: datetime, offset_str: str) -> datetime:
    """
    Given an event_time (datetime) and an offset string like '12h' or '1 day',
    return the datetime for the early notification.
    """
    seconds = parse(offset_str)
    if seconds is None:
        raise ValueError(f"Could not parse offset: {offset_str}")
    return normalize_dt(event_time - timedelta(seconds=seconds))


def find_next_fire_time(cron_expr: str, base_time: datetime | None = None, bias_seconds: int = 65) -> datetime:
    """
    Given a cron expression, return the next datetime it would fire.
    Pushes base_time forward by bias_seconds to avoid returning the 'current' tick.
    """
    if base_time is None:
        base_time = datetime.now(user_tz())
    else:
        base_time = normalize_dt(base_time)
    itr = croniter(cron_expr, base_time + timedelta(seconds=bias_seconds), day_or=False)
    return normalize_dt(itr.get_next(datetime))


def handle_set(payload):
    # create the doc
    entry = manager.add_entry("reminders", payload)
    # calculate cron string from schedule
    entry["cron"] = schedule_to_cron(entry["schedule"])
    # calculate early notification if offset exists
    if entry.get("notification_offset"):
        next_fire_time = find_next_fire_time(entry["cron"])
        entry["early_notification"] = calc_early(next_fire_time, entry["notification_offset"])
    if entry.get("snooze_until"):
        entry["snooze_until"] = normalize_dt(entry["snooze_until"])
    if entry.get("skip_until"):
        entry["skip_until"] = normalize_dt(entry["skip_until"])
    manager.edit_entry("reminders", entry.get("id"), entry)
    return entry

def handle_edit(payload, base_time = None):
    entry = manager.get_entry("reminders", payload["id"])
    # Force‑preserve the true ID
    payload["id"] = entry["id"]
    # Merge updates (excluding id to be safe)
    updates = {k: v for k, v in payload.items() if k != "id" and v is not None}
    entry.update(updates)
    entry["cron"] = schedule_to_cron(entry["schedule"])
    if entry.get("notification_offset"):
        next_fire_time = find_next_fire_time(entry["cron"], base_time)
        entry["early_notification"] = calc_early(next_fire_time, entry["notification_offset"])
    if entry.get("snooze_until"):
        entry["snooze_until"] = normalize_dt(entry["snooze_until"])
    if entry.get("skip_until"):
        entry["skip_until"] = normalize_dt(entry["skip_until"])
    manager.edit_entry("reminders", entry["id"], entry)
    return entry

def handle_snooze(payload):
    entry = manager.get_entry("reminders", payload["id"])
    entry["snooze_until"] = normalize_dt(payload["snooze_until"])  # one‑time datetime
    manager.edit_entry("reminders", entry["id"], entry)
    return entry

def handle_skip(payload):
    entry = manager.get_entry("reminders", payload["id"])
    skip_until = normalize_dt(payload["skip_until"])
    entry["skip_until"] = skip_until
    entry["status"] = "enabled"  # skip implies temporary pause, not permanent disable

    cron_expr = entry.get("cron")
    offset_str = entry.get("notification_offset")
    early_notification = None

    if cron_expr and offset_str:
        base_time = skip_until
        while True:
            next_fire = find_next_fire_time(cron_expr, base_time)
            candidate_early = calc_early(next_fire, offset_str)
            if candidate_early > skip_until:
                early_notification = candidate_early
                break
            base_time = next_fire + timedelta(seconds=1)

    if early_notification:
        entry["early_notification"] = early_notification

    manager.edit_entry("reminders", entry["id"], entry)
    return entry

def handle_toggle(payload):
    entry = manager.get_entry("reminders", payload["id"])
    entry["status"] = payload["status"]
    if entry.get("notification_offset"):
        next_fire_time = find_next_fire_time(entry["cron"])
        entry["early_notification"] = calc_early(next_fire_time, entry["notification_offset"])
    manager.edit_entry("reminders", entry["id"], entry)
    return entry

def search_for_timely_reminders(window_minutes=0.5):
    tz = user_tz()
    now_local = datetime.now(tz)
    lower_bound = now_local - timedelta(minutes=window_minutes)
    upper_bound = now_local + timedelta(minutes=window_minutes)
    base_time = now_local - timedelta(minutes=5)

    query = {"type": "reminder_layer", "id": "reminders"}
    reminders_doc = cortex.get_entries(query)
    reminders_doc = serialize_doc(reminders_doc)
    reminders = reminders_doc[0]["entries"] if reminders_doc else []
    triggered = []

    for entry in reminders:
        try:
            cron = entry.get("cron")
            skip_until = entry.get("skip_until")
            ends_on = entry.get("ends_on")
            status = entry.get("status", "enabled")
            early_notification = entry.get("early_notification")
            snooze_until = entry.get("snooze_until")

            if status == "disabled":
                continue

            # Normalize all datetimes
            if skip_until:
                skip_dt = normalize_dt(skip_until)
                if skip_dt > now_local:
                    continue

            if ends_on:
                end_dt = normalize_dt(ends_on)
                if end_dt < now_local:
                    continue

            # Check static one-off triggers
            for label, t in (("early", early_notification), ("snooze", snooze_until)):
                if t:
                    t_dt = normalize_dt(t)
                    if lower_bound <= t_dt <= upper_bound and entry not in triggered:
                        if label == "early":
                            entry[
                                "is_early"] = f"This is a {entry['notification_offset']} early warning on the upcoming reminder."
                        elif label == "snooze":
                            entry["is_snooze"] = "This is the reminder returning from snooze."
                        triggered.append(entry)

            # Cron-based trigger
            if cron:
                itr = croniter(cron, base_time)
                next_trigger = itr.get_next(datetime)
                next_trigger = normalize_dt(next_trigger)
                if lower_bound <= next_trigger <= upper_bound and entry not in triggered:
                    triggered.append(entry)

        except Exception as e:
            print(f"❌ Error processing reminder {entry.get('id')}: {e}")
            continue

    print(f"✅ Found {len(triggered)} reminders ready to fire.")
    return triggered

