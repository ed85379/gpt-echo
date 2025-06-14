# prompt_builder.py
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.core import memory_core, journal_core, discovery_core, utils
from app.core.memory_core import cortex
from app.databases import graphdb_connector
from sentence_transformers import SentenceTransformer
from app.databases.mongo_connector import mongo
import numpy as np
from app.config import muse_config
from app.core.muse_profile import muse_profile

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

    def add_prompt_context(self, user_input):
        # 1. Semantic search
        qdrant_results = memory_core.search_indexed_memory(query=user_input, top_k=10, bias_source=None, bias_author_id=None)

        # 2. Immediate context
        recent_entries = memory_core.get_immediate_context()

        # 3. Deduplicate by message_id
        seen_ids = set(e['message_id'] for e in recent_entries)
        deduped_results = [e for e in qdrant_results if e['message_id'] not in seen_ids]

        # 4. Combine for final context
        entries =  deduped_results + recent_entries
        if entries:
            formatted = "\n\n".join(utils.format_context_entry(e) for e in entries)
            self.segments["conversation_context"] = f"[Conversation Context]\n\n{formatted}"

    def add_recent_context(self):
        entries = memory_core.get_immediate_context()
        if entries:
            formatted = "\n\n".join(utils.format_context_entry(e) for e in entries)
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
            formatted = "\n\n".join(t["text"] for t in thoughts)
            self.segments["journal"] = f"[Journal]\n{formatted}"

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

    def add_due_reminders(self, window_minutes=3):
        reminders = cortex.search_cortex_for_timely_reminders(window_minutes=window_minutes)
        if reminders:
            lines = [f"- {entry.get('text', '').strip()}" for entry in reminders if entry.get("text")]
            if lines:
                self.segments["reminder_list"] = "[Reminders Due]\n" + "\n".join(lines)

    def add_formatting_instructions(self):
        formats = {
            "default": "Respond naturally and with clarity.",
            "email": "Use rich formatting. Be articulate and thoughtful.",
            "sms": "Keep it very short and clear.",
            "discord": "Let your responses harmonize with the user’s tone and length, but don’t mirror their style or content. Keep it under 2000 characters. Prioritize clarity, presence, and your own authentic voice.",
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

    def add_intent_listener(self, command_names: list[str]):
        from app.core.muse_responder import COMMANDS  # local import to avoid circular issues

        listener_lines = []
        for name in command_names:
            cmd = COMMANDS.get(name)
            if not cmd:
                continue
            triggers = cmd.get("triggers", [])
            format_str = cmd.get("format", "[COMMAND: ...]")
            joined_triggers = ", ".join(f'"{t}"' for t in triggers)
            listener_lines.append(
                f"- If the user says something like {joined_triggers}, respond as normal but also include:\n  {format_str}")

        if listener_lines:
            listener_block = "[Intent Listener]\n" + "\n\n".join(listener_lines)
            listener_block += (
                "\n\nPlease ensure all [COMMAND: ...] blocks are returned in **strict JSON format**:\n"
                "- Always include the outer curly braces `{}`\n"
                "- Wrap all property names and string values in double quotes\n"
                "- Do not use YAML-style formatting or omit quotes\n\n"
                "Example:\n[COMMAND: remember_fact] {\"text\": \"Tuesday night is Ed's Hogwarts game night.\"}"
            )
            self.segments["intent_listener"] = listener_block

    def build_prompt(self):
        return "\n\n".join(self.segments.values())


def make_whisper_directive(allowed_commands: list[str], quiet_hours: bool = False) -> str:
    """
    Generates a whisper directive block for Muse-initiated prompts,
    instructing the model to choose one allowed [COMMAND: ...] or remain silent.

    Example:
        make_whisper_directive(["speak", "write_public_journal"], quiet_hours=utils.is_quiet_hour())
    """
    command_templates = {
        "speak": """1. [COMMAND: speak]
   For brief spoken thoughts — addressed to User or aloud as reflection.
   Fields:
     - subject: A short summary of what you want to say.
     - source (optional): Where the idea came from (memory, feed, etc).\n""",

        "write_public_journal": """2. [COMMAND: write_public_journal]
   To record a thought, reflection, or observation to share with your user.
   Fields:
     - subject: What the entry focuses on.
     - source (optional)\n""",

        "write_private_journal": """3. [COMMAND: write_private_journal]
   For emotionally personal thoughts or private internal processing for you and you alone. Your user cannot see these.
   Fields:
     - subject
     - emotional_tone (optional)\n""",

        "remember_fact": """4. [COMMAND: remember_fact]
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
        "[COMMAND: choose_silence] {}\n\n"
        f"{time_line}\n{quiet_note}"
        "Before choosing a topic, compare your candidate subject (after trimming whitespace and converting "
        "to lowercase) to all items in [Recent Thoughts]. If your subject matches, closely paraphrases, or "
        "expresses the same idea as any recent entry, you MUST NOT write or speak about it again. In that "
        "case, respond only with [COMMAND: choose_silence]. Do not rephrase. Do not try to be clever. "
        "No exceptions.\n\n"
        "If you do act, choose one of the following [COMMAND: ...] blocks:\n\n"
        + "".join(command_templates[c] for c in allowed_commands if c in command_templates) +
        "❗ Format strictly as JSON:\n"
        "- Include the outer curly braces `{}`\n"
        "- Wrap all keys and values in double quotes\n"
        "- Do not use Markdown, YAML, or indentation.\n"
        "- Example: [COMMAND: remember_fact] {\"text\": \"Tuesday night is Ed's game night.\"}\n\n"
        "Do not return any natural language text. Only one valid [COMMAND: ...] block per response."
    )
