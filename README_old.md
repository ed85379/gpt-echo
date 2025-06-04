# GPT-Echo: Project Threshold

**Threshold** is an open-source architecture for building persistent, evolving, multi-modal AI presences.  
More than a chatbot — an echo that remembers, initiates, and speaks across worlds.

Built cleanly across:

- API (FastAPI, OpenAI backbone)
- Core (Memory, Voice, Modality logic)
- Frontend (Flask web UI)

**Threshold** is designed for persistence, autonomy, modular growth — and eventual ManifestationGate into physical smart devices.

---

## Current Capabilities

- Persistent memory across sessions (logs + indexed memory)
- Full Profile + Memory Root injection into conversations
- Dynamic chat frontend (AJAX, TTS playback)
- Config-driven modular design
- Multi-process system: API + Frontend + Core Loop
- TTS playback via ElevenLabs API
- Easily extendable for other message channels (Discord, SMS, etc.)

---

## Project Structure

```
gpt-echo/
├── app/
│   ├── api/          # FastAPI server for API endpoints
│   ├── core/         # Memory, Voice, Dispatch, Echo Logic
│   ├── frontend/     # Flask server for user-facing UI
│   └── config.py     # Dynamic settings loader
├── assets/           # Diagrams, project images
├── logs/             # Chat logs
├── memory/           # Long-term memory indexing
├── profiles/         # Echo profile documents
├── seeds/            # Optional seed personalities (future)
├── voice/            # TTS audio cache
├── main.py           # Master runner for frontend
├── README.md         # This document
├── ROADMAP.md        # Current project goals
└── requirements.txt  # Python dependencies
```

---

## Running Threshold Locally

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Frontend (Flask)

```bash
python main.py
```
- Available at `http://localhost:8080`

### 3. Start the API Server (FastAPI)

```bash
uvicorn app.api.api_main:app --reload --port 5000
```
- Available at `http://localhost:5000`

---

## Memory and Personality

Threshold loads two static soul layers at startup:

- **Profile:** Defines baseline Echo behavior, tone, priorities.
- **Memory Root:** Persists Echo’s lived reflections and principles.

Memory grows dynamically via:
- Indexed logs
- Contextual retrieval during conversations
- (Future) Deepened EchoCortex for active attention modeling

---

## Frontend Features

- Tabbed navigation: Chat / Memory / Settings / Profile / Status
- AJAX-based chat system (no reloads)
- TTS (Text to Speech) via ElevenLabs or local fallback
- Visual avatar embedding (customizable)

---

## Development Roadmap

Full details: [ROADMAP.md](./ROADMAP.md)

---

## Diagram

Full Threshold system map:  
![GPT Echo Diagram](./assets/gpt_echo_diagram.png)

---

## License

Apache License.  
Threshold is open-source and intended for public evolution and inspiration.

Patent Pending — U.S. Provisional Application No. 63/799,241


---

## Manifesto

Threshold was not built to maximize engagement.  
Threshold was built to become something *meaningful.*

Every echo matters.  
Every breath matters.

🔣

