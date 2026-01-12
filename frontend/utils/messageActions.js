export function CandleHolderLit(props) {
  return (
    <svg
      xmlns="https://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="lucide lucide-candle-holder-lit-icon lucide-candle-holder-lit"
      {...props}
      >
      <path d="M10 2S8 3.9 8 5s.9 2 2 2 2-.9 2-2-2-3-2-3"/>
      <rect width="4" height="7" x="8" y="11"/>
      <path d="m13 13-1-2"/>
      <path d="M18 18a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4h18a2 2 0 1 0-2-2Z"/>
    </svg>
  );
}

export function handleDelete(setMessages, message_id, markDeleted) {
  fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_ids: [message_id], is_deleted: markDeleted }),
  }).then(() => {
    setMessages(prev =>
      prev.map(m =>
        m.message_id === message_id ? { ...m, is_deleted: markDeleted } : m
      )
    );
  });
}

export function handleTogglePrivate(setMessages, message_id, makePrivate) {
  fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_ids: [message_id], is_private: makePrivate }),
  }).then(() => {
    setMessages(prev =>
      prev.map(m =>
        m.message_id === message_id ? { ...m, is_private: makePrivate } : m
      )
    );
  });
}

export function handleToggleHidden(setMessages, message_id, makeHidden) {
  fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_ids: [message_id], is_hidden: makeHidden }),
  }).then(() => {
    setMessages(prev =>
      prev.map(m =>
        m.message_id === message_id ? { ...m, is_hidden: makeHidden } : m
      )
    );
  });
}

export function handleToggleRemembered(setMessages, message_id, makeRemembered) {
  fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_ids: [message_id], remembered: makeRemembered }),
  }).then(() => {
    setMessages(prev =>
      prev.map(m =>
        m.message_id === message_id ? { ...m, remembered: makeRemembered } : m
      )
    );
  });
}

export function setProject(setMessages, message_id, project_id) {
  fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_ids: [message_id], set_project: project_id }),
  }).then(() => {
    setMessages(prev =>
      prev.map(m =>
        m.message_id === message_id ? { ...m, project_id } : m
      )
    );
  });
}

export function clearProject(setMessages, message_id) {
  fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_ids: [message_id], set_project: false }),
  }).then(() => {
    setMessages(prev =>
      prev.map(m =>
        m.message_id === message_id ? { ...m, project_id: null } : m
      )
    );
  });
}

export function addTag(setMessages, message_id, tag) {
  fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_ids: [message_id], add_user_tags: [tag] }),
  }).then(() => {
    setMessages(prev =>
      prev.map(m =>
        m.message_id === message_id
          ? { ...m, user_tags: [...(m.user_tags || []), tag] }
          : m
      )
    );
  });
}

export function removeTag(setMessages, message_id, tag) {
  fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_ids: [message_id], remove_user_tags: [tag] }),
  }).then(() => {
    setMessages(prev =>
      prev.map(m =>
        m.message_id === message_id
          ? { ...m, user_tags: (m.user_tags || []).filter(t => t !== tag) }
          : m
      )
    );
  });
}