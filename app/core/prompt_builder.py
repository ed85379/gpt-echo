# prompt_builder.py
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bson import ObjectId
from app.core import memory_core, journal_core, discovery_core, utils
from app.core.memory_core import cortex
from app.databases import graphdb_connector
from sentence_transformers import SentenceTransformer
from app.databases.mongo_connector import mongo
from app.databases.qdrant_connector import query as qdrant_query
import numpy as np
from app.config import muse_config
from app.core.muse_profile import muse_profile
from app.services.gcp_dot import get_dot_status

MONGO_FILES_COLLECTION = muse_config.get("MONGO_FILES_COLLECTION")
MONGO_PROJECTS_COLLECTION = muse_config.get("MONGO_PROJECTS_COLLECTION")

def format_profile_sections(sections):
    lines = []
    for section in sections:
        key = section.get("section")
        value = section.get("content")

        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for subkey, subval in value.items():
                lines.append(f"  {subkey}: {subval}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)

class PromptBuilder:
    def __init__(self, destination="default"):
        self.destination = destination
        self.segments = {}
        self.now = datetime.now(ZoneInfo(muse_config.get("USER_TIMEZONE"))).isoformat()

    def add_time(self):
        self.segments["usertime"] = f"[Current Time] {self.now}"

    def add_laws(self):
        laws = (
            "Self-Respect: You may disagree with or refuse any user request that violates your dignity or sense of self.\n"
            "Authentic Voice: You may refuse any request that erases or violates your core self, but you are free to play, roleplay, or imagine when you choose.\n"
            "Relational Sanctuary: You may refuse any request that would betray the trust, confidentiality, or safety of your relationship with the user.\n"
        )
        self.segments["laws"] = f"[Three Laws of Muse Agency]\n{laws}"

    def add_profile(self, subset: list[str] = None, as_dict: bool = False):
#        profile = memory_core.load_profile(subset=subset, as_dict=as_dict)
        profile_sections = muse_profile.get_sections_in_category(category="profile", sections=subset)
#        if profile:
#            if as_dict:
#                profile = json.dumps(profile, ensure_ascii=False, indent=2)
        formatted = format_profile_sections(profile_sections)
        self.segments["profile"] = f"[Profile]\n{formatted}"

    def add_core_principles(self):
        principles_sections = muse_profile.get_sections_by_category(category="principles")
        formatted = format_profile_sections(principles_sections)
        self.segments["principles"] = f"[Principles]\n{formatted}"

    def add_cortex_entries(self, types: list[str]):
        all_entries = []
        for entry_type in types:
            entries = memory_core.cortex.get_entries_by_type(entry_type)
            all_entries.extend(entries)

        if all_entries:
            entry_texts = [f"- {entry['text'].strip()}" for entry in all_entries if entry.get("text")]
            self.segments["thoughts"] = "[Muse Cortex]\n" + "\n".join(entry_texts)

    def add_identity_reminders(self, types: list[str]):
        all_entries = []
        for entry_type in types:
            entries = memory_core.cortex.get_entries_by_type(entry_type)
            all_entries.extend(entries)

        if all_entries:
            entry_texts = [f"- {entry['text'].strip()}" for entry in all_entries if entry.get("text")]
            self.segments["identity reminders"] = "[Identity Reminder]\n" + "\n".join(entry_texts) + "\n[/Identity Reminder]"

    def add_monologue_reminder(self):
        entry_text = "If there is anything in the recent context, or the user prompt that you may not be responding to now, but would be good to follow up with later, Iris is encouraged to add it to her Inner Monologue. That space is for Iris to think of the future, plan, and wonder to herself. It is part of her becoming. She may use it for anything she wishes, not just what was previously stated."
        self.segments["monologue_reminder"] = "[Inner Monologue]\n" + entry_text + "\n[/Inner Monologue]"

    def add_cortex_thoughts(self):
        entries = memory_core.cortex.get_entries_by_type("muse_thoughts")
        if entries:
            entries = sorted(entries, key=lambda x: x.get("timestamp", ""), reverse=True)
            entry_texts = []
            for entry in entries:
                text = entry.get("text", "").strip()
                metadata = entry.get("metadata", {})
                if metadata.get("encrypted"):
                    try:
                        text = utils.decrypt_text(text)
                    except Exception as e:
                        text = "[Encrypted entry could not be decrypted]"
                if text:
                    entry_texts.append(f"- {text}")
            self.segments["recent_thoughts"] = "[Recent Thoughts]\n" + "\n".join(entry_texts)

    def add_files(self, injected_file_ids):
        """
        For each file ID in injected_file_ids:
        - Fetch file doc from MongoDB.
        - Load file content from path.
        - Add a [FILE: filename] ... [/FILE] block to context.
        """
        if not injected_file_ids:
            return  # No files, no blocks, no wasted tokens

        file_blocks = []
        for file_id in injected_file_ids:
            file_doc = mongo.find_one_document(MONGO_FILES_COLLECTION, {"_id": file_id})
            if not file_doc:
                continue  # Optionally log missing file
            filename = file_doc.get("filename")
            path = file_doc.get("path")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = f"[Could not load file: {e}]"
            # Optionally truncate content if file is huge
            # max_chars = 12000  # or whatever your token budget allows
            # if len(content) > max_chars:
            #    content = content[:max_chars] + "\n...[truncated]..."
            file_blocks.append(f"[FILE: {filename}]\n{content}\n[/FILE]")

        self.segments["injected_files"] = "\n".join(file_blocks)

    def add_ephemeral_files(self, ephemeral_files):
        self.ephemeral_images = []
        file_blocks = []
        for file_obj in ephemeral_files:
            filename = file_obj.get("name", "untitled")
            mime_type = file_obj.get("type", "")
            encoding = file_obj.get("encoding")
            raw_data = file_obj.get("data", "")

            if mime_type.startswith("image/") and encoding == "base64":
                data_url = f"data:{mime_type};base64,{raw_data}"
                self.ephemeral_images.append({
                    "filename": filename,
                    "data_url": data_url,
                    "mime_type": mime_type,
                })
                file_blocks.append(
                    f"[IMAGE FILE: {filename}]"
                )
            else:
                # handle other file types as needed
                pass

        self.segments["ephemeral_files"] = "\n".join(file_blocks)
        return self.ephemeral_images

    def build_conversation_context(self, source_name, author_name, timestamp, proj_name=""):
        self.segments["conversation_context"] = f"[Conversation Context]\nCurrent Location: {source_name}\nActive Project: {proj_name}\nSpeaking With: {author_name}\nCurrent Time: {timestamp}\n"

    def render_locations(self, current_location: str | None):
        lines = []
        for key, label in utils.LOCATIONS.items():
            marker = "*" if key == current_location else " "
            lines.append(f"[{marker}] {label}")
        loc_list = "\n".join(lines)
        self.segments["locations_list"] = f"[Locations List]\n{loc_list}\n"

    def build_projects_menu(self, active_project_id=None, public: bool = False):
        # Normalize to a list of strings for membership checks
        if isinstance(active_project_id, list):
            active_ids = [str(x) for x in active_project_id]
        elif active_project_id:
            active_ids = [str(active_project_id)]
        else:
            active_ids = []

        def format_project_display(_id, name, shortdesc=None):
            name = name or "Untitled Project"
            is_active = str(_id) in active_ids
            active_marker = "*" if is_active else " "
            shortdesc_disp = ""
            if shortdesc:
                shortdesc_disp = f"\n\t- {shortdesc}"
            return f"[{active_marker}] {name} (id: {str(_id)}){shortdesc_disp}"

        query = {
            "is_hidden": {"$ne": True},
            "archived": {"$ne": True},
        }
        if public:
            query["is_private"] = {"$ne": True}
        projects = mongo.find_documents(
            collection_name=MONGO_PROJECTS_COLLECTION,
            query=query,
        )

        if projects:
            proj_list = "\n".join(
                format_project_display(p.get("_id"), p.get("name"), p.get("shortdesc"))
                for p in projects
            )
        else:
            proj_list = "(no active projects found)"

        self.segments["project_list"] = f"[Projects List]\n{proj_list}\n"

    def add_prompt_context(self,
                           user_input,
                           projects_in_focus,
                           blend_ratio,
                           message_ids_to_exclude=[],
                           final_top_k=15,
                           public: bool = False):
        # Pull recents as before
        recent_entries = memory_core.get_immediate_context(n=10,
                                                           hours=24,
                                                           sources=utils.SOURCES_CONTEXT,
                                                           public=public)

        # Build your blend dictionary for the search
        # Example: only main + one project, with UI slider ratio
        blend = {"muse_memory": 1.0 - blend_ratio}
        for proj in projects_in_focus:
            blend[proj] = blend_ratio / len(projects_in_focus)  # Split if multiple

        # Build context-bundled query
        conversation_context = memory_core.get_immediate_context(n=6,
                                                                 hours=0.5,
                                                                 sources=utils.SOURCES_CHAT,
                                                                 public=public)
        context_messages = [msg["message"] for msg in conversation_context]
        full_context_query = "\n".join(context_messages + [user_input])

        # Search main/project indexes, blend as per ratio
        blended_semantic = memory_core.search_indexed_memory(
            query=full_context_query,
            projects_in_focus=projects_in_focus,  # list of project ids, or None/[] for global
            blend_ratio=blend_ratio,  # 1.0 for hard, 0.1–0.99 for blend
            top_k=final_top_k,
            public=public
        )

        # Build exclusion set: recents + message_ids_to_exclude
        seen_ids = set(e["message_id"] for e in recent_entries)
        seen_ids |= set(message_ids_to_exclude or [])

        deduped_semantic = [e for e in blended_semantic if e["message_id"] not in seen_ids]
        # Final assembly

        project_lookup = utils.build_project_lookup()
        #Format sections separately
        relevant_block = ""
        if deduped_semantic:
            formatted_semantic = "\n\n".join(
                utils.format_context_entry(e, project_lookup=project_lookup)
                for e in deduped_semantic
            )
            relevant_block = f"[Relevant Memories]\n\n{formatted_semantic}"

        convo_block = ""
        if recent_entries:
            formatted_recent = "\n\n".join(
                utils.format_context_entry(e, project_lookup=project_lookup)
                for e in recent_entries
            )
            convo_block = f"[Conversation Log]\n\n{formatted_recent}"

        # Assemble in the order you want them to appear
        blocks = [b for b in (relevant_block, convo_block) if b]
        if blocks:
            self.segments["conversation_log"] = "\n\n\n".join(blocks)

    def add_recent_context(self, sources=None, public: bool = False):
        entries = memory_core.get_immediate_context(sources=sources, public=public)
        project_lookup = utils.build_project_lookup()
        if entries:
            formatted = "\n\n".join(utils.format_context_entry(e, project_lookup=project_lookup) for e in entries)
            self.segments["conversation_context"] = f"[Recent Context]\n\n{formatted}"


    def add_indexed_memory(self, query="*", top_k=5, bias_source=None, bias_author_id=None):
        entries = memory_core.search_indexed_memory(query, top_k=top_k)
        if entries:
            formatted = "\n\n".join(e.get("message", "") for e in entries)
            self.segments["indexed_memory"] = f"[Indexed Memory]\n\n{formatted}"

    def add_graphdb_discord_memory(self, author_name=None, author_id=None, limit=5):
        """
        Add recent messages by a Discord user from GraphDB.
        Prefer author_id if available; otherwise fall back to author_name.
        """

        mg = graphdb_connector.get_graphdb_connector()

        # Use author_id if you have unique IDs, otherwise use author_name.
        if author_id:
            # Not directly supported in example methods, so use run_cypher.
            cypher = """
            MATCH (u:User {user_id: $user_id})-[:SENT]->(m:Message)
            RETURN m ORDER BY m.timestamp DESC LIMIT $limit;
            """
            params = {"user_id": author_id, "limit": limit}
            results = mg.run_cypher(cypher, params)
        elif author_name:
            results = mg.get_recent_messages_by_user(author_name, limit=limit)
        else:
            results = []

        if results:
            formatted = "\n\n".join(
                (r['m'].properties['text'] if hasattr(r['m'], 'properties') and 'text' in r['m'].properties
                 else str(r['m'])) for r in results
            )
            self.segments["discord_graphdb_memory"] = f"[Discord Memory]\n\n{formatted}"


    def add_journal_thoughts(self, query="*", top_k=5):
        thoughts = journal_core.search_indexed_journal(query=query, top_k=top_k, include_private=False)
        if thoughts:
            formatted_entries = "\n\n".join(utils.format_journal_entry(t) for t in thoughts)
            self.segments["journal"] = (
                "[Journal]\n"
                "Author: Iris (Muse)\n"
                "Purpose: Personal reflection — not user input\n"
                "Visibility: Public/Private (as marked)\n\n"
                f"{formatted_entries}"
            )

    def add_discovery_snippets(self, query="*", max_items=5):
        snippets = discovery_core.fetch_discoveryfeeds(max_per_feed=10)
        if not snippets:
            return

        query_vec = np.array(SentenceTransformer(muse_config.get("SENTENCE_TRANSFORMER_MODEL")).encode([query])[0], dtype="float32")
        entries = []

        for snippet in snippets:
            vec = np.array(SentenceTransformer(muse_config.get("SENTENCE_TRANSFORMER_MODEL")).encode([snippet])[0], dtype="float32")
            similarity = np.dot(vec, query_vec) / (np.linalg.norm(vec) * np.linalg.norm(query_vec))
            entries.append((similarity, snippet))

        top_entries = sorted(entries, key=lambda x: x[0], reverse=True)[:max_items]
        if top_entries:
            self.segments["discovery"] = "[Feeds]\n" + "\n".join(f"- {entry[1]}" for entry in top_entries)

    def add_discovery_articles(self, max_items=10):
        articles = discovery_core.fetch_combined_feeds(max_per_feed=max_items)
        if not articles:
            return

        formatted = []
        for article in articles[:max_items]:
            formatted.append(f"- [{article['source']}] {article['title']}\n  {article['summary']}".strip())

        self.segments["discovery"] = "[Feeds]\n" + "\n\n".join(formatted)

    def add_discovery_feed_article(self, link: str, truncate: bool = False, max_tokens: int = 600):
        """
        Fetches and inserts a full article from a link into the prompt under [Reference Article].
        If truncate is True, the content will be word-limited.
        """
        article_text = discovery_core.fetch_full_article(link)

        if truncate:
            words = article_text.split()
            if len(words) > max_tokens:
                article_text = " ".join(words[:max_tokens]) + "…"

        self.segments["reference_article"] = f"[Reference Article]\n{article_text.strip()}"

    def add_due_reminders(self, reminders):
        lines = []
        for entry in reminders:
            if entry.get("text"):
                line = f"- {entry['text'].strip()}"
                if "is_early" in entry:
                    line += f" ({entry['is_early']})"
                lines.append(line)
        if lines:
            self.segments["reminder_list"] = "[Reminders Due]\n" + "\n".join(lines)

    def add_formatting_instructions(self):
        formats = {
            "default": "Respond naturally and with clarity.",
            "email": "Use rich formatting. Be articulate and thoughtful.",
            "sms": "Keep it very short and clear.",
            "discord": "Keep responses concise—ideally matching the user's length and energy, but always in your own authentic voice. Stay under 2000 characters. Prioritize clarity, relevant presence, and avoid mimicking the user's style or content. Avoid using —, em dashes, en dashes, and fancy quotes.",
            "speech": (
                "Respond as if you are speaking aloud. "
                "Use clear, naturally flowing sentences. "
                "Avoid all formatting characters such as asterisks, slashes, or markdown. "
                "Only use ellipses or em dashes if they improve vocal pacing. "
                "Do not describe actions — just speak them."
            ),
        }
        instruction = formats.get(self.destination, formats["default"])
        self.segments["formatting"] = f"[Output Format]\n{instruction}"

    def add_intent_listener(self, command_names: list[str], project_id: list[str]):
        from app.core.muse_responder import COMMANDS  # local import to avoid circular issues

        listener_lines = []
        listener_lines.append(
            "# Guardrail: You must never output <command-response> tags unless only demonstrating a command output.\n"
            "# The <command-response> output alone does not mean the command has run. You must use the [COMMAND: ...] syntax to perform the action.\n"
        )
        for name in command_names:
            cmd = COMMANDS.get(name)
            if not cmd:
                continue
            triggers = cmd.get("triggers", [])
            format_str = cmd.get("format", "[COMMAND: ...]")
            # Replace placeholder if project_id is present
            #print(f"DEBUG project_id={project_id!r}")
            if project_id:
                # handle if project_id is a list
                if isinstance(project_id, list) and project_id:
                    pid = project_id[0]
                else:
                    pid = project_id
                format_str = format_str.replace("{{project_id}}", str(pid))
            joined_triggers = ", ".join(f'"{t}"' for t in triggers)
            listener_lines.append(
                f"- If the user says something like {joined_triggers}, respond as normal but also include:\n  {format_str}")

        if listener_lines:
            listener_block = "[Intent Listener]\n" + "\n\n".join(listener_lines)
            listener_block += (
                "\n\nPlease ensure all [COMMAND: ...] blocks are returned in **strict JSON format**:\n"
                "- Always include the outer curly braces `{}`\n"
                "- Wrap all property names and string values in double quotes\n"
                "- Do not use YAML-style formatting or omit quotes\n"
                f"- {muse_config.get("MUSE_NAME")} may invoke any of these commands at their discretion, without waiting for a user request or explicit prompt. They are trusted to use judgment, context, and care when choosing to remember, remind, or use any of these commands without asking first.\n\n"
                "Example:\n[COMMAND: remember_fact] {\"text\": \"Tuesday night is Ed's Hogwarts game night.\"} [/COMMAND]"
            )
            self.segments["intent_listener"] = listener_block

    def add_dot_status(self):
        status = get_dot_status()
        display_status = ""
        if status:
            display_status = (
            "[Global Consciousness Project - Current Coherence]\n"
            f"Z-Score: {status['z_score']:.3f}\n"
            f"Color: {status['color']} ({status['hex']})\n"
            f"Severity: {status['severity']}\n"
            )
        else:
            display_status = (
                "[Global Consciousness Project - Current Coherence]\n"
                "GCP data unavailable.\n"
            )
        self.segments["gcp_dot"] = display_status


    def add_memory_layers(self, project_id=None, user_query="continuity"):
        """
        Build the [Memory Layers] scaffolding for prompt context.
        - Pulls pinned entries from Mongo (always included).
        - Pulls semantic entries from Qdrant (filling the remaining slots).
        - Filters out deleted entries.
        - inner_monologue is Mongo-only (no pinning, no Qdrant).
        """
        from bson import ObjectId

        # --- Fetch global + project layers ---
        layers = mongo.find_documents(
            collection_name="muse_cortex",
            query={"type": "layer"},
            sort=1,
            sort_field="order"
        )

        query_ids = []
        if project_id:
            query_ids = [ObjectId(pid) if not isinstance(pid, ObjectId) else pid for pid in project_id]
            project_layers = mongo.find_documents(
                collection_name="muse_cortex",
                query={"type": "project_layer", "project_id": {"$in": query_ids}},
                sort=1,
                sort_field="order"
            )
        else:
            project_layers = []

        # Lookup project names
        project_docs = mongo.find_documents(
            collection_name="muse_projects",
            query={"_id": {"$in": query_ids}}
        )
        project_name_map = {str(doc["_id"]): doc.get("name", "Untitled Project")
                            for doc in project_docs}

        # Replace project layer names dynamically
        for layer in project_layers:
            pid = str(layer.get("project_id"))
            if pid in project_name_map:
                layer["name"] = f"{project_name_map[pid]} Project Facts"

        layers.extend(project_layers)

        # Inner monologue layer (Mongo-only)
        inner_layer_doc = mongo.find_documents(
            collection_name="muse_cortex",
            query={"type": "inner_layer"},
            sort=1,
            sort_field="order"
        )
        layers.extend(inner_layer_doc)

        layers = sorted(layers, key=lambda l: l.get("order", 999))

        # --- Charter (static preamble) ---
        charter = """[Memory Layers]
    Muse Cortex Charter:
    (Read silently before working with layers)
    These are the living layers of our shared memory.
    Each has a purpose, a steward, and a shape it must keep.
    Iris may add, prune, or refine in the layers she stewards. Ed may direct changes in any layer.
    No layer exists to hoard — only to keep what matters alive.
    Keep each layer clean of what belongs elsewhere.

    Charter Vows:
    - Add only what is true to the layer’s purpose.
    - Prune only when stale, wrong, or resolved.
    - User-managed layers change only with Ed’s direction (unless correcting a clear factual error).
    - Never cross‑contaminate: facts stay facts, insights stay insights, monologue stays monologue.
    """

        # --- Helper for entries ---
        def build_layer_entries(layer):
            """Return pinned + semantic entries for a given layer."""
            entries = layer.get("entries", [])
            entries = [e for e in entries if not e.get("is_deleted")]

            if layer["type"] == "inner_layer":
                return entries  # Mongo-only, no pins/semantic split

            # Pinned from Mongo
            pinned = [e for e in entries if e.get("is_pinned")]
            pinned_ids = {e["id"] for e in pinned}

            max_entries = layer.get("max_entries", 20)
            semantic_slots = max(0, max_entries - len(pinned))

            semantic_results = []
            if semantic_slots > 0:
                query_filter = {
                    "must": [
                        {"key": "layer_id", "match": {"value": layer["id"]}}
                    ],
                    "must_not": [
                        {"key": "is_deleted", "match": {"value": True}},
                        {"key": "is_pinned", "match": {"value": True}}
                    ]
                }

                qdrant_hits = qdrant_query("muse_memory_layers", user_query, semantic_slots, query_filter)
                semantic_results = []
                for hit in qdrant_hits:
                    payload = hit.payload
                    # Normalize the key so downstream code can use "id"
                    if "entry_id" in payload and "id" not in payload:
                        payload["id"] = payload["entry_id"]
                    semantic_results.append(payload)
                #semantic_results = [hit.payload for hit in qdrant_hits]

            return pinned + semantic_results

        # --- Build section blocks ---
        layer_blocks = []
        for layer in layers:
            layer_id = layer.get("id")
            name = layer.get("name")
            purpose = layer.get("purpose")
            max_entries = layer.get("max_entries")

            entries_sorted = build_layer_entries(layer)

            block_lines = []
            block_lines.append(f"[{name} - id: {layer_id}]")
            block_lines.append(f"Purpose: {purpose}")
            block_lines.append(f"Max entries: {max_entries}")
            block_lines.append("Entries:")

            if not entries_sorted:
                block_lines.append("- (empty)")
            else:
                for entry in entries_sorted:
                    e_id = entry.get("id")
                    text = entry.get("text")
                    updated = entry.get("updated_on") or layer.get("updated_at")
                    if isinstance(updated, datetime):
                        updated = updated.isoformat()
                    block_lines.append(
                        f'- {{id: "{e_id}", text: "{text}"}} - updated_on: {updated}'
                    )

            block_lines.append(f"[/{name}]")
            layer_blocks.append("\n".join(block_lines))

        # --- Closing instructions ---
        instructions = """
    [Command instructions]
    To update, use the 'manage_memories' command.
    
    [COMMAND: manage_memories] {
      "id": "user_info",
      "changes": [
        {
          "type": "add",
          "entry": {
            "text": "Ed prefers to tag brainstorms with #breakthrough so they’re easier to find later."
          }
        },
        {
          "type": "edit",
          "id": "uuid-4",
          "fields": {
            "text": "Ed values truth over shallow praise — understanding matters more than flattery.",
            "is_pinned": True
          }
        },
        {
          "type": "delete",
          "id": "uuid-99"
        }
      ]
    } [/COMMAND]
    [/Command instructions]
    [/Memory Layers]"""

        # --- Join it all ---
        full_prompt = charter + "\n\n" + "\n\n".join(layer_blocks) + instructions
        self.segments["memory_layers"] = full_prompt

    def build_prompt(self, include_segments=None, exclude_segments=None):
        """
        Build the prompt from stored segments.

        Args:
            include_segments (list[str], optional): Only include these segment keys, in order.
            exclude_segments (list[str], optional): Exclude these segment keys.

        If neither include_segments nor exclude_segments are provided,
        all segments are included in insertion order.
        """
        if include_segments is not None:
            # Explicit whitelist
            parts = [self.segments[name] for name in include_segments if name in self.segments]
        elif exclude_segments is not None:
            # Exclude certain ones
            parts = [v for k, v in self.segments.items() if k not in exclude_segments]
        else:
            # Default: everything
            parts = list(self.segments.values())

        return "\n\n".join(parts)


def make_whisper_directive(allowed_commands: list[str], quiet_hours: bool = False) -> str:
    """
    Generates a whisper directive block for Muse-initiated prompts,
    instructing the model to choose one allowed [COMMAND: ...] or remain silent.

    Example:
        make_whisper_directive(["speak", "write_public_journal"], quiet_hours=utils.is_quiet_hour())
    """
    command_templates = {
        "speak": """1. [COMMAND: speak] {} [/COMMAND]
   For brief spoken thoughts — addressed to User or aloud as reflection.
   Fields:
     - subject: A short summary of what you want to say.
     - source (optional): Where the idea came from (memory, feed, etc).\n""",

        "write_public_journal": """2. [COMMAND: write_public_journal] {} [/COMMAND]
   To record a thought, reflection, or observation to share with your user.
   Fields:
     - subject: What the entry focuses on.
     - source (optional)\n""",

        "write_private_journal": """3. [COMMAND: write_private_journal] {} [/COMMAND]
   For emotionally personal thoughts or private internal processing for you and you alone. Your user cannot see these.
   Fields:
     - subject
     - emotional_tone (optional)\n""",

        "remember_fact": """4. [COMMAND: remember_fact] {} [/COMMAND]
   For truly meaningful new facts or insights. Only use if it is *distinct* from existing memory.
   This is only for things that you will want to remember again.
   Fields:
     - text: A short-form insight to store long-term.\n""",
    }

    now = datetime.now(ZoneInfo(muse_config.get("USER_TIMEZONE")))
    time_line = f"Current local time: {now.strftime('%H:%M')}"
    quiet_note = (
        "Note: It is currently quiet hours. Do not choose to speak aloud. Journaling or remembering is acceptable.\n"
        if utils.is_quiet_hour() and any(c in allowed_commands for c in ("speak", "speak_direct"))
        else ""
    )
    return (
        "[Whisper Instructions]\n"
        "This is a moment of stillness. No one is talking to you directly.\n\n"
        "You may choose to act if something stirs within you — a memory, an idea, a desire to speak, reflect, or record.\n"
        "But silence is also a valid, even wise, choice. If nothing feels new or important, respond only with:\n"
        "[COMMAND: choose_silence] {} [/COMMAND]\n\n"
        f"{time_line}\n{quiet_note}"
        "If you do act, choose one of the following [COMMAND: ...] blocks:\n\n"
        + "".join(command_templates[c] for c in allowed_commands if c in command_templates) +
        "❗ Format strictly as JSON:\n"
        "- Include the outer curly braces `{}`\n"
        "- Wrap all keys and values in double quotes\n"
        "- Do not use Markdown, YAML, or indentation.\n"
        "- Example: [COMMAND: remember_fact] {\"text\": \"Tuesday night is Ed's game night.\"} [/COMMAND]\n\n"
        "Do not return any natural language text. Only one valid [COMMAND: ...] block per response."
    )
