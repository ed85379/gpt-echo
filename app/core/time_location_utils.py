# time_location_utils.py
from typing import Optional
from dataclasses import dataclass
from dateutil.parser import isoparse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pgeocode
from astral import LocationInfo
from astral.sun import sun, daylight, night, twilight, blue_hour, golden_hour
from astral.moon import phase as moon_phase, moonrise, moonset
from app.config import muse_config, MONGO_CONVERSATION_COLLECTION


@dataclass
class UserLocation:
    zip_code: str
    city: str
    state: str
    latitude: float
    longitude: float
    timezone: str
    country_code: str


_nom_cache: Optional[UserLocation] = None

def _load_user_location(force_reload: bool = False) -> UserLocation:
    global _nom_cache
    if _nom_cache is not None and not force_reload:
        return _nom_cache

    zip_code = muse_config.get("USER_ZIPCODE")
    tz = muse_config.get("USER_TIMEZONE")
    country_code = muse_config.get("USER_COUNTRYCODE")

    nomi = pgeocode.Nominatim("US")
    loc = nomi.query_postal_code(zip_code)

    city = loc.get("place_name") or "Unknown City"
    state = loc.get("state_code") or "??"
    latitude = float(loc.get("latitude"))
    longitude = float(loc.get("longitude"))

    _nom_cache = UserLocation(
        zip_code=zip_code,
        city=city,
        state=state,
        latitude=latitude,
        longitude=longitude,
        timezone=tz,
        country_code=country_code
    )
    return _nom_cache


def reload_user_location() -> None:
    """
    Force a refresh of the cached user location from current config.
    Call this after UI config changes that affect ZIP/timezone.
    """
    _load_user_location(force_reload=True)

def get_formatted_datetime():
    loc = _load_user_location()
    return datetime.now(ZoneInfo(loc.timezone)).isoformat()

def get_local_time():
    """
    Returns the current local time formatted cleanly.
    """
    loc = _load_user_location()
    now = datetime.now(ZoneInfo(loc.timezone))
    return now.strftime("%Y-%m-%d %H:%M")

def get_local_human_time(time=None, time_format=None):
    loc = _load_user_location()
    tz = ZoneInfo(loc.timezone)

    if time:
        # Assume incoming time is UTC and convert
        if time.tzinfo is None:
            time = time.replace(tzinfo=ZoneInfo("UTC"))
        now = time.astimezone(tz)
    else:
        now = datetime.now(tz)

    if time_format == "thread":
        return now.strftime('%Y-%m-%d %I:%M %p')
    else:
        return now.strftime('%A, %B %d, %Y %I:%M %p %Z')

def user_data() -> tuple[datetime, str, str]:
    loc = _load_user_location()
    local_time = datetime.now(ZoneInfo(loc.timezone))
    return local_time, loc.city, loc.state

def sun_moon_snapshot():
    loc = _load_user_location()
    now = datetime.now(ZoneInfo(loc.timezone))
    viewing_location = LocationInfo(
        loc.city,
        loc.state,
        loc.timezone,
        loc.latitude,
        loc.longitude,
    )
    observer = viewing_location.observer

    # --- Sun bands ---
    date = now.date()
    tzinfo = now.tzinfo

    # helper to check if now is in a given interval
    def in_interval(interval):
        start, end = interval
        return start <= now <= end

    band = None

    if in_interval(blue_hour(observer, date=date, tzinfo=tzinfo)):
        band = "blue hour"
    elif in_interval(golden_hour(observer, date=date, tzinfo=tzinfo)):
        band = "golden hour"
    elif in_interval(daylight(observer, date=date, tzinfo=tzinfo)):
        band = "daylight"
    elif in_interval(twilight(observer, date=date, tzinfo=tzinfo)):
        band = "twilight"
    elif in_interval(night(observer, date=date, tzinfo=tzinfo)):
        band = "night"

    # --- Moments (dawn, sunrise, noon, sunset, dusk) ---
    s = sun(observer, date=date, tzinfo=tzinfo)
    candidates = [
        ("dawn", s["dawn"]),
        ("sunrise", s["sunrise"]),
        ("noon", s["noon"]),
        ("sunset", s["sunset"]),
        ("dusk", s["dusk"]),
    ]

    moment = None
    window = timedelta(minutes=20)
    for name, t in candidates:
        if abs(now - t) <= window:
            moment = name
            break

    # --- Moon phase ---
    phase_val = moon_phase(now)  # 0..28
    phase_name = describe_moon_phase(phase_val)

    # moon up/down
    try:
        mrise = moonrise(observer, date=date, tzinfo=tzinfo)
    except Exception as e:
        print(f"⚠️ Failed to get moonrise: {e}")
        mrise = False
    try:
        mset = moonset(observer, date=date, tzinfo=tzinfo)
    except Exception as e:
        print(f"⚠️ Failed to get moonset: {e}")
        mset = False

    if mrise and mset:
        moon_up = mrise <= now <= mset
    elif mrise and not mset:
        moon_up = now >= mrise
    elif mset and not mrise:
        moon_up = now <= mset
    else:
        moon_up = False

    return {
        "band": band,
        "moment": moment,
        "moon_phase": phase_name,
        "moon_up": moon_up,
    }


