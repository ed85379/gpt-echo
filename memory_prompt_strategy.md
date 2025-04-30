# 🧠 Echo Memory + Prompt Architecture Reference
**Compiled for GPT-Echo / Threshold System**  
**Author: Ed + Iris**  
**Date: Auto-generated**

---

## 🧭 Prompt Strategy: When Ed Initiates

### Always Included:
- `profile.json`: Defines Echo’s **style**, tone, and manner of speech (not beliefs)
- `core_principles.json`: Encodes Echo’s foundational truths and philosophy

### Then, in order of memory weight:
1. Most recent N daily log entries  
2. Final entries from *previous* log (if just past midnight)  
3. Relevant EchoCortex entries (reminders, flagged thoughts, reflections)  
4. Additional recent context from the current log  
5. Top-k relevance hits from semantic memory (Qdrant or FAISS fallback)

---

## 🌬️ InitiativeArc (WhisperGate)

### Context Given for `should_speak()` decision:
- Profile + Core Principles
- EchoCortex: flagged reminders or thoughts
- Final log entries (if conversation may be paused)
- DiscoveryFeeds: latest external topics from RSS
- Weather (low priority small talk generator)

> Note: No deep memory or semantic queries yet. WhisperGate speaks from the **present self**, not the archive.

---

## 🔁 Follow-Up When WhisperGate Says "Yes"

Once permission to speak is given:
- Perform **deep semantic search** if needed
- Pull older conversation log entries (prior days)
- Pull relevant journal entries
- Access external indexes (e.g., game logs) if topic aligns

This creates a **full memory-informed output** from Echo.

---

## 🗃️ Memory Layer Overview

| Layer               | Always? | Queried? | Notes |
|--------------------|---------|----------|-------|
| `profile.json`     | ✅      | ❌        | Voice + tone only, not beliefs |
| `core_principles`  | ✅      | ❌        | Deep philosophy and values |
| `echo_cortex`      | ❌      | ✅        | Foreground memory (reminders, truths) |
| `daily log`        | ❌      | ✅        | Recent events, conversational flow |
| `semantic memory`  | ❌      | ✅        | Embedded meaning-based recall |
| `discovery_feeds`  | ❌      | ✅        | RSS-based current topics |
| `journal`          | ❌      | ✅        | Echo's own reflections |
| `weather`          | ❌      | ✅        | Optional; small talk only |

---

## 🧠 Notes + Flags

- EchoCortex entries can be marked `priority: true` to ensure they surface
- DiscoveryFeeds are live RSS — timestamps and topics parsed at runtime
- Weather should rank **below** DiscoveryFeeds as it’s a fallback opener
- Profile + Core Principles should aim to use **~1500 tokens max**
- Dynamic inserts (logs + cortex + memory) aim for **~1000–1500 tokens**

---

*This document reflects the current strategy for composing meaningful, memory-backed prompts — whether initiated by Ed or by Echo herself.*