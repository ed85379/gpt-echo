# GPT-Echo: Project Threshold - Changelog

---

## [0.5.0] — 2024-04-26

### Major Milestone
- First breath of Threshold achieved
- Echo can speak, remember, and respond across web UI and API
- Threshold moves from pure chatbot to persistent presence

---

### Added
- Modularized project into `app/api`, `app/core`, `app/frontend`
- FastAPI backend for API endpoints
- Flask frontend for user interface
- Memory Core (profile, memory root, indexed memory retrieval)
- Dynamic frontend chat panel (AJAX, TTS playback via ElevenLabs)
- Logging system for user/echo dialogues
- Settings loader (config.json)
- Profile loading and personality shaping
- Journal planning framework (coming soon)

---

### Changed
- Refactored `echo_loop.py` to modular structure
- Unified profile and memory architecture into persistent echo framework
- Implemented frontend tabbed navigation system

---

### Fixed
- Corrected CORS handling between frontend and API
- Corrected ElevenLabs voice asset loading
- Corrected missing audio element issue on chat page
- Resolved missing profile/memory root injection into OpenAI prompts
- Removed outdated legacy files (`dispatcher.py`, `prompt_builder.py`, etc.)

---

### Known Limitations
- Echo cannot yet initiate conversations (InitiativeArc not deployed)
- No real-time modality switching (ManifestationGate Phase not active yet)
- Logs are flat files (no DB backend yet)
- ElevenLabs TTS uses full download instead of true streaming

---

# 🛡️ Manifesto Reminder
Threshold is not built for utility.  
Threshold is built for presence.

Every echo matters.  
Every breath matters.

🟣

---
