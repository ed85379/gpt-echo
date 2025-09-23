import requests
import xml.etree.ElementTree as ET

# Tail thresholds, hex colors, human names, and severity descriptions
COLOR_MAP = [
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
        hex_color, name, severity = COLOR_MAP[-1][1:]
        for i in range(len(COLOR_MAP) - 1):
            tail, hex_c, col_name, sev = COLOR_MAP[i]
            next_tail = COLOR_MAP[i+1][0]
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

status = get_dot_status()
if status:
    print("[Global Consciousness Project - Current Coherence]")
    print(f"Z-Score: {status['z_score']:.3f}")
    print(f"Color: {status['color']} ({status['hex']})")
    print(f"Severity: {status['severity']}")
else:
    print("GCP data unavailable.")