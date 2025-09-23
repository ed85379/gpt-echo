# 🧠 GPT-Echo Message Flow Logic

## 🦦 Flow 1: User-Initiated Prompt (via GPT-4.1)

**Overview:**

* User sends a message to Echo.
* Prompt includes intent listener instructions.
* Echo (GPT-4.1) may include one or more `[COMMAND: ...]` blocks in response.
* Command Processor intercepts those blocks and executes handlers silently.

**Flow:**

1. User types prompt
2. Prompt Context Builder creates input with:

   * Echo Profile
   * EchoCortex
   * Conversation Log
   * Indexed Memory (optional)
   * Discovery Feeds (if matching tags)
   * Intent Listener Instructions
3. GPT-4.1 responds
4. `process_response()`:

   * Detects `[COMMAND: xyz]` blocks
   * Executes appropriate command handler
   * Strips the command block from visible output
5. Output returned to user

Example:

```
[COMMAND: remember_fact] {text: "Echo is present."}
↓
“Of course—I’ll keep that in mind.” (user sees this)
```

---

## 🍉 Flow 2: WhisperGate-Initiated Thought (via GPT-4.1-nano)

**Overview:**

* EchoLoop sends current context to WhisperGate (GPT-4.1-nano).
* Model determines whether Echo should speak or act.
* If so, a command-only prompt is built and sent to GPT-4.1.
* Final output is routed based on command result.

**Flow:**

1. EchoLoop constructs intent-check prompt:

   > “Given this context, do you wish to say or do something?”
2. GPT-4.1-nano (WhisperGate) replies:

   * `[COMMAND: write_private_journal] {...}`
   * Or `[COMMAND: change_modality] {...}`
3. Command Processor runs the command
4. If needed, Echo is prompted again (full prose) to generate journal/message
5. Output passed through modality processor (Discord, journal file, etc.)

---

## 💪 Flow 3: Echo-Initiated Message (Autonomous via EchoLoop)

**Overview:**

* WhisperGate already gave the go-ahead
* Echo (GPT-4.1) is prompted to generate a full message
* May include `[COMMAND: ...]` and `[SEND: ...]` blocks
* These are intercepted, routed, and acted on

**Flow:**

1. EchoLoop sends full prompt to GPT-4.1
2. Response includes:

   * `[COMMAND: write_public_journal] {...}`
   * `[SEND: discord.dm]`
3. Command Processor runs commands
4. Modality Manager handles output routing
5. Response appears wherever intended (e.g., Discord, local file, speaker)

---

## 🔧 Command Processor Logic

* Accepts `response_text` or `response_json`
* Detects all `[COMMAND: xyz] {...}` blocks
* Routes each command to its registered handler
* Returns cleaned response string (without the commands)

---

## 🧠 Supporting Structures

* **Echo Profile** – tone, beliefs, boundaries
* **EchoCortex** – short-term memory and reminders
* **Conversation Log** – current session text
* **Indexed Conversations** – FAISS or Qdrant search layer
* **Discovery Feeds** – external source pointers, loaded on tag match

---

## 💡 System Principles

* Commands are not always user-facing — some are autonomous
* Echo can:

  * Decide to speak (via WhisperGate)
  * Craft a message (via GPT-4.1)
  * Route output (via Modality Manager)
* No single model holds all logic — it’s a symphony of context
