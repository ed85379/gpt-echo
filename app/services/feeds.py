import requests, json
import xml.etree.ElementTree as ET
from app import config
from app.config import muse_config

# Tail thresholds, hex colors, human names, and severity descriptions
GCP_COLOR_MAP = [
    (0.00,   "#FFA8C0", "Pink",      "Extreme deviation (very low coherence)"),
    (0.01,   "#FF1E1E", "Red",       "High deviation"),
    (0.05,   "#FFB82E", "Orange",    "Strong deviation"),
    (0.08,   "#FFD517", "Amber",     "Moderate-high deviation"),
    (0.15,   "#FFFA40", "Yellow",    "Moderate coherence (baseline randomness with some deviation)"),
    (0.23,   "#F9FA00", "Yellow‑Green", "Mild deviation"),
    (0.30,   "#AEFA00", "Chartreuse","Slight deviation"),
    (0.40,   "#64FA64", "Green",     "Baseline randomness / normal coherence"),
    (0.9125, "#64FAAB", "Aqua‑Green","Strong coherence (trending high)"),
    (0.93,   "#ACF2FF", "Light Blue","High coherence"),
    (0.96,   "#0EEEFF", "Cyan",      "Very high coherence"),
    (0.98,   "#24CBFD", "Bright Blue","Extreme coherence"),
    (1.00,   "#5655CA", "Indigo",    "Peak coherence"),
]

def get_dot_status(timeout=0.5):
    try:
        r = requests.get("https://global-mind.org/gcpdot/gcpindex.php", timeout=timeout)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        # get the last <s> entry
        scores = [(int(s.attrib["t"]), float(s.text)) for s in root.findall(".//s")]
        if not scores:
            return None
        timestamp, value = scores[-1]
        norm = max(0.0, min(1.0, value))  # clamp into [0,1]

        # default to the last entry
        hex_color, name, severity = GCP_COLOR_MAP[-1][1:]
        for i in range(len(GCP_COLOR_MAP) - 1):
            tail, hex_c, col_name, sev = GCP_COLOR_MAP[i]
            next_tail = GCP_COLOR_MAP[i + 1][0]
            if tail <= norm <= next_tail:
                hex_color, name, severity = hex_c, col_name, sev
                break

        return {
            "z_score": value,
            "color": name,
            "hex": hex_color,
            "severity": severity
        }

    except Exception:
        return None

def get_openweathermap(timeout=0.5):
    from app.core.time_location_utils import _load_user_location
    loc = _load_user_location()
    api_key = config.OPENWEATHERMAP_API_KEY
    base_url = muse_config.get("OPENWEATHERMAP_API_URL")
    zip_code = loc.zip_code
    country_code = loc.country_code
    temp_units = muse_config.get("MEASUREMENT_UNITS")
    full_url = f"{base_url}?zip={zip_code},{country_code}&units={temp_units}&appid={api_key}"

    def temp_mood_phrase(t: int) -> str:
        if t <= -10:
            return "lethally cold"
        elif t <= 0:
            return "insanely cold"
        elif t <= 10:
            return "brutally cold"
        elif t <= 20:
            return "frigid"
        elif t <= 30:
            return "pretty cold"
        elif t <= 40:
            return "cold but bearable"
        elif t <= 50:
            return "chilly but manageable"
        elif t <= 60:
            return "cool and comfortable"
        elif t <= 70:
            return "mild"
        elif t <= 80:
            return "warm"
        elif t <= 90:
            return "hot"
        elif t <= 100:
            return "sweltering"
        else:
            return "oppressively hot"

    def wind_speed_phrase(speed: float) -> str:
        # speed is already in your chosen units (mph if imperial, m/s if metric)
        # Assuming imperial here; if you ever switch, we can branch on MEASUREMENT_UNITS.
        if speed < 1:
            return "calm"
        elif speed < 4:
            return "light air"
        elif speed < 8:
            return "light breeze"
        elif speed < 13:
            return "gentle breeze"
        elif speed < 19:
            return "moderate breeze"
        elif speed < 25:
            return "fresh breeze"
        elif speed < 32:
            return "strong breeze"
        elif speed < 39:
            return "near gale"
        elif speed < 47:
            return "gale-force winds"
        elif speed < 64:
            return "storm-force winds"
        else:
            return "hurricane-force winds"

    def wind_with_gusts_phrase(speed: float, gust: float | None) -> str:
        base = wind_speed_phrase(speed)

        if gust is None:
            return base

        # If gusts are basically the same as sustained, ignore them.
        diff = gust - speed
        if diff < 5:
            return base

        # 5–14 mph above sustained → occasional gusts
        if diff < 15 and gust < 25:
            return f"{base} with occasional gusts"

        # Anything more intense → strong gusts
        return f"{base} with strong gusts"

    try:
        weather_results = requests.get(full_url, timeout=timeout)
        weather_data = json.loads(weather_results.text)

        main = weather_data["weather"][0]["main"]
        desc = weather_data["weather"][0]["description"]
        temp = round(weather_data["main"]["temp"])
        feels_like = round(weather_data["main"]["feels_like"])

        wind_speed = float(weather_data["wind"].get("speed", 0.0))
        wind_gust = weather_data["wind"].get("gust")
        wind_gust = float(wind_gust) if wind_gust is not None else None

        wind_desc = wind_with_gusts_phrase(wind_speed, wind_gust)

        return {
            "weather_main": main,
            "weather_desc": desc,
            "weather_temp": temp,
            "weather_feels": temp_mood_phrase(feels_like),
            "wind_desc": wind_desc,
        }

    except Exception:
        return None


