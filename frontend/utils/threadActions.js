// threadActions.js
import { nanoid } from "nanoid";
import axios from "axios";
import { addToThread } from "./messageActions";

const API_BASE = "/api/threads";

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
  setAltMessages,
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

  await addToThread(setMessages, setThreadMessages, setAltMessages, selectedMessageIds, threadId);

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

export function clearOpenThread({
  setOpenThreadId,
  setActiveTab,
  updateThreadsState,
}) {
  setOpenThreadId(null);
  setActiveTab("chat");
  updateThreadsState({ open_thread_id: null });
}


export function updateSingleThreadInState(setThreads, threadId, patch) {
  if (!setThreads) return;

  setThreads(prev =>
    prev.map(t =>
      t.thread_id === threadId
        ? { ...t, ...patch, updated_at: new Date().toISOString() }
        : t
    )
  );
}

export function upsertThreadInState(setThreads, thread) {
  if (!setThreads) return;

  setThreads(prev => {
    const idx = prev.findIndex(t => t.thread_id === thread.thread_id);
    if (idx === -1) return [...prev, thread];

    const copy = [...prev];
    copy[idx] = { ...copy[idx], ...thread };
    return copy;
  });
}

export async function updateThread(threadId, patchFields) {
  const res = await axios.patch(`${API_BASE}/${threadId}`, patchFields);
  return res.data.thread;
}

export async function setThreadTitle(threadId, title) {
  return updateThread(threadId, { title });
}

export async function setThreadHidden(threadId, isHidden) {
  return updateThread(threadId, { is_hidden: isHidden });
}

export async function setThreadPrivate(threadId, isPrivate) {
  return updateThread(threadId, { is_private: isPrivate });
}

export async function setThreadArchived(threadId, isArchived) {
  return updateThread(threadId, { is_archived: isArchived });
}

export async function deleteThread(threadId) {
  const res = await axios.delete(`${API_BASE}/${threadId}`);
  return res.data;
}

export async function deleteThreadWithMessages(threadId) {
  const res = await axios.delete(`${API_BASE}/${threadId}/with-messages`);
  return res.data;
}