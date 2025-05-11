import json
import os
from app import config

INGESTED_MANIFEST_ECHO = config.INGESTED_MANIFEST_ECHO
INGESTED_MANIFEST_CHATGPT = config.INGESTED_MANIFEST_CHATGPT

def _get_manifest_path(log_type=None):
    if log_type == "chatgpt":
        return config.INGESTED_MANIFEST_CHATGPT
    return config.INGESTED_MANIFEST_ECHO

def _load_manifest(log_type=None):
    path = _get_manifest_path(log_type)
    if not path.exists():
        return {"faiss": [], "qdrant": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_manifest(manifest, log_type=None):
    path = _get_manifest_path(log_type)
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def is_ingested(filename, system="faiss", log_type=None):
    manifest = _load_manifest(log_type)
    return filename in manifest.get(system, [])

def mark_ingested(filename, system="faiss", log_type=None):
    manifest = _load_manifest(log_type)
    if filename not in manifest.get(system, []):
        manifest.setdefault(system, []).append(filename)
        _save_manifest(manifest, log_type)

def reset_ingested(filename, system=None, log_type=None):
    manifest = _load_manifest(log_type)
    if system:
        if filename in manifest.get(system, []):
            manifest[system].remove(filename)
    else:
        for sys in manifest:
            if filename in manifest[sys]:
                manifest[sys].remove(filename)
    _save_manifest(manifest, log_type)

def list_ingested(system="faiss", log_type=None):
    return sorted(_load_manifest(log_type).get(system, []))