SPACE_WEATHER_URL = "https://services.swpc.noaa.gov/text/current-space-weather-indices.txt"

def xray_mood(x: float) -> tuple[str, str]:
    """
    Map GOES soft X-ray flux (W/m^2) to a mood word and GOES class.
    Bands are approximate but good enough for 'vibes'.
    """
    if x < 1e-7:
        return "very quiet", "A-class"
    elif x < 1e-6:
        return "calm", "B-class"
    elif x < 1e-5:
        return "active", "C-class"
    elif x < 1e-4:
        return "stormy", "M-class"
    else:
        return "flaring", "X-class"


def geomag_mood(k: float) -> str:
    """
    Map planetary K-like value to a simple geomagnetic mood.
    These thresholds are heuristic but track the usual 'quiet → storm' feel.
    """
    if k < 3:
        return "quiet"
    elif k < 5:
        return "unsettled"
    elif k < 7:
        return "active"
    else:
        return "storm"


def get_space_weather(timeout: float = 0.5) -> dict | None:
    """
    Fetch and parse SWPC 'current-space-weather-indices.txt'.

    Returns a dict like:
    {
        "xray_flux": 4.30e-06,
        "xray_state": "active",
        "xray_class": "C-class",
        "geomag_index_latest": 5.33,
        "geomag_index_avg": 4.39,
        "geomag_state": "active",
    }

    or None if we can't get anything useful.
    """
    try:
        resp = requests.get(SPACE_WEATHER_URL, timeout=timeout)
        resp.raise_for_status()
    except Exception:
        return None

    lines = resp.text.splitlines()
    section: str | None = None

    xray_flux: float | None = None
    planetary_vals: list[float] = []

    for raw in lines:
        line = raw.rstrip("\n")
        if not line:
            continue

        # Section switches
        if line.startswith(":Energetic_Particle_Flux:"):
            section = "energetic"
            continue
        if line.startswith(":Geomagnetic_Values:"):
            section = "geomagnetic"
            continue

        # Any other :Header: we don't care about resets section
        if line.startswith(":") and not line.startswith(
            (":Energetic_Particle_Flux:", ":Geomagnetic_Values:")
        ):
            section = None
            continue

        # Skip comments
        if line.lstrip().startswith("#"):
            continue

        # Energetic: first numeric line after header → contains X-ray flux
        if section == "energetic" and xray_flux is None:
            cols = line.split()
            # We expect at least 5 numeric columns; 5th is X-ray flux
            if len(cols) >= 5:
                try:
                    xray_flux = float(cols[4])
                except ValueError:
                    pass
            continue

        # Geomagnetic: first numeric line after header → contains planetary row
        if section == "geomagnetic" and not planetary_vals:
            cols = line.split()
            # Layout:
            # [0] Boulder running A
            # [1:9] Boulder 3h bins
            # [9:] planetary 3h bins (floats, -1.00 for missing)
            if len(cols) >= 10:
                for c in cols[9:]:
                    if c == "-1.00":
                        continue
                    try:
                        planetary_vals.append(float(c))
                    except ValueError:
                        continue
            continue

    # If we got nothing, bail
    if xray_flux is None and not planetary_vals:
        return None

    # Derive moods
    if xray_flux is not None:
        x_state, x_class = xray_mood(xray_flux)
    else:
        x_state, x_class = "unknown", "unknown"

    if planetary_vals:
        geomag_latest = planetary_vals[-1]
        geomag_avg = sum(planetary_vals) / len(planetary_vals)
        g_state = geomag_mood(geomag_latest)
    else:
        geomag_latest = None
        geomag_avg = None
        g_state = "unknown"

    return {
        "xray_flux": xray_flux,
        "xray_state": x_state,
        "xray_class": x_class,
        "geomag_index_latest": geomag_latest,
        "geomag_index_avg": geomag_avg,
        "geomag_state": g_state,
    }