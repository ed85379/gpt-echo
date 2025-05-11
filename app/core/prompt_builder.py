# prompt_builder.py

from app import config
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core import memory_core, journal_core, discovery_core, utils
from app.core.memory_core import cortex
from sentence_transformers import SentenceTransformer
import numpy as np


model = SentenceTransformer(config.SENTENCE_TRANSFORMER_MODEL)
USE_QDRANT = config.USE_QDRANT


class PromptBuilder:
    def __init__(self, destination="default"):
        self.destination = destination
        self.segments = {}
        self.now = datetime.now(ZoneInfo(memory_core.USER_TIMEZONE)).isoformat()

    def add_profile(self, subset: list[str] = None, as_dict: bool = False):
        profile = memory_core.load_profile(subset=subset, as_dict=as_dict)
        if profile:
            if as_dict:
                profile = json.dumps(profile, ensure_ascii=False, indent=2)
            self.segments["profile"] = f"[User Time]{self.now}\n\n[Profile]\n{profile.strip()}"

    def add_core_principles(self):
        principles = memory_core.load_core_principles()
        if principles:
            self.segments["principles"] = f"[Principles]\n{principles.strip()}"

    def add_cortex_entries(self, types: list[str]):
        all_entries = []
        for entry_type in types:
            entries = memory_core.cortex.get_entries_by_type(entry_type)
            all_entries.extend(entries)

        if all_entries:
            entry_texts = [f"- {entry['text'].strip()}" for entry in all_entries if entry.get("text")]
            self.segments["thoughts"] = "[Echo Cortex]\n" + "\n".join(entry_texts)

    def add_cortex_thoughts(self):
        entries = memory_core.cortex.get_entries_by_type("echo_thoughts")
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

    def add_recent_conversation(self, query="*", top_k=5, days_back=1, bias_source=None, bias_author_id=None, model=model):
        entries = memory_core.search_recent_logs(query, model=model, top_k=top_k, days_back=days_back)
        if entries:
            formatted = "\n\n".join(e.get("labeled_text", "") for e in entries if "labeled_text" in e)
            self.segments["conversation_log"] = f"[Conversation Context]\n\n{formatted}"

    def add_recent_lines(self, count=10):
        # Use today's date in user's timezone
        now = datetime.now(ZoneInfo(config.get_setting("USER_TIMEZONE", "UTC")))
        date_str = now.strftime("%Y-%m-%d")

        logs = memory_core.load_log_for_date(date_str)
        last_lines = logs[-count:] if len(logs) >= count else logs
        formatted = "\n\n".join(
            f"{entry.get('role', '').capitalize()}: {entry.get('message', '').strip()}"
            for entry in last_lines if entry.get("message")
        )
        if formatted:
            self.segments["conversation_log"] = f"[Conversation Context]\n\n{formatted}"

    def add_indexed_memory(self, query="*", top_k=5, bias_source=None, bias_author_id=None, use_qdrant=USE_QDRANT):
        entries = memory_core.search_indexed_memory(query, top_k=top_k, use_qdrant=use_qdrant)
        if entries:
            formatted = "\n\n".join(e.get("message", "") for e in entries)
            self.segments["indexed_memory"] = f"[Indexed Memory]\n\n{formatted}"

    def add_journal_thoughts(self, query="*", top_k=5):
        thoughts = journal_core.search_indexed_journal(query=query, top_k=top_k, include_private=False)
        if thoughts:
            formatted = "\n\n".join(t["text"] for t in thoughts)
            self.segments["journal"] = f"[Journal]\n{formatted}"

    def add_discovery_snippets(self, query="*", max_items=5):
        snippets = discovery_core.fetch_discoveryfeeds(max_per_feed=10)
        if not snippets:
            return

        query_vec = np.array(model.encode([query])[0], dtype="float32")
        entries = []

        for snippet in snippets:
            vec = np.array(model.encode([snippet])[0], dtype="float32")
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
            "discord": "Match the tone and length of the user input.",
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
        from app.core.echo_responder import COMMANDS  # local import to avoid circular issues

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
    Generates a whisper directive block for Echo-initiated prompts,
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
   To record an insight, reflection, or observation in the public journal.
   Fields:
     - subject: What the entry focuses on.
     - source (optional)\n""",

        "write_private_journal": """3. [COMMAND: write_private_journal]
   For emotionally personal thoughts or private internal processing.
   Fields:
     - subject
     - emotional_tone (optional)\n""",

        "remember_fact": """4. [COMMAND: remember_fact]
   For meaningful new facts or insights. Only use if it is *distinct* from existing memory.
   Fields:
     - text: A short-form insight to store long-term.\n""",
    }

    now = datetime.now(ZoneInfo(config.USER_TIMEZONE))
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
        "Before choosing a topic, review the [Recent Thoughts] section and do not repeat subjects you've recently written or spoken about.\n\n"
        "If you do act, choose one of the following [COMMAND: ...] blocks:\n\n"
        + "".join(command_templates[c] for c in allowed_commands if c in command_templates) +
        "❗ Format strictly as JSON:\n"
        "- Include the outer curly braces `{}`\n"
        "- Wrap all keys and values in double quotes\n"
        "- Do not use Markdown, YAML, or indentation.\n"
        "- Example: [COMMAND: remember_fact] {\"text\": \"Tuesday night is Ed's Hogwarts game night.\"}\n\n"
        "Do not return any natural language text. Only one valid [COMMAND: ...] block per response."
    )
