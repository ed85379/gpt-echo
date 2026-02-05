// threadActions.js
import { nanoid } from "nanoid";
import { addToThread } from "./messageActions";

function buildDefaultThreadTitle() {
  const now = new Date();
  const pad = n => String(n).padStart(2, "0");

  return `Thread - ${now.getFullYear()}-${pad(
    now.getMonth() + 1
  )}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

export async function createThreadWithMessages({
  setMessages,
  setThreadMessages,
  selectedMessageIds,
  setOpenThreadId,
  setActiveTab,
  updateThreadsState,
  refreshThreads,
  title, // optional
  setThreads,
}) {
  if (!selectedMessageIds || !selectedMessageIds.length) return;

  const threadId = nanoid();

  await addToThread(setMessages, setThreadMessages, selectedMessageIds, threadId);

  const nowIso = new Date().toISOString();
  const effectiveTitle = title && title.trim().length
    ? title
    : buildDefaultThreadTitle();

  // Optimistic thread
  if (setThreads) {
    setThreads(prev => [
      ...prev,
      {
        thread_id: threadId,
        title: effectiveTitle,
        is_archived: false,
        created_at: nowIso,
        updated_at: nowIso,
      },
    ]);
  }

  // Backend create
  fetch("/api/threads", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      thread_id: threadId,
      title: title ?? effectiveTitle,
    }),
  })
    .then(res => {
      if (!res.ok) {
        console.error("Failed to create thread");
      } else if (refreshThreads) {
        refreshThreads();
      }
    })
    .catch(err => {
      console.error("Error creating thread", err);
    });

  setOpenThreadId(threadId);
  setActiveTab("thread");
  updateThreadsState({ open_thread_id: threadId });
}