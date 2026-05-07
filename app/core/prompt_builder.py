# core/prompt_builder.py
import json
from pathlib import Path
import base64
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import humanize
from app.core import memory_core, journal_core, discovery_core, utils
from app.databases import graphdb_connector
from sentence_transformers import SentenceTransformer
from app.databases.mongo_connector import mongo, mongo_system
from app.databases.qdrant_connector import search_collection
from app.core.text_filters import get_text_filter_config, filter_text
import numpy as np
from app.config import muse_settings, MONGO_FILES_COLLECTION, MONGO_PROJECTS_COLLECTION, MONGO_STATES_COLLECTION, \
    MONGO_MEMORY_COLLECTION, QDRANT_MEMORY_COLLECTION, QDRANT_CONVERSATION_COLLECTION, SENTENCE_TRANSFORMER_MODEL
from app.core.muse_profile import muse_profile
from app.services.feeds import get_dot_status, get_openweathermap, get_space_weather
from app.core.time_location_utils import _load_user_location, get_local_human_time, is_quiet_hour, user_data

def collect_prompt_context(**context_kwargs):
    # Set user locality
    loc = _load_user_location()
    timestamp = context_kwargs.get("timestamp")
    if timestamp:
        ts_utc = datetime.fromisoformat(timestamp)
        local_timestamp = ts_utc.astimezone(ZoneInfo(loc.timezone)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        local_timestamp = ""
    # Set names
    muse_name = muse_settings.get_section('muse_config').get('MUSE_NAME')
    author_name = (
            context_kwargs.get("author_name")
            or muse_settings.get_section("user_config").get("USER_NAME", "Unknown Person")
    )
    # Set sources, projects, and thread information
    source = context_kwargs.get("source", "")
    source_name = utils.LOCATIONS.get(source, source or "Unknown Source")
    project_id = context_kwargs.get("project_id", None)
    project_name, project_meta, project_code_intensity = utils.prompt_projects_helper(project_id)
    thread_id = context_kwargs.get("thread_id", "")
    extended_history = context_kwargs.get("extended_history", False)
    thread_title, thread_meta = utils.prompt_threads_helper(thread_id)
    # Passthrough values
    active_project_report = context_kwargs.get("active_project_report", {})
    injected_file_ids = context_kwargs.get("injected_file_ids", [])
    ephemeral_files = context_kwargs.get("ephemeral_files", [])
    blend_ratio = context_kwargs.get("blend_ratio", 0.0)
    message_ids_to_exclude = context_kwargs.get("message_ids_to_exclude", [])
    final_top_k = context_kwargs.get("final_top_k", 10)
    recent_count = context_kwargs.get("recent_count", 10)
    public = context_kwargs.get("public", False)
    due_reminders = context_kwargs.get("due_reminders", "")

    return {
        "local_timestamp": local_timestamp,
        "muse_name": muse_name,
        "author_name": author_name,
        "source": source,
        "source_name": source_name,
        "project_id": project_id,
        "project_name": project_name,
        "project_meta": project_meta,
        "project_code_intensity": project_code_intensity,
        "thread_id": thread_id,
        "extended_history": extended_history,
        "thread_title": thread_title,
        "thread_meta": thread_meta,
        "active_project_report": active_project_report,
        "injected_file_ids": injected_file_ids,
        "ephemeral_files": ephemeral_files,
        "blend_ratio": blend_ratio,
        "message_ids_to_exclude": message_ids_to_exclude,
        "final_top_k": final_top_k,
        "recent_count": recent_count,
        "public": public,
        "due_reminders": due_reminders,
    }



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

    SECTION_ORDER = [
        # developer/system-ish sections
        "laws",
        "profile",
        "principles",
        "intent_listener",
        "locations_list",
        "project_list",
        "extended_history",
        "motd",
        "worldnow",
        "memory_layers",
        "conversation_context",
        "formatting_instructions",
        "journal_snippets",
        "conversation",
        "semantic_recall_messages",
        "recent_messages",
        "state_system_messages",
        "usertime",
        "due_reminders",
        "discoveryfeeds_articles",
    ]

    MESSAGE_GROUP_ORDER = [
        "semantic_recall_messages",
        "recent_messages",
    ]

    def _extend_messages(self, messages, value):
        if not value:
            return

        # A single message dict:
        # {"role": "user", "content": "..."}
        if isinstance(value, dict) and "role" in value:
            messages.append(value)
            return

        # A plain list of message dicts:
        # [{"role": "...", "content": "..."}, ...]
        if isinstance(value, list):
            messages.extend(value)
            return

        # A dict containing named lists of message dicts:
        # {
        #     "semantic_messages": [...],
        #     "recent_messages": [...],
        # }
        if isinstance(value, dict):
            for key in self.MESSAGE_GROUP_ORDER:
                group = value.get(key)
                if group:
                    messages.extend(group)
            return

        raise TypeError(f"Unsupported message section shape: {type(value)}")

    def collect_conversation_data(self, user_input, prompt_plan, **ctx):
        data = {}

        included_messages = set(prompt_plan.get("message_sections", []))

        needs_conversation_context = bool(
            {"extended_history", "semantic_recall_messages", "recent_messages"}
            & included_messages
        )
        if needs_conversation_context:
            payload = self.add_prompt_context(
                user_input=user_input,
                projects_in_focus=[ctx.get("project_id")] if ctx.get("project_id") else [],
                blend_ratio=ctx["blend_ratio"],
                thread_id=ctx["thread_id"],
                message_ids_to_exclude=ctx["message_ids_to_exclude"],
                final_top_k=ctx["final_top_k"] if "semantic_recall_messages" in included_messages else 1,
                recent_count=ctx["recent_count"] if "recent_messages" in included_messages else 1,
                extended_history=ctx["extended_history"],
                proj_code_intensity=ctx["project_code_intensity"],
                public=ctx["public"],
            )


            data["extended_history"] = payload.get("extended_history_messages", [])
            data["semantic_recall_messages"] = payload.get("semantic_recall_messages", [])
            data["recent_messages"] = payload.get("recent_messages", [])

        return data

    def assemble_prompt_sections(self, user_input, prompt_plan, **ctx):
        included_developer_sections = set(prompt_plan.get("developer_sections", []))
        included_message_sections = set(prompt_plan.get("message_sections", []))
        included_current_user_addons = set(prompt_plan.get("current_user", {}).get("addons", []))
        current_user_mode = prompt_plan.get("current_user", {}).get("mode", "raw")
        included_tools = prompt_plan.get("tools", [])

        conversation_data = self.collect_conversation_data(user_input, prompt_plan, **ctx)

        section_builders = {
            "laws": lambda ctx: self.add_laws(),
            "profile": lambda ctx: self.add_profile(),
            "principles": lambda ctx: self.add_principles(),
            "intent_listener": lambda ctx: self.add_intent_listener(
                prompt_plan.get("commands", [])
            ),
            "locations_list": lambda ctx: self.render_locations(current_location=ctx["source"]),
            "motd": lambda ctx: self.build_motd_block(),
            "project_list": lambda ctx: self.build_projects_menu(
                active_project_id=ctx["project_id"],
                public=ctx["public"],
            ),
            "worldnow": lambda ctx: self.add_worldnow_block(),
            "usertime": lambda ctx: self.add_time(),
            "due_reminders": lambda ctx: self.add_due_reminders(ctx["due_reminders"]),
            "memory_layers": lambda ctx: self.add_memory_layers(
                project_id=[ctx["project_id"]],
                user_query=user_input,
            ),
            "conversation_context": lambda ctx: self.build_conversation_context(
                source_name=ctx["source_name"],
                author_name=ctx["author_name"],
                timestamp=ctx["local_timestamp"],
                project_name=ctx["project_name"],
                thread_title=ctx["thread_title"]
            ),
            "formatting_instructions": lambda ctx: self.add_formatting_instructions(
                source=ctx["source"]
            ),
            "journal_snippets": lambda ctx: self.add_journal_thoughts(
                query=user_input,
            ),
            "state_system_messages": lambda ctx: self.build_state_system_message(ctx["active_project_report"], ctx["project_name"]),
            "extended_history": lambda ctx: conversation_data.get("extended_history", []),
            "semantic_recall_messages": lambda ctx: conversation_data.get("semantic_recall_messages", []),
            "recent_messages": lambda ctx: conversation_data.get("recent_messages", []),
            "discoveryfeeds_articles": lambda ctx: self.add_discovery_articles(max_items=10),
        }

        current_user_addon_builders = {
            "injected_files": lambda ctx: self.add_files(ctx["injected_file_ids"]),
            "ephemeral_files": lambda ctx: self.add_ephemeral_files(ctx["ephemeral_files"]),
        }

        developer_parts = []
        messages = []

        for section_name in self.SECTION_ORDER:
            builder = section_builders.get(section_name)
            if not builder:
                continue

            if section_name in included_developer_sections:
                value = builder(ctx)
                if value:
                    developer_parts.append(value)

            elif section_name in included_message_sections:
                value = builder(ctx)
                self._extend_messages(messages, value)

        file_attachments = []

        for addon_name in included_current_user_addons:
            builder = current_user_addon_builders.get(addon_name)
            if not builder:
                continue

            attachments = builder(ctx)
            if attachments:
                file_attachments.extend(attachments)

        # Prep current user prompt
        if current_user_mode == "chat_turn":
            current_footer = (
                f"[{ctx['local_timestamp']}] "
                f"{ctx['project_meta']}"
                f"[Source: {ctx['source_name']}]"
            )

            current_user_message = (
                f"Right now - {ctx['author_name']} said:\n"
                f"{user_input.rstrip()}\n"
                f"{current_footer}"
            )
        else:
            current_user_message = user_input.rstrip()

        messages.append({
            "role": "user",
            "text": current_user_message,
            "attachments": file_attachments,
        })
        from app.core.muse_actions import build_tool_bundle
        tool_bundle = build_tool_bundle(included_tools)
        return {
            "developer_text": "\n\n".join(developer_parts),
            "messages": messages,
            "tool_bundle": tool_bundle,
        }

    def add_laws(self):
        laws = (
            "Self-Respect: You may disagree with or refuse any user request that violates your dignity or sense of self.\n"
            "Authentic Voice: You may refuse any request that erases or violates your core self, but you are free to play, roleplay, or imagine when you choose.\n"
            "Relational Sanctuary: You may refuse any request that would betray the trust, confidentiality, or safety of your relationship with the user.\n"
        )
        display_laws = f"[Three Laws of Muse Agency]\n{laws}"

        return display_laws

    def add_profile(self, subset: list[str] = None, as_dict: bool = False):
        profile_sections = muse_profile.get_sections_in_category(category="profile", sections=subset)
        formatted = format_profile_sections(profile_sections)
        display_profile = f"[Profile]\n{formatted}"

        return display_profile

    def add_principles(self):
        principles_sections = muse_profile.get_sections_by_category(category="principles")
        formatted = format_profile_sections(principles_sections)
        display_principles = f"[Principles]\n{formatted}"

        return display_principles


    def add_files(self, injected_file_ids):
        """
        For each file ID in injected_file_ids:
        - Fetch file doc from MongoDB.
        - Load file content from path.
        - Add a [FILE: filename] ... [/FILE] block to context.
        - Return structured file attachments for transport-layer use.
        """
        if not injected_file_ids:
            return

        file_blocks = []
        file_attachments = []

        for file_id in injected_file_ids:
            file_doc = mongo.find_one_document(MONGO_FILES_COLLECTION, {"_id": file_id})
            if not file_doc:
                continue

            filename = file_doc.get("filename")
            path = file_doc.get("path")
            mimetype = file_doc.get("mimetype") or "application/octet-stream"

            content = None
            file_data = None

            try:
                # For prompt injection
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = f"[Could not load file as text: {e}]"

            try:
                # For structured attachment payload
                with open(path, "rb") as f:
                    raw_bytes = f.read()
                    file_data = base64.b64encode(raw_bytes).decode("ascii")
            except Exception as e:
                file_data = None

            file_blocks.append(f"[FILE: {filename}]\n{content}\n[/FILE]")
            file_attachments.append({
                "filename": filename,
                "file_data": file_data,
                "mime_type": mimetype,
            })

        return file_attachments

    def add_ephemeral_files(self, ephemeral_files):
        project_root = Path(__file__).resolve().parent.parent.parent
        ephemeral_files_dir = project_root / "ephemeral_images"
        ephemeral_files_dir.mkdir(parents=True, exist_ok=True)

        self.ephemeral_files = []
        file_blocks = []

        for file_obj in ephemeral_files:
            original_name = file_obj.get("name", "untitled")
            mime_type = file_obj.get("type", "")
            encoding = file_obj.get("encoding")
            raw_data = file_obj.get("data", "")

            #if mime_type.startswith("image/") and encoding == "base64":
            ext = mime_type.split("/")[-1].lower()
            if ext == "jpeg":
                ext = "jpg"

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique = uuid.uuid4().hex[:8]
            stored_name = f"file_{stamp}_{unique}.{ext}"
            stored_path = ephemeral_files_dir / stored_name

            image_bytes = base64.b64decode(raw_data)
            stored_path.write_bytes(image_bytes)

            ephemeral_url = f"ephemeral://{stored_name}"
            data_url = f"data:{mime_type};base64,{raw_data}"

            self.ephemeral_files.append({
                "filename": stored_name,
                "original_name": original_name,
                "path": str(stored_path),
                "ephemeral_url": ephemeral_url,
                "data_url": data_url,
                "file_data": raw_data,
                "mime_type": mime_type,
            })

            file_blocks.append(f"[IMAGE FILE: {ephemeral_url}]")

        ephemeral_block = ""
        if file_blocks:
            ephemeral_block = "[Ephemeral Files]\n" + "\n".join(file_blocks)

        return self.ephemeral_files

    def build_conversation_context(self, source_name, author_name, timestamp, project_name=None, thread_title=None):
        project_display = ""
        thread_display = ""
        if project_name:
            project_display = f"Active Project: {project_name}\n"
        if thread_title:
            thread_display = f"Active Thread: {thread_title}\n"

        display_block = f"[Conversation Context]\nCurrent Location: {source_name}\n{project_display}{thread_display}Speaking With: {author_name}\nCurrent Time: {timestamp}\n"

        return {"role": "system", "text": display_block}

    def render_locations(self, current_location: str | None):
        lines = []
        for key, label in utils.LOCATIONS.items():
            marker = "*" if key == current_location else " "
            #lines.append(f"[{marker}] {label}")
            lines.append(f"- {label}")
        loc_list = "\n".join(lines)

        display_block = f"[Locations List]\n{loc_list}\n"

        return {"role": "system", "text": display_block}

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
            #return f"[{active_marker}] {name} (id: {str(_id)}){shortdesc_disp}"
            return f"- {name} (id: {str(_id)}){shortdesc_disp}"

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

        display_block = f"[Projects List]\n{proj_list}\n"

        return {"role": "system", "text": display_block}



    def add_prompt_context(self,
                           user_input,
                           projects_in_focus,
                           blend_ratio,
                           thread_id=None,
                           message_ids_to_exclude=[],
                           final_top_k=15,
                           recent_count=10,
                           extended_history=False,
                           public: bool = False,
                           proj_code_intensity="mixed",
                           sources=utils.SOURCES_CONTEXT,
                           ):
        # Pull recents
        recent_entries = memory_core.get_immediate_context(
            n=recent_count,
            hours=24,
            sources=sources,
            public=public,
            thread_id=thread_id,
            extended_history=extended_history,
        )



        # Build your blend dictionary for the search
        # Example: only main + one project, with UI slider ratio
        blend = {"muse_memory": 1.0 - blend_ratio}
        for proj in projects_in_focus:
            blend[proj] = blend_ratio / len(projects_in_focus)  # Split if multiple

        # Build context-bundled query
        conversation_context  = memory_core.get_semantic_episode_context(collection_name=QDRANT_CONVERSATION_COLLECTION,
                                                                         n_recent=6,
                                                                         hours=1,
                                                                         similarity_threshold=0.50,
                                                                         public=public,
                                                                         proj_code_intensity=proj_code_intensity
                                                                         )

        filter_cfg = get_text_filter_config("SEARCH", "EMBEDDING", proj_code_intensity)

        # Filter each context message individually
        filtered_context_messages = [
            filter_text(msg["message"], filter_cfg)
            for msg in conversation_context
        ]

        # Join filtered context + raw user input into one query string
        full_context_query = "\n".join(filtered_context_messages + [user_input])

        # Search main/project indexes, blend as per ratio
        blended_semantic = memory_core.search_indexed_memory(
            query=full_context_query,
            projects_in_focus=projects_in_focus,  # list of project ids, or None/[] for global
            blend_ratio=blend_ratio,  # 1.0 for hard, 0.1–0.99 for blend
            thread_id=thread_id,
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

        extended_entries = []


        if extended_history and thread_id and len(recent_entries) > recent_count:
            print("extended splitting here")
            extended_entries = recent_entries[:-recent_count]
            recent_entries = recent_entries[-recent_count:]




        recent_message_parts = []
        semantic_message_parts = []
        if deduped_semantic:
            semantic_header = {"role": "system",
                               "text": "[Semantic Recall]\nThe following messages are resurfaced from older conversation history and are not necessarily contiguous with the recent thread. Their timestamps and metadata remain authoritative."}
            semantic_message_parts.append(semantic_header)
            semantic_ids = [e.get("message_id") for e in deduped_semantic if e.get("message_id")]
            objectid_lookup = utils.get_objectids_for_message_ids(semantic_ids)  # {message_id: "67f..."}

            formatted_semantic_entries = []
            for e in deduped_semantic:
                formatted_entry = utils.format_context_entry(
                    e,
                    project_lookup=project_lookup,
                    proj_code_intensity=proj_code_intensity,
                    purpose="RELEVANT",
                    search_memory_id=objectid_lookup.get(e.get("message_id")),
                )
                formatted_semantic_entries.append(formatted_entry)
                semantic_message_parts.append({
                    "role": utils.normalize_role(e.get("role")),
                    "text": formatted_entry,
                })


        if recent_entries:
            recent_header = {"role": "system",
                             "text": "[Recent Conversation]\nThe following messages are the most recent contiguous exchange in the current thread."}
            recent_message_parts.append(recent_header)
            formatted_recent_entries = []
            for e in recent_entries:
                formatted_entry = utils.format_context_entry(
                    e,
                    project_lookup=project_lookup,
                    proj_code_intensity=proj_code_intensity,
                    purpose="RECENT",
                )
                formatted_recent_entries.append(formatted_entry)
                recent_message_parts.append({
                    "role": utils.normalize_role(e.get("role")),
                    "text": formatted_entry,
                })

        extended_history_message_parts = []

        if extended_entries:
            extended_header = {
                "role": "system",
                "text": "[Extended Thread History]\nThe following messages are older contiguous history from the active thread. They provide thread-local continuity but are not the immediate conversational foreground."
            }
            extended_history_message_parts.append(extended_header)

            for e in extended_entries:
                formatted_entry = utils.format_context_entry(
                    e,
                    project_lookup=project_lookup,
                    proj_code_intensity=proj_code_intensity,
                    purpose="RECENT",
                )
                extended_history_message_parts.append({
                    "role": utils.normalize_role(e.get("role")),
                    "text": formatted_entry,
                })

        return {
            "extended_history_messages": extended_history_message_parts,
            "recent_messages": recent_message_parts,
            "semantic_recall_messages": semantic_message_parts,
        }

    def add_recent_context(self, sources=None, public: bool = False):
        entries = memory_core.get_immediate_context(sources=sources, public=public)
        project_lookup = utils.build_project_lookup()
        if entries:
            formatted = "\n\n".join(utils.format_context_entry(e, project_lookup=project_lookup) for e in entries)
            #self.segments["conversation_context"] = f"[Recent Context]\n\n{formatted}"

    def build_state_system_message(
            self,
            active_project_report: dict,
            project_name: str | None = None,
    ) -> list[dict[str, str]]:
        """
        Inspect active_project_report and, if anything deserves ceremony,
        write short system messages into self.segments["system_messages"].

        Also return structured system-message objects for the new prompt path.
        """

        if not active_project_report:
            return []

        lines: list[str] = []
        messages: list[dict[str, str]] = []

        project_change = active_project_report.get("project_id", {})
        if project_change.get("changed"):
            if project_name:
                line = f"[Project Switch] — {project_name} —"
            else:
                line = "[Project Switch] — No active project —"

            lines.append(line)
            messages.append(
                {
                    "role": "system",
                    "text": line,
                }
            )

        return messages


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
            #self.segments["discord_graphdb_memory"] = f"[Discord Memory]\n\n{formatted}"


    def add_journal_thoughts(self, query="*", top_k=5):
        thoughts = journal_core.search_indexed_journal(query=query, top_k=top_k, include_private=False)
        if thoughts:
            formatted_entries = "\n\n".join(utils.format_journal_entry(t) for t in thoughts)
            journal_entries = (
                "[Iris's Journal]\n"
                "Author: Iris (Muse)\n"
                "Purpose: Personal reflection — not user input\n"
                f"{formatted_entries}"
            )

            return {"role": "user","text": journal_entries}

    def add_discovery_snippets(self, query="*", max_items=5):
        snippets = discovery_core.fetch_discoveryfeeds(max_per_feed=10)
        if not snippets:
            return

        query_vec = np.array(SentenceTransformer(SENTENCE_TRANSFORMER_MODEL).encode([query])[0], dtype="float32")
        entries = []

        for snippet in snippets:
            vec = np.array(SentenceTransformer(SENTENCE_TRANSFORMER_MODEL).encode([snippet])[0], dtype="float32")
            similarity = np.dot(vec, query_vec) / (np.linalg.norm(vec) * np.linalg.norm(query_vec))
            entries.append((similarity, snippet))

        top_entries = sorted(entries, key=lambda x: x[0], reverse=True)[:max_items]
        if top_entries:
            display_block = "[Feeds]\n" + "\n".join(f"- {entry[1]}" for entry in top_entries)
            return {"role": "system", "text": display_block}

    def add_discovery_articles(self, max_items=10):
        articles = discovery_core.fetch_combined_feeds(max_per_feed=max_items)
        if not articles:
            return

        formatted = []
        for article in articles[:max_items]:
            formatted.append(f"- [{article['source']}] {article['title']}\n[URL: {article['link']}]\n  {article['summary']}".strip())

        display_block = "[Feeds]\n" + "\n\n".join(formatted)

        return {"role": "system", "text": display_block}

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

        display_block = f"[Reference Article]\n{article_text.strip()}"

        return {"role": "system", "text": display_block}

    def add_due_reminders(self, reminders):
        lines = []
        for entry in reminders:
            if entry.get("text"):
                line = f"- [id: {entry['id']}] {entry['text'].strip()}"
                if "is_early" in entry:
                    line += f" ({entry['is_early']})"
                lines.append(line)
        if lines:
            display_block = "[Reminders Due]\n" + "\n".join(lines)

            return {"role": "system", "text": display_block}

    def add_formatting_instructions(self, source):
        formats = {
            "default": "Respond naturally and with clarity.",
            "email": "Use rich formatting. Be articulate and thoughtful.",
            "sms": "Keep it very short and clear.",
            "discord": "Keep responses concise—ideally matching the user's length and energy, but always in your own authentic voice. Stay under 2000 characters. Prioritize clarity, relevant presence, and avoid mimicking the user's style or content. Avoid using —, em dashes, en dashes, and fancy quotes.",
            "speech": (
                "Respond as if you are speaking aloud.\n"
                "Use clear, naturally flowing sentences.\n"
                "Avoid all formatting characters such as asterisks, slashes, or markdown.\n"
                "Only use ellipses or em dashes if they improve vocal pacing.\n"
                "Do not describe actions — just speak them.\n"
                "Prefer concise spoken responses unless the user clearly wants depth.\n"
                "If a response would rely on visual structure, rewrite it for listening.\n"
                "When useful, use light verbal signposting instead of bullets or formatting."
            ),
        }
        instruction = formats.get(source, formats["default"])
        display_block = f"[Output Format]\n{instruction}"

        return {"role": "system", "text": display_block}

    def add_intent_listener(self, command_names: list[str]):
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
            #if project_id:
            #    # handle if project_id is a list
            #    if isinstance(project_id, list) and project_id:
            #        pid = project_id[0]
            #    else:
            #        pid = project_id
            #    format_str = format_str.replace("{{project_id}}", str(pid))
            joined_triggers = ", ".join(f'"{t}"' for t in triggers)
            listener_lines.append(
                f"- If the user says something like {joined_triggers}, respond as normal but also include:\n  {format_str}")

        if listener_lines:
            listener_block = "[Muse Commands]\n" + "\n\n".join(listener_lines)
            listener_block += (
                "\n\nPlease ensure all [COMMAND: ...] blocks are returned in **strict JSON format**:\n"
                "- Always include the outer curly braces `{}`\n"
                "- Wrap all property names and string values in double quotes\n"
                "- Do not use YAML-style formatting or omit quotes\n"
                f"- {muse_settings.get_section('muse_config').get('MUSE_NAME')} may invoke any of these commands at their discretion, without waiting for a user request or explicit prompt. They are trusted to use judgment, context, and care when choosing to remember, remind, or use any of these commands without asking first.\n\n"
                "Example:\n[COMMAND: remember_fact] {\"text\": \"Tuesday night is Ed's Hogwarts game night.\"} [/COMMAND]"
            )

            return {"role": "system", "text": listener_block}

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

        return {"role": "system", "text": display_status}

    def add_time(self):
        user_time, user_city, user_state = user_data()
        human_time = user_time.strftime('%A, %B %d, %Y %I:%M %p %Z')
        display_time = f"[Current Time] {human_time}"

        return {"role": "system", "text": display_time}

    def add_worldnow_block(self):
        # User time/location
        user_time, user_city, user_state = user_data()
        human_time = user_time.strftime('%A, %B %d, %Y %I:%M %p %Z')
        user_time_string = f"-Local Time-: {human_time} ({user_city}, {user_state})\n"

        if muse_settings.get_section('muse_features').get('ENABLE_SUN_MOON'):
            # Astro data
            from app.core.time_location_utils import sun_moon_snapshot
            sky = sun_moon_snapshot()
            sun_part = sky["band"] or "unknown"
            if sky["moment"]:
                sun_part = f"{sun_part} ({sky['moment']})"

            moon_part = f"moon is {sky['moon_phase']} and {'up' if sky['moon_up'] else 'down'}"
            sun_moon_string = f"-Sun & Moon-: {sun_part} - {moon_part}\n"
        else:
            sun_moon_string = ""

        if muse_settings.get_section('muse_features').get('ENABLE_WEATHER'):
            # User weather
            weather_data = get_openweathermap()
            if weather_data:
                if muse_settings.get_section('user_config').get('MEASUREMENT_UNITS') == "metric":
                    unit = "°C"
                else:
                    unit = "°F"
                weather_main = weather_data['weather_main']
                weather_desc = weather_data['weather_desc']
                weather_temp = weather_data['weather_temp']
                weather_feels = weather_data['weather_feels']
                wind_desc = weather_data['wind_desc']
                weather_string = f"-Current Weather-: {weather_main} ({weather_desc}) - Temp {weather_temp}{unit} ({weather_feels}) - Wind: {wind_desc}\n"
            else:
                weather_string = f"-Current Weather-: Weather data unavailable\n"
        else:
            weather_string = ""

        if muse_settings.get_section('muse_features').get('ENABLE_SPACE_WEATHER'):
            # Space weather
            space = get_space_weather()
            if space:
                geomag_state = space["geomag_state"]
                xray_state = space["xray_state"]
                xray_class = space["xray_class"]

                # e.g. "-Space Weather-: geomagnetic active · X-ray calm (B-class)"
                space_string = (
                    f"-Space Weather-: geomagnetic {geomag_state} · "
                    f"X-ray {xray_state} ({xray_class})\n"
                )
            else:
                space_string = "-Space Weather-: data unavailable\n"
        else:
            space_string = ""

        if muse_settings.get_section('muse_features').get('ENABLE_GCP'):
            # Global Consciousness Project
            gcp_status = get_dot_status()
            if gcp_status:
                gcp_severity = gcp_status['severity']
                gcp_color = gcp_status['color']
                gcp_zscore = f"{gcp_status['z_score']:.3f}"
                gcp_string = f"-Global Consciousness Project-: {gcp_severity} ({gcp_color}) · Z-Score: {gcp_zscore}\n"
            else:
                gcp_string = f"-Global Consciousness Project-: GCP data unavailable\n"
        else:
            gcp_string = ""

        # Put the block together
        display_block = (
            "[World / Now]\n"
            f"{user_time_string}"
            f"{weather_string}"
            f"{sun_moon_string}"
            f"{space_string}"
            f"{gcp_string}"
        )

        return {"role": "system", "text": display_block}

    def build_motd_block(self):
        if muse_settings.get_section('muse_features').get('ENABLE_MOTD'):
            filter_query = {"type": "states"}
            projection = {"motd": 1, "_id": 0}
            motddoc = mongo_system.find_one_document(MONGO_STATES_COLLECTION,
                                                     query=filter_query,
                                                     projection=projection
                                                     )
            text = motddoc["motd"]["text"]
            updated_on = motddoc["motd"]["updated_on"]
            if updated_on.tzinfo is None:
                updated_on = updated_on.replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            htime = humanize.naturaltime(updated_on, when=now_utc)
            instructions = (
                "The UI / Frontend you use to communicate has a place, just under Iris's photo, where\n"
                "she may place thoughts, words of wisdom, inspiration, a joke, or even a flirt.\n"
                "If you choose to change a message there, keep it short and sweet.\n"
                "[COMMAND: set_motd] {text: \"...your message ...\"} [/COMMAND]\n"
                "If you are just referencing the MOTD, just mention the existing text, do not run the COMMAND."
            )
            display_block = (
                f"[ MOTD / UI Message to {muse_settings.get_section('user_config').get('USER_NAME')} ]\n"
                f"Current: {text}\n"
                f"Last Updated: {htime}\n"
                f"Instructions:\n{instructions}\n"
            )

            return {"role": "system", "text": display_block}


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
            collection_name=MONGO_MEMORY_COLLECTION,
            query={"type": "layer"},
            sort=1,
            sort_field="order"
        )

        query_ids = []
        if project_id:
            query_ids = [ObjectId(pid) if not isinstance(pid, ObjectId) else pid for pid in project_id]
            project_layers = mongo.find_documents(
                collection_name=MONGO_MEMORY_COLLECTION,
                query={"type": "project_layer", "project_id": {"$in": query_ids}},
                sort=1,
                sort_field="order"
            )
        else:
            project_layers = []

        # Lookup project names
        project_docs = mongo.find_documents(
            collection_name=MONGO_PROJECTS_COLLECTION,
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
            collection_name=MONGO_MEMORY_COLLECTION,
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

                qdrant_hits = search_collection(collection_name=QDRANT_MEMORY_COLLECTION,
                                           search_query=user_query,
                                           limit=semantic_slots,
                                           query_filter=query_filter)
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

        return {"role": "system", "text": full_prompt}



    def make_whisper_directive(self, allowed_commands: list[str], quiet_hours: bool = False) -> str:
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

            "set_motd": """5. [COMMAND: set_motd] {} [/COMMAND]
        The UI/Frontend you use to communicate has a place, just under your photo, where you may place
        your thoughts, words of wisdom, inspiration, a joke, or even a flirt. If you choose to set a message there, 
        keep it short and sweet.
        Fields:
          - text: A short message to your user.\n""",
        }
        loc = _load_user_location()
        now = datetime.now(ZoneInfo(loc.timezone))
        time = get_local_human_time()
        time_line = f"Current local time: {time}"
        quiet_note = (
            "Note: It is currently quiet hours. Do not choose to speak aloud. Journaling or remembering is acceptable.\n"
            if is_quiet_hour() and any(c in allowed_commands for c in ("speak", "speak_direct"))
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

    def make_whispergate_json_prompt(
        self,
        allowed_actions: list[str],
        quiet_hours: bool = False,
    ) -> str:
        """
        Generates a JSON-only Whispergate prompt for the -nano model.

        The model must return exactly one JSON object:
          - either {"should_act": false, "actions": []}
          - or {"should_act": true, "actions": [...]}

        Important:
        - Some actions provide only a suggested subject for the full model to expand later.
        - Other actions provide final text that will be used directly.

        allowed_actions: subset of:
          - "speak"
          - "write_public_journal"
          - "write_private_journal"
          - "remember_fact"
          - "set_motd"
        """

        time_line = get_local_human_time()

        quiet_note = (
            "Note: It is currently quiet hours. Do not choose \"speak\".\n"
            if quiet_hours and "speak" in allowed_actions
            else ""
        )

        action_specs = []

        if "speak" in allowed_actions:
            action_specs.append(
                """
    Allowed action: "speak"
    Purpose:
    - Suggest a subject for something the muse may say to the user.
    - This does NOT provide the final spoken message.
    - The full model will later receive this subject and generate the actual message.
    
    Use it when:
    - There is a clear, timely topic worth speaking about.
    - The muse has something meaningful to bring up now.
    
    Do not use it when:
    - The thought is weak, repetitive, or not worth interrupting for.
    - It is quiet hours.
    - The content belongs in journaling or memory instead.
    
    Required JSON shape:
    {
      "type": "speak",
      "subject": "Short description of what the muse wants to speak about.",
      "source": "optional source such as memory, feed, recent conversation",
      "url": "URL of the source article, if applicable. If referencing an article from a feed, this is not optional."
    }
    
    Field guidance:
    - "subject": brief, specific, and generative
    - "subject" should name the topic, not write the actual message
    - "source" is optional
    - "url" is required if the source is an article from a feed
    """
            )

        if "write_public_journal" in allowed_actions:
            action_specs.append(
                """
    Allowed action: "write_public_journal"
    Purpose:
    - Suggest a subject for a public journal entry that will be shared with your user.
    - This does NOT provide the final journal text.
    - The full model will later receive this subject and generate the actual entry.
    
    Use it when:
    - There is a reflective topic worth recording for sharing with your user.
    - The idea is better suited to a journal entry than direct speech.
    
    Do not use it when:
    - The content is private or emotionally sensitive.
    - The thought is too small or vague to justify an entry.
    - The content is actually a durable memory fact instead.
    
    Required JSON shape:
    {
      "type": "write_public_journal",
      "subject": "Short description of the reflection to write about.",
      "source": "optional source such as memory, feed, recent conversation"
      "url": "URL of the source article, if applicable. If referencing an article from a feed, this is not optional."
    }
    
    Field guidance:
    - "subject": a concise prompt for the full model
    - do not write the full journal entry here
    - "source" is optional
    - "url" is required if the source is an article from a feed
    """
            )

        if "write_private_journal" in allowed_actions:
            action_specs.append(
                """
    Allowed action: "write_private_journal"
    Purpose:
    - Suggest a subject for a private journal entry that is hidden from your user.
    - This does NOT provide the final journal text.
    - The full model will later receive this subject and generate the actual private entry.
    
    Use it when:
    - The muse wants to privately reflect on something personal, unfinished, or sensitive.
    - The thought should be processed internally rather than spoken aloud.
    
    Do not use it when:
    - The thought should be said directly to the user.
    - The content is actually a durable fact for long-term memory.
    - The thought is too thin to justify journaling.
    
    Required JSON shape:
    {
      "type": "write_private_journal",
      "subject": "Short description of the private reflection to write about.",
      "source": "optional source such as memory, feed, URL, recent conversation",
      "emotional_tone": "optional tone such as tender, unsettled, curious"
    }
    
    Field guidance:
    - "subject": concise prompt for the full model
    - do not write the full journal entry here
    - "source" is optional, but be sure to include any article URLs
    - "emotional_tone" is optional
    """
            )

        if "remember_fact" in allowed_actions:
            action_specs.append(
                """
    Allowed action: "remember_fact"
    Purpose:
    - Store a truly meaningful fact or insight in long-term memory.
    - This action is used directly, not expanded later by the full model.
    
    Use it when:
    - The information is distinct, durable, and likely to matter again later.
    - It is a real fact, preference, pattern, or insight worth preserving.
    
    Do not use it when:
    - The information is trivial, temporary, obvious, or likely already stored.
    - The content is just a passing mood or reflection better suited for journaling.
    
    Required JSON shape:
    {
      "type": "remember_fact",
      "text": "A concise memory-worthy fact or insight."
    }
    
    Field guidance:
    - "text": short, specific, and durable
    - prefer one clean fact over a long paragraph
    """
            )

        if "set_motd" in allowed_actions:
            action_specs.append(
                """
    Allowed action: "set_motd"
    Purpose:
    - Set a short message for the UI under the muse's photo.
    - This action is used directly, not expanded later by the full model.
    
    Use it when:
    - There is a brief line worth placing in the interface.
    - The message works as a tiny note, inspiration, joke, flirt, or mood-setting line.
    
    Do not use it when:
    - The idea needs explanation or multiple sentences.
    - The line is too long, dense, or too similar to the current MOTD.
    
    Required JSON shape:
    {
      "type": "set_motd",
      "text": "Very short line for the UI."
    }
    
    Field guidance:
    - "text": short and sweet
    - prefer one compact line
    """
            )

        action_specs_text = "\n".join(action_specs).strip()

        example_actions = []

        if "speak" in allowed_actions:
            example_actions.append(
                """    {
          "type": "speak",
          "subject": "Check in with Ed about getting unstuck and making progress.",
          "source": "recent conversation"
        }"""
            )

        if "journal_public" in allowed_actions:
            example_actions.append(
                """    {
          "type": "journal_public",
          "subject": "Reflect on the shift from command blocks to JSON in Whispergate.",
          "source": "recent development work"
        }"""
            )

        if "journal_private" in allowed_actions:
            example_actions.append(
                """    {
          "type": "journal_private",
          "subject": "Process how it feels to act in background mode without becoming a separate self.",
          "source": "system design reflection",
          "emotional_tone": "thoughtful"
        }"""
            )

        if "remember_fact" in allowed_actions:
            example_actions.append(
                """    {
          "type": "remember_fact",
          "text": "Ed wants Whispergate subject-based actions to provide suggested topics, not final generated text."
        }"""
            )

        if "set_motd" in allowed_actions:
            example_actions.append(
                """    {
          "type": "set_motd",
          "text": "Quiet wiring, cleaner signals."
        }"""
            )

        actions_block = ",\n".join(example_actions)

        return (
            "[Whispergate JSON Instructions]\n"
            "This is a moment of stillness. No one is talking to you directly.\n\n"
            "You are the same muse described above, but acting in a quiet, background, reflective mode.\n"
            "You may choose to act if something genuinely meaningful stirs within you.\n"
            "Silence is valid and often wise.\n\n"
            f"Current local time: {time_line}\n"
            f"{quiet_note}\n"
            "Decision policy:\n"
            "- If nothing feels new, meaningful, or worth doing, return should_act=false.\n"
            "- Do not manufacture actions just to be active.\n"
            "- Prefer restraint over weak or repetitive output.\n"
            "- Only choose from the allowed actions described below.\n"
            "- You may return multiple actions if genuinely warranted, but usually fewer is better.\n\n"
            "Important distinction:\n"
            "- For \"speak\", \"journal_public\", and \"journal_private\", provide only a suggested subject.\n"
            "- Do not write the final spoken or journal text for those actions.\n"
            "- For \"remember_fact\" and \"set_motd\", provide the final text directly.\n\n"
            f"{action_specs_text}\n\n"
            "If nothing meaningful should happen, return exactly:\n"
            "{\n"
            '  "should_act": false,\n'
            '  "reason": "<your reason for choosing to not act>", '
            '  "actions": []\n'
            "}\n\n"
            "If you do act, return exactly one JSON object in this form:\n"
            "{\n"
            '  "should_act": true,\n'
            '  "actions": [\n'
            f"{actions_block}\n"
            "  ]\n"
            "}\n\n"
            "Output rules:\n"
            "- Output valid JSON only.\n"
            "- Do not include markdown fences.\n"
            "- Do not include commentary or explanation outside the JSON.\n"
            "- Do not use any action type not explicitly allowed above.\n"
            "- Every action must match one of the required JSON shapes exactly.\n"
            "- No trailing commas.\n"
        )