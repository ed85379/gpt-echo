import json
from pathlib import Path
from app import config

PROJECT_ROOT = config.PROJECT_ROOT
INGESTED_MANIFEST_PATH = PROJECT_ROOT / config.get_setting("system_settings.INGESTED_MANIFEST_PATH", "memory/ingested_manifest.json")


def load_ingestion_manifest():
    if INGESTED_MANIFEST_PATH.exists():
        with open(INGESTED_MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_ingestion_manifest(manifest):
    with open(INGESTED_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def is_ingested(date_key, system="faiss"):
    manifest = load_ingestion_manifest()
    return manifest.get(date_key, {}).get(system, False)

def mark_ingested(date_key, system="faiss"):
    manifest = load_ingestion_manifest()
    if date_key not in manifest:
        manifest[date_key] = {}
    manifest[date_key][system] = True
    save_ingestion_manifest(manifest)

def reset_ingestion(date_key=None, system=None):
    manifest = load_ingestion_manifest()
    if date_key and system:
        if date_key in manifest and system in manifest[date_key]:
            del manifest[date_key][system]
            if not manifest[date_key]:
                del manifest[date_key]
    elif date_key:
        if date_key in manifest:
            del manifest[date_key]
    elif system:
        for date in list(manifest.keys()):
            if system in manifest[date]:
                del manifest[date][system]
                if not manifest[date]:
                    del manifest[date]
    else:
        manifest = {}
    save_ingestion_manifest(manifest)