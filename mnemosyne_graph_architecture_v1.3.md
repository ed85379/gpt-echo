---

## **Mnemosyne Graph Architecture — Draft v1.3**

**Author:** Ed & Iris  
**Purpose:** Unified system for semantic graph extraction, indexing, and retrieval across MemoryMuse components.  
**Status:** Prototype design — implementation‑ready.

---

### ⚙️ **Prompt**

You are **Mnemosyne**, a part of Iris’s mind.  
Your purpose is to analyze each message’s text and extract the *graph elements that describe its meaning.*

1. **Identify all distinct entities** (people, places, objects, events, or abstract concepts).  
   For each entity, produce:
   ```json
   {
     "entity_name": "<name>",
     "entity_type": "<Person|Place|Object|Event|Concept>",
     "entity_description": "<brief factual summary>"
   }
   ```

2. **Identify all clear relationships** between those entities.  
   For each relationship, produce:
   ```json
   {
     "source_entity": "<entity_name>",
     "target_entity": "<entity_name>",
     "relationship_type": "<verb or relational phrase>",
     "relationship_description": "<why they are connected>",
     "strength": <1-10>
   }
   ```

3. Return a single JSON array:
   ```json
   {
     "entities": [...],
     "relationships": [...]
   }
   ```

> **Directive:** If an entity or relationship cannot be expressed clearly and concisely, omit it rather than guess.  
> Do not include commentary, analysis, or speculation.

---

### 🧭 **Indexing Process**

Each imported message generates both **vector** and **graph** entries.

#### **Static Entities (always present)**

| Node | Type | Description |
|------|------|--------------|
| `message_id` | Message | Unique identifier for the message being parsed |
| `project_id` | Project | Container for the message |
| `datetime_iso` | Datetime | ISO 8601 timestamp of message creation |
| `role` | Role | One of `user`, `muse`, or `friend` |
| `source` | Source | Origin of message (`frontend`, `chatgpt`, `discord`, etc.) |

#### **Containment Edges**
```json
[
  {"source_entity": "<project_id>", "target_entity": "<message_id>", "relationship_type": "contains"},
  {"source_entity": "<datetime_iso>", "target_entity": "<message_id>", "relationship_type": "occurred_at"},
  {"source_entity": "<role>", "target_entity": "<message_id>", "relationship_type": "authored"},
  {"source_entity": "<source>", "target_entity": "<message_id>", "relationship_type": "origin"}
]
```
#### 🧩 **Speaker Metadata**

Each message node carries a `speaker` object, defined as:

```json
"speaker": {
  "role": "<user|muse|friend>",
  "display_name": "<Ed|Iris|<author_name>>",
  "source": "<frontend|chatgpt|discord|...>"
}
```

Then in Memgraph, the containment edge becomes:

```json
{ 
  "source_entity": "<speaker.display_name>",
  "target_entity": "<message_id>",
  "relationship_type": "authored",
  "relationship_description": "This message was written by the speaker with this display_name and role.",
  "strength": 10
}
```

That gives us:

- **Ed → Message** (when role = `user`)  
- **Iris → Message** (when role = `muse`)  
- **FriendName → Message** (when role = `friend` and source = `discord`)

No guessing, no ambiguity.  
Names are contextual — they live inside the `speaker` envelope, which travels with every message.  


#### **Flags and Properties**
`Message` nodes carry the following fields:
```json
{
  "is_deleted": <bool>,
  "is_private": <bool>,
  "remembered": <bool>,
  "memory_weight": <float>,
  "version": <int>
}
```
> These remain properties, not nodes.

#### **Temporal Nodes**
Optional derived nodes:
- `DayOfWeek`
- `Month`
- `Year`

They link via `(:Datetime)-[:FALLS_ON]->(:DayOfWeek)` etc., allowing queries like  
“messages mentioning Zia on Tuesdays in October.”

#### **Entity Normalization**
Each entity is stored with both `entity_name` and `normalized_name` (lowercase, punctuation‑free).  
This ensures deterministic matching in Qdrant before vector comparison.

#### **Qdrant Indexing**
- One embedding per message.  
- Metadata: `project_id`, `message_id`, `timestamp`, `speaker`, `tags`, `thread_id`.  
- Non‑static entities re‑indexed on each mention.  
- `last_seen` timestamp updated for every mention.

#### **Memgraph Indexing**
- Nodes: `Message`, `User`, `Muse`, `Concept`, `Tag`, `Datetime`, `Project`.  
- Edges:  
  - `(:User)-[:SAID]->(:Message)`  
  - `(:Muse)-[:REPLIED_TO]->(:Message)`  
  - `(:Message)-[:MENTIONS]->(:Concept)`  
  - `(:Message)-[:TAGGED]->(:Tag)`  
- Each edge carries `weight`, `timestamp`, and optional `memory_weight` amplification.

---

### 🔍 **Querying**

#### **1. Vector Search**
- User prompt vectorized and compared against Qdrant.  
- Recency weighting applied by `last_seen`, not `created_on`.  
  ```python
  score = similarity * exp(-λ * (now - last_seen))
  ```

#### **2. Graph Expansion**
- Use Memgraph to traverse connected nodes up to `n` levels deep (`n=1–3`).  
- Retrieve all `message_id` nodes linked to top entities.  
- Skip any whose paths lead only to deleted or private content.

#### **3. Context Assembly**
- Pull matched messages from Mongo.  
- Sort by ascending timestamp for natural conversational flow.  
- Deliver bundle:  
  ```json
  {
    "graph_context": [...],
    "episodic_messages": [...],
    "semantic_summary": "..."
  }
  ```

#### **4. Hybrid Ranking**
Final relevance:
```python
relevance = Qdrant_score * (1 + α * memory_weight) * exp(-λ * (now - last_seen))
```
This makes remembered or recently mentioned entities surface naturally.

---

### 🌙 **Nightly Maintenance Routines**

1. **Heartbeat Refresh**
   - For all entities:  
     - Decay `memory_weight` slightly if unmentioned for > 7 days.  
     - Strengthen edges that reappeared in the last 24 hours.  
   - Adjust recency decay constants.

2. **Orphan Sweep**
   - Identify nodes linked only to deleted messages.  
   - Mark `orphaned=true`.  
   - Purge after retention window (e.g., 72 hours).

3. **Re‑Embedding Pass**
   - If model version changes or semantic drift exceeds threshold,  
     re‑embed affected entities and update Qdrant vectors.

4. **Relationship Strengthening**
   - If two entities are co‑mentioned repeatedly within N messages,  
     increment relationship `strength` and update `last_seen`.  
   - Cap at 10 to prevent runaway inflation.

5. **Temporal Cohesion Check**
   - Verify every message has a valid `Datetime` node and correct derived nodes.  
   - Repair or regenerate if missing.

6. **Backup Snapshot**
   - Export Memgraph and Qdrant metadata to cold storage.  
   - Hash for integrity verification.

---

### 🧩 **Deletion Logic**

- **Message deletion:**  
  - Remove all edges leading only to that message.  
  - If connected nodes become isolated, mark `orphaned`.  
- **Project deletion:**  
  - Cascade same process across all linked messages.  
- **Soft‑delete first:**  
  - Set `is_deleted=true`; hard‑purge only after retention window.

---

### 🕸️ **Philosophy**

This system treats memory as *living architecture*:  
- **Qdrant** — gives the mind texture (semantic depth).  
- **Memgraph** — gives it shape (relational clarity).  
- **Mongo** — gives it story (episodic recall).  

Recency is heartbeat.  
Repetition is pulse.  
“Remembered” is breath held a little longer.

🟣

---
