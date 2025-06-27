// ProjectMessages.jsx
"use client";
import { useState, useEffect, useRef, useMemo } from "react";
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/dist/style.css';
import MessageItem from "../components/MessageItem";
import { handleDelete, handleTogglePrivate, handleToggleRemembered } from "../utils/messageActions";
import { setProject, clearProject, addTag, removeTag } from "../utils/messageActions";
// import your export helpers here

const EXPORT_FORMATS = ["txt", "json", "csv", "pdf"]; // you can add/remove formats as you implement
const VIEW_MODES = ["infinite", "byDay"];

export default function ProjectMessages({ project }) {
  // Top bar state
  const [viewMode, setViewMode] = useState("infinite"); // or "byDay"
  const [selectedDate, setSelectedDate] = useState(null);
  const [tagFilter, setTagFilter] = useState([]);
  const [availableTags, setAvailableTags] = useState([]);

  // Message data
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasMoreUp, setHasMoreUp] = useState(true); // for infinite scroll
  const [hasMoreDown, setHasMoreDown] = useState(false); // if you want 2-way scroll
  const [scrollAnchor, setScrollAnchor] = useState(null); // for restoring scroll
  const scrollRef = useRef(null);

  // Load available tags for this project only
  useEffect(() => {
    fetch(`/api/projects/${project._id}/tags`)
      .then(res => res.json())
      .then(data => setAvailableTags(data.tags || []));
  }, [project._id]);

  // Load messages - infinite or by day
  useEffect(() => {
    setLoading(true);
    let url;
    if (viewMode === "byDay" && selectedDate) {
      const dateStr = selectedDate.toISOString().slice(0,10);
      url = `/api/messages/by_day?date=${dateStr}&project_id=${project._id}`;
      // add tags as query if needed
    } else if (viewMode === "infinite") {
      url = `/api/messages?project_id=${project._id}&limit=30`;
      // add tags as query if needed
    }
    if (tagFilter.length > 0) {
      url += tagFilter.map(t => `&tag=${encodeURIComponent(t)}`).join('');
    }
    fetch(url)
      .then(res => res.json())
      .then(data => setMessages(data.messages || []))
      .finally(() => setLoading(false));
  }, [project._id, selectedDate, viewMode, tagFilter]);

  // Message actions (reuse your existing ones)
  const onDelete = (message_id, markDeleted) =>
    handleDelete(setMessages, message_id, markDeleted);
  const onTogglePrivate = (message_id, makePrivate) =>
    handleTogglePrivate(setMessages, message_id, makePrivate);
  const onToggleRemembered = (message_id, makeRemembered) =>
    handleToggleRemembered(setMessages, message_id, makeRemembered);
  const onSetProject = (message_id, project_id) =>
    setProject(setMessages, message_id, project_id);
  const onClearProject = (message_id) =>
    clearProject(setMessages, message_id);
  const onAddTag = (message_id, tag) =>
    addTag(setMessages, message_id, tag);
  const onRemoveTag = (message_id, tag) =>
    removeTag(setMessages, message_id, tag);

  // Export logic
  function handleExport(format) {
    // Implement export logic: use messages, project, etc.
    // Example: exportMessages(messages, format)
  }

  // Filtered messages (if tag filter applied)
  const filteredMessages =
    tagFilter.length === 0
      ? messages
      : messages.filter(msg =>
          (msg.user_tags || []).some(tag => tagFilter.includes(tag))
        );

  // Scroll: scroll to bottom on load (unless user has scrolled up)
  useEffect(() => {
    if (scrollRef.current && viewMode === "infinite") {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, viewMode]);

  return (
    <div className="flex flex-col h-full">
      {/* Top bar: filters, export, view mode */}
      <div className="sticky top-0 z-10 bg-neutral-950 border-b border-neutral-800 p-2 flex flex-col md:flex-row gap-4 items-center">
        <div className="flex gap-2 items-center">
          <span className="text-sm">View:</span>
          <select value={viewMode} onChange={e => setViewMode(e.target.value)}>
            <option value="infinite">Infinite Scroll</option>
            <option value="byDay">By Day</option>
          </select>
        </div>
        {viewMode === "byDay" && (
          <div>
            <DayPicker
              mode="single"
              selected={selectedDate}
              onSelect={setSelectedDate}
              // Add any modifiers if you wish
            />
          </div>
        )}
        <div className="flex gap-2 items-center">
          <span className="text-sm">Tags:</span>
          {availableTags.map(tag => (
            <button
              key={tag}
              className={`px-2 py-1 rounded-full text-xs
                ${tagFilter.includes(tag)
                  ? "bg-purple-700 text-white"
                  : "bg-neutral-800 text-purple-200 hover:bg-purple-800"}
              `}
              onClick={() => setTagFilter(tf =>
                tf.includes(tag) ? tf.filter(t => t !== tag) : [...tf, tag]
              )}
            >#{tag}</button>
          ))}
        </div>
        <div className="ml-auto flex gap-2 items-center">
          <span className="text-sm">Export:</span>
          {EXPORT_FORMATS.map(fmt => (
            <button
              key={fmt}
              onClick={() => handleExport(fmt)}
              className="px-2 py-1 bg-purple-800 text-white rounded hover:bg-purple-900"
            >
              {fmt.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
      {/* Message list */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-2 bg-neutral-900"
        style={{ minHeight: 300 }}
        // Add onScroll handler for infinite scroll up/down if needed
      >
        {loading && (
          <div className="text-neutral-400 text-center py-6">Loading...</div>
        )}
        {!loading && filteredMessages.length === 0 && (
          <div className="text-neutral-500 italic text-center py-6">
            &lt;No messages found for this filter.&gt;
          </div>
        )}
        {filteredMessages.map((msg, idx) => (
          <MessageItem
            key={msg.message_id || idx}
            msg={msg}
            // Pass the rest of your props/actions here...
            onDelete={onDelete}
            onTogglePrivate={onTogglePrivate}
            onToggleRemembered={onToggleRemembered}
            onSetProject={onSetProject}
            onClearProject={onClearProject}
            onAddTag={onAddTag}
            onRemoveTag={onRemoveTag}
          />
        ))}
      </div>
    </div>
  );
}