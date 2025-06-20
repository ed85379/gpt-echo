"use client";

import { useState, useEffect } from "react";
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/dist/style.css';
import { Remarkable } from 'remarkable';
import { linkify } from 'remarkable/linkify';
import { Eye, EyeOff, EyeClosed, Tags, Shredder, SquareX } from 'lucide-react';
import { useConfig } from '../hooks/ConfigContext';

const md = new Remarkable({
  html: false,
  breaks: true,
  linkTarget: "_blank",
  typographer: true,
});
md.use(linkify);

export function CandleHolderLit(props) {
  return (
    <svg
        xmlns="http://www.w3.org/2000/svg"
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

const SOURCE_CHOICES = [
  { key: "frontend", label: "Frontend" },
  { key: "chatgpt", label: "ChatGPT" },
  { key: "discord", label: "Discord" }
];

const formatTimestamp = (utcString) => {
  if (!utcString) return "";
  const dt = new Date(utcString);
  return dt.toLocaleString();
};

function getMonthRange(date) {
  // Current month and year
  const year = date.getUTCFullYear();
  const month = date.getUTCMonth();

  // Previous month (handle January rollover)
  const prevMonth = month === 0 ? 11 : month - 1;
  const prevYear = month === 0 ? year - 1 : year;

  // Start: first of previous month
  const start = `${prevYear}-${String(prevMonth + 1).padStart(2, '0')}-01`;

  // End: last of current month
  const firstOfNextMonth = new Date(Date.UTC(year, month + 1, 1));
  const lastOfMonth = new Date(firstOfNextMonth.getTime() - 24 * 3600 * 1000);
  const end = `${lastOfMonth.getUTCFullYear()}-${String(lastOfMonth.getUTCMonth() + 1).padStart(2, '0')}-${String(lastOfMonth.getUTCDate()).padStart(2, '0')}`;

  return { start, end };
}

const HistoryTab = () => {
  const [source, setSource] = useState("Frontend");
  const [calendarStatus, setCalendarStatus] = useState({});
  const [selectedDate, setSelectedDate] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [displayMonth, setDisplayMonth] = useState(new Date());
  const [tagDialogOpen, setTagDialogOpen] = useState(null);
  const [newTag, setNewTag] = useState("");
  const [availableTags, setAvailableTags] = useState([]);
  const [tagFilter, setTagFilter] = useState([]);
  const { museProfile, museProfileLoading } = useConfig();
  const museName = museProfile?.name?.[0]?.content ?? "Muse";

  const filteredMessages =
    tagFilter.length === 0
      ? messages
      : messages.filter(msg =>
          (msg.user_tags || []).some(tag => tagFilter.includes(tag))
        );

  useEffect(() => {
    setCalendarStatus({});
    const { start, end } = getMonthRange(displayMonth);

    let params = `source=${encodeURIComponent(source)}&start=${start}&end=${end}`;
    tagFilter.forEach(t => {
      params += `&tag=${encodeURIComponent(t)}`;
    });

    fetch(`/api/messages/calendar_status_simple?${params}`)
      .then(res => res.json())
      .then(data => {
        setCalendarStatus(data.days || {});
      });
  }, [source, displayMonth, tagFilter]);


  useEffect(() => {
    fetch("/api/messages/user_tags")
      .then(res => res.json())
      .then(data => setAvailableTags(data.tags || []));
  }, []);

  useEffect(() => {
    setMessages([]);
    if (!selectedDate) return;
    setLoading(true);
    const dateStr = selectedDate.toISOString().slice(0,10);
    fetch(`/api/messages/by_day?date=${dateStr}&source=${encodeURIComponent(source)}`)
      .then(res => res.json())
      .then(data => setMessages(data.messages || []))
      .finally(() => setLoading(false));
  }, [selectedDate, source]);

  function handleDelete(message_id, markDeleted) {
    fetch("/api/messages/tag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_ids: [message_id], is_deleted: markDeleted })
    })
    .then(() => {
      setMessages(prev =>
        prev.map(m =>
          m.message_id === message_id ? { ...m, is_deleted: markDeleted } : m
        )
      );
    });
  }

  function handleTogglePrivate(message_id, makePrivate) {
    fetch("/api/messages/tag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_ids: [message_id], is_private: makePrivate })
    })
    .then(() => {
      setMessages(prev =>
        prev.map(m =>
          m.message_id === message_id ? { ...m, is_private: makePrivate } : m
        )
      );
    });
  }

    function handleToggleRemembered(message_id, makeRemembered) {
    fetch("/api/messages/tag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_ids: [message_id], remembered: makeRemembered })
    })
    .then(() => {
      setMessages(prev =>
        prev.map(m =>
          m.message_id === message_id ? { ...m, remembered: makeRemembered } : m
        )
      );
    });
  }

  function addTag(message_id, tag) {
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

  function removeTag(message_id, tag) {
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

  return (
<div className="p-6 text-white bg-neutral-950 overflow-y-auto"
     style={{ maxHeight: "calc(100vh - 92px - 48px)" }}>
  <div className="flex items-center gap-6 mb-4">
        <label className="text-sm text-neutral-300">
          Source:
          <select
            value={source}
            onChange={e => setSource(e.target.value)}
            className="ml-2 px-2 py-1 rounded bg-neutral-900 text-white border border-neutral-700"
          >
            {SOURCE_CHOICES.map(opt =>
              <option key={opt.key} value={opt.key}>{opt.label}</option>
            )}
          </select>
        </label>
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-sm text-neutral-300">Filter by tag:</span>
          {availableTags.map(tagObj => (
            <button
              key={tagObj.tag}
              className={`px-3 py-1 rounded-full text-xs transition-all
                ${tagFilter.includes(tagObj.tag)
                  ? "bg-purple-700 text-white font-semibold shadow"
                  : "bg-neutral-800 text-purple-200 hover:bg-purple-800"}
              `}
              onClick={() => {
                setTagFilter(tf =>
                  tf.includes(tagObj.tag)
                    ? tf.filter(t => t !== tagObj.tag)
                    : [...tf, tagObj.tag]
                );
              }}
            >
              #{tagObj.tag}
              <span className="ml-1 text-neutral-400">{tagObj.count}</span>
            </button>
          ))}
          {tagFilter.length > 0 && (
            <button
              className="ml-2 px-2 py-1 bg-neutral-700 text-purple-200 rounded hover:bg-neutral-600"
              onClick={() => setTagFilter([])}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="flex gap-6 mt-4 flex-col md:flex-row">
        {/* Calendar */}
        <div className="w-full md:w-1/4 mb-6 md:mb-0">
          <DayPicker
            mode="single"
            month={displayMonth}
            onMonthChange={setDisplayMonth}
            selected={selectedDate}
            onSelect={setSelectedDate}
            modifiers={{
              hasMessages: day => {
                const d = day.toISOString().slice(0,10);
                return !!calendarStatus[d];
              }
            }}
            modifiersClassNames={{
              hasMessages: "bg-purple-800/70 text-white font-bold"
            }}
          />
        </div>

        {/* Log viewer */}
        <div className="w-full md:w-3/4 space-y-2 bg-neutral-900 p-4 rounded-lg border border-neutral-700 min-h-[300px]">
          {!selectedDate && (
            <div className="w-full h-64 text-neutral-500 text-sm font-mono flex items-center justify-center">
              &lt;Select a date to view conversation log&gt;
            </div>
          )}
          {loading && (
            <div className="w-full h-24 text-neutral-400 text-center flex items-center justify-center">
              Loading...
            </div>
          )}
          {!loading && selectedDate && messages.length === 0 && (
            <div className="w-full h-64 text-neutral-500 text-sm font-mono flex items-center justify-center">
              &lt;No messages found for this day.&gt;
            </div>
          )}
          {messages.length > 0 && (
            <div className="space-y-2">
                {filteredMessages.map((msg, idx) => {
                  let renderedHTML = "";
                  try {
                    renderedHTML = md.render((msg.message || msg.text || "").trim());
                  } catch (e) {
                    renderedHTML = "<em>[Failed to render markdown]</em>";
                    console.error("Remarkable error:", e, msg.message || msg.text);
                  }

                  // Role and display name logic
                  const effectiveRole = msg.from || msg.role || "";

                  let displayName = "Other";
                  let bubbleClass = "bg-purple-900 text-white self-start text-left"; // Default

                  if (effectiveRole === "user") {
                    displayName = "You";
                    bubbleClass = "bg-neutral-800 text-purple-100 self-end text-left";
                  } else if (effectiveRole === "muse" || effectiveRole === "iris") {
                    displayName = museName;
                    bubbleClass = "bg-purple-950 text-white self-start text-left";
                  } else if (effectiveRole === "other" || effectiveRole === "friend") {
                    displayName = msg.username ? msg.username : "Friend";
                    bubbleClass = "bg-neutral-700 text-white self-start text-left";
                  } else if (effectiveRole) {
                    displayName = effectiveRole.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
                    bubbleClass = "bg-purple-900 text-white self-start text-left";
                  }

                  // Alignment and tag logic
                  const rightAlign = effectiveRole === "user";
                  const isPrivate = !!msg.is_private;
                  const isRemembered = !!msg.remembered;
                  const isDeleted = !!msg.is_deleted;
                  const userTags = msg.user_tags?.filter(t => t !== "private" && t !== "deleted" && t !== "remembered") || [];
                  const bubbleWidth = "max-w-[80%]";

                  return (
                    <div
                      key={idx}
                      className={`space-y-1 flex flex-col ${rightAlign ? "items-end" : "items-start"}`}
                    >
                      <div className={`${bubbleWidth} ${rightAlign ? "ml-auto" : ""}`}>
                        <div className="text-xs text-neutral-400">{displayName}</div>
                        <div className="text-xs text-neutral-500">{formatTimestamp(msg.timestamp)}</div>
                        <div
                          className={`relative group text-sm px-3 py-2 rounded-lg whitespace-pre-wrap ${bubbleClass}`}
                        >
                          <div
                            className="prose prose-invert max-w-none"
                            dangerouslySetInnerHTML={{ __html: renderedHTML }}
                          />

                          {/* Tagging bar (appears on hover) */}
                        <div className="absolute bottom-2 right-3 hidden group-hover:flex gap-2 z-10">
                          {!isDeleted && (
                            <>
                              <button
                                onClick={() => setTagDialogOpen(msg.message_id)}
                                title="Tag message"
                                className="text-neutral-400 hover:text-purple-300 transition-colors"
                                style={{ background: "none", border: "none", cursor: "pointer" }}
                              >
                                <Tags size={18} />
                              </button>
                              <button
                                onClick={() => handleToggleRemembered(msg.message_id, !isRemembered)}
                                title={isRemembered ? "Let memory fade" : "Mark as strong memory"}
                                className={`transition-colors ${isRemembered ? "text-purple-400" : "text-neutral-400"} hover:text-purple-300`}
                                style={{ background: "none", border: "none", cursor: "pointer" }}
                              >
                                <CandleHolderLit
                                      className={`transition-colors ${isRemembered ? "text-purple-400" : "text-neutral-400"} hover:text-purple-300`}

                                    />
                              </button>
                              <button
                                onClick={() => handleTogglePrivate(msg.message_id, !isPrivate)}
                                title={isPrivate ? "Set as public" : "Mark as private"}
                                className={`transition-colors ${isPrivate ? "text-purple-400" : "text-neutral-400"} hover:text-purple-300`}
                                style={{ background: "none", border: "none", cursor: "pointer" }}
                              >
                                {isPrivate ? <EyeClosed size={18} /> : <Eye size={18} />}
                              </button>
                              <button
                                onClick={() => handleDelete(msg.message_id, true)}
                                title="Delete message"
                                className="text-neutral-400 hover:text-red-400 transition-colors"
                                style={{ background: "none", border: "none", cursor: "pointer" }}
                              >
                                <Shredder size={18} />
                              </button>
                            </>
                          )}
                          {isDeleted && (
                            <button
                              onClick={() => handleDelete(msg.message_id, false)}
                              title="Undelete message"
                              className="text-neutral-400 hover:text-purple-300 transition-colors"
                              style={{ background: "none", border: "none", cursor: "pointer" }}
                            >
                              <SquareX size={18} />
                            </button>
                          )}
                        </div>

                    {tagDialogOpen === msg.message_id && (
                      <div className="absolute z-20 right-10 bottom-2 bg-neutral-900 p-4 rounded-lg shadow-lg w-64">
                        <div className="mb-2 font-semibold text-purple-100">Edit Tags</div>
                        {/* List current tags */}
                        <div className="flex flex-wrap gap-1 mb-2">
                          {(msg.user_tags || []).map(tag => (
                            <span
                              key={tag}
                              className="bg-purple-800 text-xs text-purple-100 px-2 py-0.5 rounded-full flex items-center"
                            >
                              {tag}
                              <button
                                className="ml-1 text-purple-300 hover:text-red-300"
                                onClick={() => removeTag(msg.message_id, tag)}
                              >×</button>
                            </span>
                          ))}
                        </div>
                        {/* Add new tag */}
                        <div className="flex">
                          <input
                            type="text"
                            className="flex-1 rounded px-2 py-1 text-sm bg-neutral-800 text-white border-none outline-none"
                            value={newTag}
                            onChange={e => setNewTag(e.target.value)}
                            placeholder="Add tag..."
                            onKeyDown={e => {
                              if (e.key === "Enter" && newTag.trim()) {
                                addTag(msg.message_id, newTag.trim());
                                setNewTag("");
                              }
                            }}
                          />
                          <button
                            className="ml-2 text-purple-300 hover:text-purple-100"
                            onClick={() => {
                              if (newTag.trim()) {
                                addTag(msg.message_id, newTag.trim());
                                setNewTag("");
                              }
                            }}
                          >Add</button>
                        </div>
                        {/* Close button */}
                        <button
                          className="absolute top-1 right-2 text-xs text-neutral-500 hover:text-purple-200"
                          onClick={() => setTagDialogOpen(null)}
                        >✕</button>
                      </div>
                    )}
                        </div>
                        {/* Tags */}
                        <div className="flex flex-wrap gap-1 mt-1 ml-2">
                          {userTags.map(tag => (
                            <span key={tag} className="bg-purple-800 text-xs text-purple-100 px-2 py-0.5 rounded-full">
                              #{tag}
                            </span>
                          ))}
                          {isRemembered && (
                            <span className="bg-neutral-700 text-xs text-purple-300 px-2 py-0.5 rounded-full flex items-center gap-1">
                              <CandleHolderLit size={14} className="inline" /> Remembered
                            </span>
                          )}
                          {isPrivate && (
                            <span className="bg-neutral-700 text-xs text-purple-300 px-2 py-0.5 rounded-full flex items-center gap-1">
                              <EyeOff size={14} className="inline" /> Private
                            </span>
                          )}
                          {isDeleted && (
                            <span className="bg-neutral-700 text-xs text-purple-300 px-2 py-0.5 rounded-full flex items-center gap-1">
                              <Shredder size={14} className="inline" /> Recycled
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}


            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryTab;
