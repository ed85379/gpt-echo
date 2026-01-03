# text_filters.py
import re
from typing import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Optional

# 1. Tags whose *entire blocks* we want to nuke (tag + inner content)
BLOCK_XML_TAGS = [
    "command-response",
    "internal-data",
]

# 2. Tags where we only strip the tags, *keep* inner text
#    Right now this list is intentionally empty, but we wire it for later.
TAG_ONLY_STRIP_XML_TAGS: list[str] = [
    "remove-this-tag"
    # e.g. "some-future-wrapper",
]

# 3. JSON blobs — we don’t want these in embeddings/prompts
JSON_BLOCK_PATTERN = re.compile(
    r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}",
    re.DOTALL,
)


BLOCK_XML_PATTERN = re.compile(
    r"<\s*(?P<tag>" + "|".join(re.escape(tag) for tag in BLOCK_XML_TAGS) + r")\b[^>]*>"
    r"(?:(?!<\s*(?P=tag)\b).)*?"
    r"</\s*(?P=tag)\s*>",
    re.DOTALL | re.IGNORECASE,
)



def build_tag_only_pattern(extra_tags: Iterable[str] | None = None) -> re.Pattern | None:
    tags = list(TAG_ONLY_STRIP_XML_TAGS)
    if extra_tags:
        tags.extend(extra_tags)

    if not tags:
        return None

    return re.compile(
        r"<\s*/?\s*(?:"
        + "|".join(re.escape(tag) for tag in tags)
        + r")\b[^>]*>",
        re.IGNORECASE,
    )

def strip_block_xml(text: str) -> str:
    """
    Remove entire blocks like:
      <command-response> ... </command-response[example]>
      <internal-data> ... </internal-data>
    including their contents.
    """
    return BLOCK_XML_PATTERN.sub("", text)


def strip_tag_only_xml(text: str, extra_tags: Iterable[str] | None = None) -> str:
    """
    Strip only the opening/closing tags for a given set of XML-ish tags,
    but leave their inner content untouched.
    Currently unused (empty list), but ready for future tags.
    """
    pattern = build_tag_only_pattern(extra_tags)
    if not pattern:
        return text
    return pattern.sub("", text)


def strip_json(text: str, mode=None) -> str:
    if mode == "replace":
        return JSON_BLOCK_PATTERN.sub("/// JSON BLOCK REMOVED FOR BREVITY ///", text)
    return JSON_BLOCK_PATTERN.sub("", text)

# This one has limited usefulness, so it isn't used.
def normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()

def clean_message_text(
    raw_text: str,
    *,
    remove_json_mode=None,
    extra_tag_only_xml: Iterable[str] | None = None,
) -> str:
    """
    Shared cleaner for:
      - embedding input
      - prompt construction

    Removes:
      - <command-response[example]>...</command-response[example]> blocks
      - <internal-data>...</internal-data> blocks
      - (optionally) JSON blobs
    Optionally:
      - strips only the tags (not content) for a configurable set of XML-ish wrappers.

    Leaves:
      - <muse-experience>, <muse-interlude>, etc., untouched for now.
    """
    text = raw_text

    # 1. Kill block-listed XML sections entirely
    text = strip_block_xml(text)

    # 2. Strip tag-only wrappers if/when we define any
    text = strip_tag_only_xml(text, extra_tags=extra_tag_only_xml)

    # 3. Strip JSON blobs (dev/infra, not story)
    if remove_json_mode is None:
        # default: remove
        text = strip_json(text)
    elif remove_json_mode == "replace":
        text = strip_json(text, mode="replace")
    elif remove_json_mode == "disabled":
        pass  # leave JSON intact
    else:
        raise ValueError(f"Unknown remove_json_mode: {remove_json_mode!r}")

    # 4. Normalize whitespace
    #text = normalize_whitespace(text)

    return text


class CodeBlockFilterMode(str, Enum):
    REMOVE = "remove"      # remove entire block
    REPLACE = "replace"    # replace with marker
    TRUNCATE = "truncate"  # keep first N lines, then marker


@dataclass
class CodeBlockFilterConfig:
    enabled: bool = True
    # Any block with more than this many lines is considered "large"
    max_lines: int = 40
    # How to handle "large" blocks
    mode: CodeBlockFilterMode = CodeBlockFilterMode.TRUNCATE
    # Optional: minimum lines before we even consider a block "codey" enough
    # to filter. E.g. ignore blocks with <= 5 lines.
    min_lines_for_filter: int = 6
    # Marker text used for REPLACE / TRUNCATE
    marker_text: str = "/// Code block shortened for brevity ///"
    # Note for Future Ed:
    # - min_lines_for_filter: only treat blocks with >= this many lines as "big code".
    #   Shorter blocks are left untouched, even if max_lines is smaller.
    # - max_lines: how many lines to KEEP when truncating big blocks.
    #   Anything over this gets shortened according to `mode`.
    #
    # Example for Mnemosyne prompt:
    #   max_lines=3, min_lines_for_filter=6, mode=TRUNCATE
    #   -> only blocks with 6+ lines are truncated to 3 lines + marker.

