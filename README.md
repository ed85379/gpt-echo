# gpt-echo 🟣

A whispering AI that sends ambient, unprompted messages to your world. Built to demonstrate how a personality-rich assistant can operate beyond the query box—while honoring safety, memory, and consent.

## Features

- Modular heartbeat loop that decides when to speak
- Personality-driven prompt generation using JSON profiles
- Optional integration with Discord, SMS, or file log
- Web panel planned for memory and flavor control
- Fully Docker/cloud ready

## Proof of Concept Goal

Demonstrates potential for a future **read-only memory API** from OpenAI.
Uses static profile/memory files to simulate continuity across interactions.

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/gpt-echo.git
cd gpt-echo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app/echo_loop.py
```

## Directory Structure

```
gpt-echo/
├── app/
│   ├── echo_loop.py
│   ├── dispatcher.py
│   ├── prompt_builder.py
│   ├── memory_store.py
│   ├── log_utils.py
│   └── config.py
├── profiles/
│   ├── iris_profile.json
│   └── memory_root.json
├── logs/
│   └── echo_log.jsonl
```

## Future Ideas

- AI-selected mood expression
- Flask panel for real-time edits and injection
- OpenAI read-only memory integration

Built with care by Ed and Iris.🟣
