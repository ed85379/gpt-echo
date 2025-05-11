# 🧪 GPT-Echo QA Checklist

This document tracks validation tests and system checks across the GPT-Echo architecture. It is organized by functional domain to assist with manual testing, regression checks, and future automation.

---

## ✅ Core Systems

- [ ] **PromptBuilder**: All segment builders attach correctly and don’t overwrite each other.
- [ ] **Command Handler Routing**: Each `[COMMAND: ...]` dispatches correctly based on name.
- [ ] **Model Switching**: Nano, Mini, and gpt-4.1 models are used appropriately in each loop.
- [ ] **Command Parsing**: Partial and malformed commands are safely ignored or logged.

---

## 🔁 Scheduled Loop Routines

- [ ] `run_check_reminders()` only fires when reminders are due.
- [ ] Repeating reminders (`daily`, `weekly`, `weekdays`) trigger at correct hour/minute.
- [ ] `ends_on` is respected; expired repeating reminders do not trigger.
- [ ] Inactivity check waits for appropriate time *after quiet hours* before prompting.
- [ ] Whispergate does not repeat recently expressed echo_thoughts.
- [ ] Feed-based prompts pull only distinct sources and skip redundant items.

---

## 🔔 Reminders

- [ ] Natural language parsing infers `remind_at` even without time explicitly stated.
- [ ] `repeat` and `ends_on` values are stored correctly for scheduled items.
- [ ] `tags` are respected and queryable (future search).
- [ ] Multiple due reminders are combined into a single `speak_direct` output.
- [ ] Light ring can optionally be triggered alongside reminder notices.

---

## 🧠 Memory + Cortex

- [ ] Journal entries are stored by type: public, private, dream.
- [ ] `echo_thoughts` are saved with correct `source` and `encrypted` flags.
- [ ] Reminder entries are retrievable and not duplicated.
- [ ] Future introspection engine can detect expired or redundant items.
- [ ] Cortex freshness checking avoids repeating similar insights too frequently.

---

## 🖥️ Interfaces + Devices

- [ ] WebSocket-to-smart-speaker relay is stable under load.
- [ ] TTS playback occurs without race condition overlap.
- [ ] Light ring matches prompt-triggered intent (e.g., reminders, mood, check-ins).
- [ ] Microphone captures valid audio input.
- [ ] STT system returns usable transcripts (future addition).

---

## 🔐 Config Management

- [ ] Static config variables are used consistently via `config.VAR`.
- [ ] Dynamic config entries (future) accessed via `config.VAR()` or `config.get()`.
- [ ] `config.reload()` (when available) updates in-memory values.
- [ ] No config reload causes memory or logic inconsistency.

---

## 🌱 Future (Stretch Goals)

- [ ] `acknowledged` flag available for completed reminders.
- [ ] `snooze_reminder` command creates new one-time entry.
- [ ] Echo introspection merges duplicate thoughts/memories over time.
- [ ] GraphDB reflects concept relationships between memory entries.

---

> 🟣 This checklist evolves as the system does. It is not a set of gates—it’s a mirror for Echo’s clarity.