# Regex to capture ```lang?\n ... \n``` blocks, non-greedy
_CODE_BLOCK_RE = re.compile(
    r"```([^\n`]*)\n(.*?)```",
    re.DOTALL
)

MNEMOSYNE_EMBEDDING_CODE_CFG = CodeBlockFilterConfig(
    enabled=True,
    mode=CodeBlockFilterMode.REMOVE,
    max_lines=0,
    min_lines_for_filter=0,
)

MNEMOSYNE_PROMPT_CODE_CFG = CodeBlockFilterConfig(
    enabled=True,
    mode=CodeBlockFilterMode.TRUNCATE,
    max_lines=3,
    min_lines_for_filter=6,
    marker_text="/// Code block shortened for brevity ///",
)

def filter_code_blocks_by_lines(
    text: str,
    config: Optional[CodeBlockFilterConfig] = None
) -> str:
    """
    Apply line-count based filtering to ``` ``` blocks.

    Modes:
      - REMOVE:   remove entire block (including backticks)
      - REPLACE:  replace entire block with a marker block
      - TRUNCATE: keep first N lines, then add marker, then closing ```
    """
    if config is None:
        # Default: do nothing
        return text

    if not config.enabled:
        return text

    def _replace(match: re.Match) -> str:
        lang = match.group(1) or ""  # may be empty
        body = match.group(2)

        # Normalize to \n for counting
        # Strip trailing newline so splitlines() behaves nicely
        body_stripped = body.rstrip("\n")
        lines = body_stripped.splitlines()
        line_count = len(lines)

        # If it's a short block, leave it alone
        if line_count <= config.min_lines_for_filter:
            return match.group(0)

        # If it's within allowed size, leave it alone
        if line_count <= config.max_lines:
            return match.group(0)

        # Over the limit: apply mode
        mode = config.mode

        if mode == CodeBlockFilterMode.REMOVE:
            # Remove entire block
            return ""

        if mode == CodeBlockFilterMode.REPLACE:
            # Replace with a synthetic block
            # Optionally include line_count in marker
            marker = f"{config.marker_text} (original {line_count} lines)"
            return f"```{lang}\n{marker}\n```"

        if mode == CodeBlockFilterMode.TRUNCATE:
            # Keep first N lines, then marker, then closing ```
            kept = lines[: config.max_lines]
            remaining = line_count - config.max_lines
            marker = f"{config.marker_text} (remaining {remaining} lines omitted)"
            new_body = "\n".join(kept + [marker])
            return f"```{lang}\n{new_body}\n```"

        # Fallback: if somehow an unknown mode sneaks in, be conservative
        return match.group(0)

    return _CODE_BLOCK_RE.sub(_replace, text)


class TextFilterPurpose(str, Enum):
    MNEMOSYNE_EMBEDDING = "mnemosyne_embedding"
    MNEMOSYNE_PROMPT = "mnemosyne_prompt"
    RECENT_CONTEXT = "recent_context"
    RELEVANT_MEMORIES = "relevant_memories"

def _json_mode_for_purpose(purpose: TextFilterPurpose) -> str | None:
    if purpose == TextFilterPurpose.MNEMOSYNE_EMBEDDING:
        return None  # default: remove
    if purpose == TextFilterPurpose.MNEMOSYNE_PROMPT:
        return "replace"
    if purpose in (TextFilterPurpose.RECENT_CONTEXT,
                   TextFilterPurpose.RELEVANT_MEMORIES):
        return "disabled"
    return None

def filter_text_for_purpose(
    raw_text: str,
    purpose: TextFilterPurpose,
) -> str:
    # 1. Base cleaner (XML + JSON)
    json_mode = _json_mode_for_purpose(purpose)
    text = clean_message_text(
        raw_text,
        remove_json_mode=json_mode,
        # you can also pass extra_tag_only_xml based on purpose if needed
    )

    # 2. Code blocks
    code_cfg = _code_cfg_for_purpose(purpose)
    if code_cfg and code_cfg.enabled:
        text = filter_code_blocks_by_lines(text, code_cfg)

    # 3. (Optional) whitespace normalization per‑purpose
    # if purpose in (TextFilterPurpose.MNEMOSYNE_EMBEDDING,):
    #     text = normalize_whitespace(text)

    return text

def _code_cfg_for_purpose(purpose: TextFilterPurpose) -> CodeBlockFilterConfig | None:
    if purpose == TextFilterPurpose.MNEMOSYNE_EMBEDDING:
        return MNEMOSYNE_EMBEDDING_CODE_CFG
    if purpose == TextFilterPurpose.MNEMOSYNE_PROMPT:
        return MNEMOSYNE_PROMPT_CODE_CFG
    # maybe no code filtering for recent context:
    if purpose in (TextFilterPurpose.RECENT_CONTEXT,
                   TextFilterPurpose.RELEVANT_MEMORIES):
        return None
    return None