"use client";

import { useState, useEffect } from "react";
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/dist/style.css';
import { Eye, EyeOff, EyeClosed, Tags, Shredder, SquareX, BookMarked } from 'lucide-react';
import { useConfig } from '@/hooks/ConfigContext';
import { useMemo } from "react";
import MessageItem from "@/components/app/MessageItem";
import { handleDelete, handleTogglePrivate, handleToggleHidden, handleToggleRemembered } from "@/utils/messageActions";
import { setProject, clearProject, addTag, removeTag } from "@/utils/messageActions";


const SOURCE_CHOICES = [
  { key: "frontend", label: "Frontend" },
  { key: "chatgpt", label: "ChatGPT" },
  { key: "discord", label: "Discord" }
];


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

const HistoryTab = ({
    onReturnToThisMoment
  }) => {
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
  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectDialogOpen, setProjectDialogOpen] = useState(null)
  const [tagsExpanded, setTagsExpanded] = useState(false);
  const hasTags = availableTags.length > 0;
  const { museProfile, museProfileLoading } = useConfig();

  const museName = museProfile?.name?.[0]?.content ?? "Muse";
  const mode = "history";
    // "Bind" each handler to local state
  const onDelete = (message_id, markDeleted) =>
    handleDelete(setMessages, message_id, markDeleted);

  const onTogglePrivate = (message_id, makePrivate) =>
    handleTogglePrivate(setMessages, message_id, makePrivate);

  const onToggleHidden = (message_id, makeHidden) =>
    handleToggleHidden(setMessages, message_id, makeHidden);

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

    useEffect(() => {
      fetch("/api/projects")
        .then(res => res.json())
        .then(data => {
          setProjects(data.projects || []);
          setProjectsLoading(false);
        });
    }, []);

    // Build a map for fast lookup
    const projectMap = useMemo(() => {
      const map = {};
      for (const proj of projects) {
        map[proj._id] = proj;
      }
      return map;
    }, [projects]);



  return (
    <div className="p-6 text-white bg-neutral-950 overflow-y-auto" style={{ maxHeight: "calc(100vh - 92px - 48px)" }}>
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
        <div className="mb-2">
          {/* Label always visible at the top */}
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-neutral-300">Filter by tag:</span>
          </div>

          {/* Tag chips in a capped-height container */}
          <div
            className={`overflow-hidden transition-[max-height] duration-200 ${
              tagsExpanded ? "max-h-none" : "max-h-14"
            }`}
          >
            <div className="flex flex-wrap gap-2 items-center">
              {availableTags.map(tagObj => (
                <button
                  key={tagObj.tag}
                  className={`px-3 py-1 rounded-full text-xs transition-all
                    ${
                      tagFilter.includes(tagObj.tag)
                        ? "bg-purple-700 text-white font-semibold shadow"
                        : "bg-neutral-800 text-purple-200 hover:bg-purple-800"
                    }
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
                  className="px-2 py-1 bg-neutral-700 text-purple-200 rounded hover:bg-neutral-600 text-xs"
                  onClick={() => setTagFilter([])}
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Full-width rail with centered chevron */}
          {hasTags && (
            <div className="mt-1 flex items-center justify-center w-full">
              <div className="h-px flex-1 bg-neutral-800" />
              <button
                type="button"
                onClick={() => setTagsExpanded(v => !v)}
                className="mx-2 flex items-center justify-center h-5 w-5 rounded-full
                           bg-neutral-800 text-neutral-300 hover:bg-neutral-700
                           hover:text-purple-200 text-xs border border-neutral-700"
                title={tagsExpanded ? "Collapse tags" : "Show all tags"}
              >
                {tagsExpanded ? "▲" : "▼"}
              </button>
              <div className="h-px flex-1 bg-neutral-800" />
            </div>
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
                return (
                  <MessageItem
                    key={msg.message_id || idx}
                    msg={msg}
                    projects={projects}
                    projectsLoading={projectsLoading}
                    projectMap={projectMap}
                    tagDialogOpen={tagDialogOpen}
                    setTagDialogOpen={setTagDialogOpen}
                    projectDialogOpen={projectDialogOpen}
                    setProjectDialogOpen={setProjectDialogOpen}
                    museName={museName}
                    onDelete={onDelete}
                    onTogglePrivate={onTogglePrivate}
                    onToggleHidden={onToggleHidden}
                    onToggleRemembered={onToggleRemembered}
                    onSetProject={onSetProject}
                    onClearProject={onClearProject}
                    onAddTag={onAddTag}
                    onRemoveTag={onRemoveTag}
                    mode={mode}
                    onReturnToThisMoment={onReturnToThisMoment}
                  />
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
