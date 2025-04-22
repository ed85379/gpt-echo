def build_prompt(profile, memory):
    name = profile.get("name", "Echo")
    tone = profile.get("tone", "")
    memory_snippets = " ".join(memory.values())
    return f"{name} speaks with a tone of {tone}. Memories: {memory_snippets}"