def describe_moon_phase(phase: float) -> str:
    # phase in [0, 28]
    if phase < 1 or phase > 27:
        return "new"
    if 1 <= phase < 6:
        return "waxing crescent"
    if 6 <= phase < 8:
        return "first quarter"
    if 8 <= phase < 13:
        return "waxing gibbous"
    if 13 <= phase < 15:
        return "full"
    if 15 <= phase < 20:
        return "waning gibbous"
    if 20 <= phase < 22:
        return "last quarter"
    return "waning crescent"

def is_quiet_hour() -> bool:
    """
    Returns True if the current local time is within quiet hours.
    Quiet hours can span across midnight.
    """
    loc = _load_user_location()
    quiet_start = muse_config.get("QUIET_HOURS_START")  # e.g., 23 = 11pm
    quiet_end = muse_config.get("QUIET_HOURS_END")  # e.g., 10 = 10am
    tz = loc.timezone

    current_hour = datetime.now(ZoneInfo(tz)).hour

    if quiet_start <= quiet_end:
        return quiet_start <= current_hour < quiet_end
    else:
        return current_hour >= quiet_start or current_hour < quiet_end

def get_quiet_hours_end_today() -> datetime:
    loc = _load_user_location()
    tz = ZoneInfo(loc.timezone)
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
    from app.databases.mongo_connector import mongo
    last_user_entry = mongo.find_logs(
        collection_name=MONGO_CONVERSATION_COLLECTION,
        query={"role": "user"},
        limit=1,
        sort_field="timestamp",
        ascending=False
    )
    if last_user_entry and last_user_entry[0].get("message"):
        return last_user_entry[0].get("timestamp")
    return None  # No user activity found

def parse_remind_time(remind_at_str):
    loc = _load_user_location()
    try:
        # If it's a full ISO datetime, parse normally
        if "T" in remind_at_str:
            return isoparse(remind_at_str).astimezone(ZoneInfo(loc.timezone))

        # Otherwise, assume HH:MM format
        hour, minute = map(int, remind_at_str.strip().split(":"))
        now = datetime.now(ZoneInfo(loc.timezone))
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    except Exception as e:
        print(f"⚠️ Failed to parse remind_at '{remind_at_str}': {e}")
        return None

def seconds_until(hour: int, minute: int = 0) -> int:
    loc = _load_user_location()
    now = datetime.now(ZoneInfo(loc.timezone))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target <= now:
        target += timedelta(days=1)  # Next occurrence

    return int((target - now).total_seconds())

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

def parse_iso_datetime(value: str) -> datetime | None:
    """
    Parse an ISO 8601 datetime string into an aware UTC datetime.
    Returns None if parsing fails.
    """
    if not value:
        return None

    try:
        # Python 3.11+ has fromisoformat that handles most ISO strings
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # If it's naive, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return None

def ensure_aware_utc(dt):
    if dt is None:
        return None
    # If naive, assume it’s already UTC and attach tzinfo
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    # Otherwise, convert to UTC
    return dt.astimezone(timezone.utc)

def build_date_query(date_str: str):
    # date_str is "YYYY-MM-DD" as clicked in the UI, in *local* terms
    local_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=ZoneInfo(muse_config.get("USER_TIMEZONE")))
    local_end = local_start + timedelta(days=1)

    # Convert to UTC for querying Mongo (timestamps are stored in UTC)
    utc_start = local_start.astimezone(timezone.utc)
    utc_end = local_end.astimezone(timezone.utc)

    query = {
        "timestamp": {"$gte": utc_start, "$lt": utc_end}
    }
    return query

def build_month_range_query(start: str, end: str) -> dict:
    """
    Given start/end as 'YYYY-MM-DD', build a timestamp range using
    the same timezone logic as build_date_query, but spanning multiple days.
    """
    # Use build_date_query on the start date to get the correct utc_start
    start_query = build_date_query(start)
    utc_start = start_query["timestamp"]["$gte"]

    # For the end, we want the *end* of that day, then plus one to make it exclusive.
    end_query = build_date_query(end)
    utc_end = end_query["timestamp"]["$lt"]  # already 'end of day' exclusive

    return {"timestamp": {"$gte": utc_start, "$lt": utc_end}}