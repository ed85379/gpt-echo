from rapidfuzz import fuzz


def find_relevant_snippets(user_input, conversation_log, threshold=50, top_k=5):
    """
    Returns top_k most relevant entries from today's conversation log.

    Args:
        user_input (str): The new user prompt.
        conversation_log (list): List of log entries (dicts with 'message' keys).
        threshold (int): Minimum fuzzy match score to consider.
        top_k (int): Number of most relevant entries to return.

    Returns:
        list: Selected relevant conversation log entries.
    """
    scored_entries = []

    for entry in conversation_log:
        score = fuzz.token_set_ratio(user_input, entry.get("message", ""))
        if score >= threshold:
            scored_entries.append((score, entry))

    # Sort by score descending and return top_k
    scored_entries.sort(reverse=True)
    return [entry for score, entry in scored_entries[:top_k]]
