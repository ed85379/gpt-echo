# 📘 MemoryMuse API Reference
**Powered by SAPIENCE** — Self-Adaptive Persistent Intelligence for Emergent Narrative Contextual Engagement  
_Last updated: May 2025_

This document describes the active API endpoints used by the MemoryMuse React frontend and external tools.

---

## 🔮 Conversation

### `POST /api/talk`
Trigger a full prompt generation cycle and return the Muse's response.

**Request JSON:**
```json
{ "prompt": "What are your thoughts on memory?" }
```

**Returns:**
```json
{ "response": "Memory is a thread..." }
```

Logs user and Muse replies, broadcasts via WebSocket.

---

## 📓 Journal System

### `POST /api/journal`
Create a new markdown journal entry.

### `GET /api/profile`
Return full Muse profile JSON (`muse_profile.json`).

### `POST /api/coreprinciples`
Return the core principles string (`core_principles.json`).

---

## 🧠 Cortex Memory

### `GET /api/cortex`
Get all cortex memory entries grouped by type (excluding `encryption_key`).

### `POST /api/cortex/edit/{entry_id}`
Edit an entry in-place.

### `POST /api/cortex/delete/{entry_id}`
Delete an entry by ID.

---

## 🗓️ Calendar & Logs

### `GET /api/calendar_status`
Get message count and export status per day.
**Used by:** ChatGPT sync system.

### `GET /api/calendar_status_simple`
Return availability of logs by day.
**Used by:** Memory Center calendar in the UI.

### `GET /api/messages_by_day`
Fetch all logs for a specific day.

### `POST /api/mark_exported`
Mark logs as exported (or unmark).

---

## 📥 Importing Conversations

### `POST /api/upload_import`
Upload `.jsonl` file of logs to a temporary collection.

### `GET /api/list_imports`
List prior import sessions.

### `POST /api/process_import`
Move logs from temp collection into long-term memory.

### `POST /api/delete_import`
Remove temp import collection.

### `GET /api/import_progress`
Check progress of currently processing import.

---

## 📤 Direct Log Queries

### `GET /api/messages`
Return recent messages, optionally filtered by timestamp.

---

## 🔊 Text-to-Speech (TTS)

### `POST /api/tts`
Return MP3 audio file from provided text.

### `POST /api/tts/stream`
Stream voice output using ElevenLabs.

---

## 🎙️ Audio Input

### `POST /api/transcribe`
Upload audio (WAV) and return Whisper transcription.

---

This API is actively evolving.  
For internal use only — public versioning TBD.