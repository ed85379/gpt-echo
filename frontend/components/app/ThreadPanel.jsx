// components/app/ThreadPanel.jsx
import React, { useMemo, useState } from "react";

export default function ThreadPanel({
  mode,
  msg_ids,
  threads,
  memberThreadIds,
  onCreateThread,
  onJoinThread,
  onLeaveThread,
  clearSelectionAndExit,
  onCancel,
}) {
  const [newTitle, setNewTitle] = useState("");
  const [joinThreadId, setJoinThreadId] = useState("");
  const [leaveThreadId, setLeaveThreadId] = useState("");

  const primaryMsgId = msg_ids?.[0] || null;

  const { joinableThreads, memberThreads, defaultTitle } = useMemo(() => {
    const memberSet = new Set(memberThreadIds);

    const nonArchived = threads.filter(t => !t.is_archived);
    const joinable = nonArchived.filter(t => !memberSet.has(t.thread_id));
    const member = threads.filter(t => memberSet.has(t.thread_id));

    const now = new Date();
    const pad = n => String(n).padStart(2, "0");
    const defaultTitleStr = `Thread - ${now.getFullYear()}-${pad(
      now.getMonth() + 1
    )}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(
      now.getMinutes()
    )}`;


    return {
      joinableThreads: joinable,
      memberThreads: member,
      defaultTitle: defaultTitleStr,
    };
  }, [threads, memberThreadIds]);

  const handleCreate = () => {
    console.log("DEBUG msg_ids", msg_ids)
    if (!msg_ids?.length) return;
    const title = newTitle.trim() || null;
    onCreateThread && onCreateThread(msg_ids, title);
    clearSelectionAndExit();
  };

  const handleJoin = () => {
    if (!joinThreadId || !msg_ids?.length) return;
    onJoinThread && onJoinThread(msg_ids, joinThreadId);
    clearSelectionAndExit();
  };

  const handleLeave = () => {
    if (!leaveThreadId || !msg_ids?.length) return;
    onLeaveThread && onLeaveThread(msg_ids, leaveThreadId);
    clearSelectionAndExit();
  };

  return (
    <div className="w-[420px] bg-neutral-900 border border-neutral-700 rounded p-3 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <span className="text-sm text-neutral-200">Manage threads for message</span>
        <button
          className="px-2 py-1 text-xs rounded border border-neutral-600 text-neutral-300"
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
      { (mode === 'add' || mode === 'single') && (
        <div className="mb-3 border-b border-neutral-700 pb-3">
          <div className="text-xs text-neutral-400 mb-1">
            Create a new thread (title optional)
          </div>
          <div className="flex items-center gap-2">
            <input
              className="flex-1 bg-neutral-800 text-sm text-neutral-100 border border-neutral-600 rounded px-2 py-1"
              placeholder={defaultTitle}
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
            />
            <button
              className="px-2 py-1 text-sm rounded bg-purple-600 text-white"
              onClick={handleCreate}
            >
              Create
            </button>
          </div>
        </div>
      )}

      { (mode === 'add' || mode === 'single') && (
        <div className="mb-3">
          <div className="text-xs text-neutral-400 mb-1">
            Join an existing thread
          </div>
          <div className="flex items-center gap-2">
            <select
              className="flex-1 bg-neutral-800 text-sm text-neutral-100 border border-neutral-600 rounded px-2 py-1"
              value={joinThreadId}
              onChange={e => setJoinThreadId(e.target.value)}
            >
              <option value="">
                {joinableThreads.length === 0
                  ? "No other threads available"
                  : "Select thread to join"}
              </option>
              {joinableThreads.map(t => {
                const id = t.thread_id;
                return (
                  <option key={id} value={id}>
                    {t.title}
                  </option>
                );
              })}
            </select>

            <button
              className="px-2 py-1 text-sm rounded bg-purple-600 text-white disabled:opacity-40"
              onClick={handleJoin}
              disabled={!joinThreadId}
            >
              Join
            </button>
          </div>
        </div>
      )}

      { (mode === 'remove' || mode === 'single') && (
        <div>
          <div className="text-xs text-neutral-400 mb-1">
            Leave a thread this message is in
          </div>
          <div className="flex items-center gap-2">
            <select
              className="flex-1 bg-neutral-800 text-sm text-neutral-100 border border-neutral-600 rounded px-2 py-1"
              value={leaveThreadId}
              onChange={e => setLeaveThreadId(e.target.value)}
            >
              <option value="">
                {memberThreads.length === 0
                  ? "Not in any threads"
                  : "Select thread to leave"}
              </option>
              {memberThreads.map(t => {
                const id = t.thread_id;
                return (
                  <option key={id} value={id}>
                    {t.title}
                  </option>
                );
              })}
            </select>

            <button
              className="px-2 py-1 text-sm rounded bg-red-700 text-white disabled:opacity-40"
              onClick={handleLeave}
              disabled={!leaveThreadId}
            >
              Leave
            </button>
          </div>
        </div>
      )}
    </div>
  );
}