// utils/messageActions.js
export function CandleHolderLit(props) {
  return (
    <svg
      xmlns="https://www.w3.org/2000/svg"
      width="16"
      height="16"
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

export function setProjectOnMessage(setMessages, message_id, project_id) {
  fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_ids: [message_id], set_project: project_id }),
  }).then(() => {
    setMessages(prev => {
      console.log('setProject prev:', typeof prev, Array.isArray(prev), prev);
      return prev.map(m =>
        m.message_id === message_id ? { ...m, project_id } : m
      );
    });
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


export function addToThread(setMessages, setThreadMessages, message_ids, thread_id) {
  if (!message_ids.length || !thread_id) return;

  // 1) Optimistic UI update in main list
  setMessages(prev =>
    prev.map(m => {
      if (!message_ids.includes(m.message_id)) return m;
      const existing = m.thread_ids || [];
      if (existing.includes(thread_id)) return m;
      return { ...m, thread_ids: [...existing, thread_id] };
    })
  );

  // 1b) Optimistic UI update in thread list (if it already has any of these messages)
  if (setThreadMessages) {
    setThreadMessages(prev =>
      prev.map(m => {
        if (!message_ids.includes(m.message_id)) return m;
        const existing = m.thread_ids || [];
        if (existing.includes(thread_id)) return m;
        return { ...m, thread_ids: [...existing, thread_id] };
      })
    );
  }

  // 2) Fire-and-forget server update
  return fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message_ids,
      add_threads: [thread_id],
    }),
  });
}

export function removeFromThread(setMessages, setThreadMessages, message_ids, thread_id) {
  if (!message_ids.length || !thread_id) return;

  // 1) Optimistic UI update in main list
  setMessages(prev =>
    prev.map(m => {
      if (!message_ids.includes(m.message_id)) return m;
      const existing = m.thread_ids || [];
      if (!existing.length) return m;
      return {
        ...m,
        thread_ids: existing.filter(tid => tid !== thread_id),
      };
    })
  );

  // 1b) Optimistic UI update in thread list (if it already has any of these messages)
  if (setThreadMessages) {
    setThreadMessages(prev =>
      prev.map(m => {
        if (!message_ids.includes(m.message_id)) return m;
        const existing = m.thread_ids || [];
        if (!existing.length) return m;
        return {
          ...m,
          thread_ids: existing.filter(tid => tid !== thread_id),
        };
      })
    );
  }

  // 2) Fire-and-forget server update
  return fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message_ids,
      remove_threads: [thread_id],
    }),
  });
}

export async function handleMultiAction(
  updateMessages,
  selectedMessageIds,
  action,
  options = {}
) {
  const { project_id, tagsToAdd = [], tagsToRemove = [], thread_id } = options;

  const body = { message_ids: selectedMessageIds };

  switch (action) {
    case "hide":
      body.is_hidden = true;
      break;
    case "unhide":
      body.is_hidden = false;
      break;
    case "delete":
      body.is_deleted = true;
      break;
    case "undelete":
      body.is_deleted = false;
      break;
    case "make_private":
      body.is_private = true;
      break;
    case "make_public":
      body.is_private = false;
      break;
    case "highlight":
      body.remembered = true;
      break;
    case "unhighlight":
      body.remembered = false;
      break;
    case "set_project":
      body.set_project = project_id ?? false;
      break;
    case "add_tags":
      if (!tagsToAdd.length) return;
      body.add_user_tags = tagsToAdd;
      break;
    case "remove_tags":
      if (!tagsToRemove.length) return;
      body.remove_user_tags = tagsToRemove;
      break;
    case "add_threads":
      body.add_threads = thread_id ?? false;
      break;
    case "remove_threads":
      body.remove_threads = thread_id ?? false;
      break;
    default:
      return;
  }

  const res = await fetch("/api/messages/tag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    console.error("Bulk action failed");
    return;
  }

  updateMessages(prev =>
    prev.map(m => {
      if (!selectedMessageIds.includes(m.message_id)) return m;

      switch (action) {
        case "hide":
          return { ...m, is_hidden: true };
        case "unhide":
          return { ...m, is_hidden: false };
        case "delete":
          return { ...m, is_deleted: true };
        case "undelete":
          return { ...m, is_deleted: false };
        case "make_private":
          return { ...m, is_private: true };
        case "make_public":
          return { ...m, is_private: false };
        case "highlight":
          return { ...m, remembered: true };
        case "unhighlight":
          return { ...m, remembered: false };
        case "set_project":
          return { ...m, project_id };
        case "add_tags": {
          if (!tagsToAdd.length) return m;
          const existing = m.user_tags || [];
          const merged = Array.from(new Set([...existing, ...tagsToAdd]));
          return { ...m, user_tags: merged };
        }
        case "remove_tags": {
          if (!tagsToRemove.length) return m;
          const existing = m.user_tags || [];
          return {
            ...m,
            user_tags: existing.filter((t) => !tagsToRemove.includes(t)),
          };
        }
        case "add_threads": {
          const existing = m.thread_ids || [];
          const merged = Array.from(new Set([...existing, ...thread_id]));
          return { ...m, thread_ids: merged };
        }
        case "remove_threads": {
          const existing = m.thread_ids || [];
          return {
            ...m,
            thread_ids: existing.filter((t) => !thread_id.includes(t)),
          };
        }
        default:
          return m;
      }
    })
  );
}


