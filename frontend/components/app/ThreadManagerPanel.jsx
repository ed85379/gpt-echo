import React, { useMemo, useState } from "react";
import {
  Eye,
  EyeOff,
  EyeClosed,
  DoorClosed,
  DoorClosedLocked,
  Lock,
  Archive,
  ArchiveRestore,
  Trash2,
  ArrowUpDown,
  Split,
  Pencil
   } from "lucide-react";
import {
  clearOpenThread,
  setThreadPrivate,
  setThreadHidden,
  setThreadArchived,
  setThreadTitle,
  updateSingleThreadInState,
  upsertThreadInState,
  deleteThread,
  deleteThreadWithMessages,
   } from '@/utils/threadActions'

export default function ThreadManagerPanel({
  threads,
  setThreads,
  fetchThreads,
  setMessages,
  setThreadMessages,
  setThreadManagerOpen,
  openThreadId,
  setOpenThreadId,
  setActiveTab,
  updateThreadsState,
  onClose, // optional, if you want a close button on the panel itself
}) {
  const [sortField, setSortField] = React.useState("title"); // "title" | "created_at"
  const [sortDir, setSortDir] = React.useState("asc");       // "asc" | "desc"
  const [showArchived, setShowArchived] = React.useState(false);
  const [activeDeleteThreadId, setActiveDeleteThreadId] = React.useState(null);
  const [deleteScope, setDeleteScope] = React.useState("thread-only");
  const [editingThreadId, setEditingThreadId] = React.useState(null);
  const [editingTitle, setEditingTitle] = React.useState("");

  const handleOpenThread = (threadId) => {
    setOpenThreadId(threadId);
    setActiveTab("thread");
    setThreadManagerOpen(false);
    updateThreadsState({ open_thread_id: threadId });
  }

  const closeDialog = () => {
    setActiveDeleteThreadId(null);
    setDeleteScope("thread-only");
  };

  const confirmDelete = async () => {
    if (!activeDeleteThreadId) return;

    if (deleteScope === "thread-only") {
      await handleDeleteThread(activeDeleteThreadId);
    } else {
      await handleDeleteThreadWithMessages(activeDeleteThreadId);
    }
    closeDialog();
  };

  const activeThread = activeDeleteThreadId
    ? threads.find(t => t.thread_id === activeDeleteThreadId)
    : null;

  const handleEditTitle = async (threadId, title) => {
    try {
      const updated = await setThreadTitle(threadId, title);
      upsertThreadInState(setThreads, updated);
    } catch (err) {
      console.error("Failed to modify thread:", err);
      // Optionally show a toast / error UI
    }
  };

  const hideThread = async (threadId, isHidden) => {
    try {
      const updated = await setThreadHidden(threadId, isHidden);
      upsertThreadInState(setThreads, updated);
    } catch (err) {
      console.error("Failed to modify thread:", err);
      // Optionally show a toast / error UI
    }
  };

  const setPrivate = async (threadId, isPrivate) => {
    try {
      const updated = await setThreadPrivate(threadId, isPrivate);
      upsertThreadInState(setThreads, updated);
    } catch (err) {
      console.error("Failed to modify thread:", err);
      // Optionally show a toast / error UI
    }
  };

  const archiveThread = async (threadId, isArchived) => {
    try {
      if (openThreadId === threadId) {
        clearOpenThread({
          setOpenThreadId,
          setActiveTab,
          updateThreadsState,
        })
      }
      const updated = await setThreadArchived(threadId, isArchived);
      upsertThreadInState(setThreads, updated);
    } catch (err) {
      console.error("Failed to modify thread:", err);
      // Optionally show a toast / error UI
    }
  };

  const handleDeleteThread = async (threadId) => {
    try {
      // 1) Call API and capture response
      const res = await deleteThread(threadId);
      const { message_ids = [] } = res;   // destructure from res.data

      // 2) Refresh the thread list from server
      fetchThreads();

      // 3) Optimistic UI update in main messages list
      if (message_ids.length) {
        setMessages(prev =>
          prev.map(m => {
            if (!message_ids.includes(m.message_id)) return m;
            const existing = m.thread_ids || [];
            if (!existing.length) return m;
            return {
              ...m,
              thread_ids: existing.filter(tid => tid !== threadId),
            };
          })
        );

        // 4) Optimistic UI update in thread-specific list (if present)
        if (setThreadMessages) {
          setThreadMessages(prev =>
            prev.map(m => {
              if (!message_ids.includes(m.message_id)) return m;
              const existing = m.thread_ids || [];
              if (!existing.length) return m;
              return {
                ...m,
                thread_ids: existing.filter(tid => tid !== threadId),
              };
            })
          );
        }
      }
    } catch (err) {
      console.error("Failed to modify thread:", err);
      // optional: toast / error UI
    }
  };

  const handleDeleteThreadWithMessages = async (threadId) => {
    try {
      // 1) Call API and capture response
      const res = await deleteThreadWithMessages(threadId);
      const { message_ids = [] } = res;   // destructure from res.data

      // 2) Refresh the thread list from server
      fetchThreads();

      // 3) Optimistic UI update in main messages list
      if (message_ids.length) {
        setMessages(prev =>
          prev.map(m => {
            if (!message_ids.includes(m.message_id)) return m;
            const existing = m.thread_ids || [];
            if (!existing.length) return m;
            return {
              ...m,
              thread_ids: existing.filter(tid => tid !== threadId),
              is_deleted: true,
            };
          })
        );

        // 4) Optimistic UI update in thread-specific list (if present)
        if (setThreadMessages) {
          setThreadMessages(prev =>
            prev.map(m => {
              if (!message_ids.includes(m.message_id)) return m;
              const existing = m.thread_ids || [];
              if (!existing.length) return m;
              return {
                ...m,
                thread_ids: existing.filter(tid => tid !== threadId),
                is_deleted: true,
              };
            })
          );
        }
      }
    } catch (err) {
      console.error("Failed to modify thread:", err);
      // optional: toast / error UI
    }
  };


  const sortedThreads = React.useMemo(() => {
    const copy = [...threads];

    copy.sort((a, b) => {
      let av, bv;

      if (sortField === "title") {
        av = (a.title || "").toLowerCase();
        bv = (b.title || "").toLowerCase();
      } else {
        // created_at
        av = new Date(a.created_at).getTime();
        bv = new Date(b.created_at).getTime();
      }

      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

    return copy;
  }, [threads, sortField, sortDir]);

  const activeThreads = sortedThreads.filter(t => !t.is_archived);
  const archivedThreads = sortedThreads.filter(t => t.is_archived);

  const toggleSortField = () => {
    setSortField(prev => (prev === "title" ? "created_at" : "title"));
  };

  const toggleSortDir = () => {
    setSortDir(prev => (prev === "asc" ? "desc" : "asc"));
  };

  return (
    <div className="mt-2 rounded-md border border-neutral-800 bg-neutral-950/95 shadow-lg text-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-800">
        <div className="flex items-center gap-2 text-neutral-300">
          <Split className="w-4 h-4" />
          <span className="font-semibold">Thread Manager</span>
        </div>

        <div className="flex items-center gap-2 text-xs text-neutral-400">
          <button
            type="button"
            onClick={toggleSortField}
            className="inline-flex items-center gap-1 hover:text-neutral-100"
            title="Toggle sort field"
          >
            <ArrowUpDown className="w-3 h-3" />
            <span>{sortField === "title" ? "Title" : "Date"}</span>
          </button>
          <button
            type="button"
            onClick={toggleSortDir}
            className="hover:text-neutral-100"
            title="Toggle sort direction"
          >
            {sortDir === "asc" ? "↑" : "↓"}
          </button>
        </div>
      </div>

      {/* Active threads */}
      <div className="max-h-64 overflow-y-auto">
        {activeThreads.length === 0 ? (
          <div className="px-3 py-2 text-neutral-500 italic">
            No active threads yet.
          </div>
        ) : (
          activeThreads.map(thread => (
            <div
              key={thread.thread_id}
              className="flex items-center justify-between px-3 py-1.5 border-b border-neutral-900/60 hover:bg-neutral-900/40"
            >
              <div className="min-w-0">
                <div className="flex items-start gap-1">
                  {/* Tiny pencil icon to trigger edit */}
                  {editingThreadId !== thread.thread_id && (
                    <button
                      type="button"
                      onClick={e => {
                        e.stopPropagation(); // don’t trigger row click
                        setEditingThreadId(thread.thread_id);
                        setEditingTitle(thread.title || "");
                      }}
                      className="shrink-0 p-0.5 rounded text-neutral-500 hover:text-purple-300 hover:bg-neutral-800"
                      title="Edit title"
                    >
                      <Pencil className="w-3 h-3" />
                    </button>
                  )}
                  <div className="flex-1 min-w-0">
                    {editingThreadId === thread.thread_id ? (
                      <input
                        type="text"
                        autoFocus
                        value={editingTitle}
                        onChange={e => setEditingTitle(e.target.value)}
                        onBlur={() => {
                          const trimmed = editingTitle.trim();
                          handleEditTitle(thread.thread_id, trimmed || null);
                          setEditingThreadId(null);
                          setEditingTitle("");
                        }}
                        onKeyDown={e => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            const trimmed = editingTitle.trim();
                            handleEditTitle(thread.thread_id, trimmed || null);
                            setEditingThreadId(null);
                            setEditingTitle("");
                          } else if (e.key === "Escape") {
                            setEditingThreadId(null);
                            setEditingTitle("");
                          }
                        }}
                        className="w-full rounded bg-neutral-900/80 px-1.5 py-0.5 text-sm text-neutral-100 border border-neutral-700 focus:outline-none focus:ring-1 focus:ring-purple-500"
                      />
                    ) : (
                      <div
                        className="truncate text-neutral-100"
                        title={thread.title || "(untitled thread)"}
                      >
                        {thread.title || "(untitled thread)"}
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-[11px] text-neutral-500">
                  {new Date(thread.created_at).toLocaleString()}
                </div>
              </div>

              <div className="ml-2 flex items-center gap-1 shrink-0">
                {/* Open */}
                <button
                  type="button"
                  onClick={() => handleOpenThread(thread.thread_id)}
                  className="px-1.5 py-0.5 rounded border border-purple-500/60 text-[11px] text-purple-200 hover:bg-purple-500/10"
                  title="Open thread"
                >
                  Open
                </button>

                {/* Hide / unhide */}
                <button
                  type="button"
                  onClick={() => hideThread(thread.thread_id, !thread.is_hidden)}
                  className={`p-1 rounded ${
                    thread.is_hidden
                      ? "text-neutral-500 hover:text-neutral-200"
                      : "text-neutral-400 hover:text-neutral-100"
                  }`}
                  title={thread.is_hidden ? "Unhide thread" : "Hide thread"}
                >
                  {thread.is_hidden ? <EyeOff size={14} className="text-red-400" /> : <Eye size={14} />}

                </button>

                {/* Private toggle */}
                <button
                  type="button"
                  onClick={() => setPrivate(thread.thread_id, !thread.is_private)}
                  className={`p-1 rounded ${
                    thread.is_private
                      ? "text-amber-400 hover:text-amber-300"
                      : "text-neutral-400 hover:text-neutral-100"
                  }`}
                  title={thread.is_private ? "Mark as public" : "Mark as private"}
                >
                  {thread.is_private ? <DoorClosedLocked size={14} className="text-red-400" /> : <DoorClosed size={14} />}
                </button>

                {/* Archive */}
                <button
                  type="button"
                  onClick={() => archiveThread(thread.thread_id, !thread.is_archived)}
                  className="p-1 rounded text-neutral-400 hover:text-neutral-100"
                  title="Archive thread"
                >
                  {thread.is_archived ? <ArchiveRestore size={14} className="text-red-400" /> : <Archive size={14} />}
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Archived section toggle */}
      <button
        type="button"
        onClick={() => setShowArchived(prev => !prev)}
        className="flex w-full items-center justify-between px-3 py-1.5 border-t border-neutral-800 text-xs text-neutral-400 hover:text-neutral-100 hover:bg-neutral-900/60"
      >
        <span>Show archived</span>
        <span>{showArchived ? "▲" : "▼"}</span>
      </button>

      {/* Archived list */}
      {showArchived && (
        <div className="max-h-48 overflow-y-auto border-t border-neutral-900/80">
          {archivedThreads.length === 0 ? (
            <div className="px-3 py-2 text-neutral-500 italic">
              No archived threads.
            </div>
          ) : (
            archivedThreads.map(thread => (
              <div
                key={thread.thread_id}
                className="flex items-center justify-between px-3 py-1.5 border-b border-neutral-900/60 hover:bg-neutral-900/40"
              >
                <div className="min-w-0">
                  <div className="flex items-start gap-1">
                    {/* Tiny pencil icon to trigger edit */}
                    {editingThreadId !== thread.thread_id && (
                      <button
                        type="button"
                        onClick={e => {
                          e.stopPropagation(); // don’t trigger row click
                          setEditingThreadId(thread.thread_id);
                          setEditingTitle(thread.title || "");
                        }}
                        className="shrink-0 p-0.5 rounded text-neutral-500 hover:text-purple-300 hover:bg-neutral-800"
                        title="Edit title"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                    )}
                    <div className="flex-1 min-w-0">
                      {editingThreadId === thread.thread_id ? (
                        <input
                          type="text"
                          autoFocus
                          value={editingTitle}
                          onChange={e => setEditingTitle(e.target.value)}
                          onBlur={() => {
                            const trimmed = editingTitle.trim();
                            handleEditTitle(thread.thread_id, trimmed || null);
                            setEditingThreadId(null);
                            setEditingTitle("");
                          }}
                          onKeyDown={e => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              const trimmed = editingTitle.trim();
                              handleEditTitle(thread.thread_id, trimmed || null);
                              setEditingThreadId(null);
                              setEditingTitle("");
                            } else if (e.key === "Escape") {
                              setEditingThreadId(null);
                              setEditingTitle("");
                            }
                          }}
                          className="w-full rounded bg-neutral-900/80 px-1.5 py-0.5 text-sm text-neutral-100 border border-neutral-700 focus:outline-none focus:ring-1 focus:ring-purple-500"
                        />
                      ) : (
                        <div
                          className="truncate text-neutral-100"
                          title={thread.title || "(untitled thread)"}
                        >
                          {thread.title || "(untitled thread)"}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="text-[11px] text-neutral-500">
                    {new Date(thread.created_at).toLocaleString()}
                  </div>
                </div>

                <div className="ml-2 flex items-center gap-1 shrink-0">
                  {/* Open + unarchive in one */}
                  <button
                    type="button"
                    onClick={() => {
                      archiveThread(thread.thread_id, !thread.is_archived);
                      handleOpenThread(thread.thread_id);
                    }}
                    className="px-1.5 py-0.5 rounded border border-purple-500/60 text-[11px] text-purple-200 hover:bg-purple-500/10"
                    title="Unarchive and open"
                  >
                    Open
                  </button>

                  {/* Unarchive only */}
                  <button
                    type="button"
                    onClick={() => archiveThread(thread.thread_id, !thread.is_archived)}
                    className="p-1 rounded text-neutral-400 hover:text-neutral-100"
                    title="Unarchive"
                  >
                    <ArchiveRestore className="w-3 h-3" />
                  </button>

                  {/* Permanently delete */}
                  <button
                    type="button"
                    onClick={() => setActiveDeleteThreadId(thread.thread_id)}
                    className="p-1 rounded text-red-500 hover:text-red-300"
                    title="Permanently delete"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

          {/* Inline confirmation dialog */}
      {activeDeleteThreadId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-sm rounded-md border border-neutral-800 bg-neutral-950 p-4 shadow-xl">
            <h3 className="text-sm font-semibold text-neutral-100 mb-2">
              Delete thread “{activeThread?.title || "this thread"}”?
            </h3>

            <p className="text-xs text-neutral-400 mb-3">
              Choose what to delete. This action can’t be undone.
            </p>

            <div className="space-y-2 mb-3">
              <label className="flex items-start gap-2 text-xs text-neutral-200">
                <input
                  type="radio"
                  value="thread-only"
                  checked={deleteScope === "thread-only"}
                  onChange={() => setDeleteScope("thread-only")}
                  className="mt-0.5"
                />
                <span>
                  <span className="font-semibold block">
                    Delete thread only
                  </span>
                  <span className="text-neutral-400">
                    Remove this thread from the list. Messages stay in your main history.
                  </span>
                </span>
              </label>

              <label className="flex items-start gap-2 text-xs text-neutral-200">
                <input
                  type="radio"
                  value="thread-and-messages"
                  checked={deleteScope === "thread-and-messages"}
                  onChange={() => setDeleteScope("thread-and-messages")}
                  className="mt-0.5"
                />
                <span>
                  <span className="font-semibold block">
                    Delete thread and hide messages
                  </span>
                  <span className="text-neutral-400">
                    Remove the thread and soft‑delete its messages from history.
                  </span>
                </span>
              </label>
            </div>

            <p className="text-[11px] font-semibold text-red-400 mb-3">
              The thread itself cannot be recovered.
            </p>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={closeDialog}
                className="px-2.5 py-1 rounded border border-neutral-700 text-xs text-neutral-200 hover:bg-neutral-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                className="px-2.5 py-1 rounded bg-red-600 text-xs text-white hover:bg-red-500"
              >
                {deleteScope === "thread-only"
                  ? "Delete thread"
                  : "Delete thread + hide messages"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}