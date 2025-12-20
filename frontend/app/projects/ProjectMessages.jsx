// ProjectMessages.jsx
"use client";
import React, { useState, useEffect, useRef } from "react";
import { Virtuoso } from "react-virtuoso";
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/dist/style.css';
import MessageItem from "@/components/app/MessageItem";
import { handleDelete, handleTogglePrivate, handleToggleHidden, handleToggleRemembered } from "@/utils/messageActions";
import { setProject, clearProject, addTag, removeTag } from "@/utils/messageActions";
import { ChevronDownIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"


const EXPORT_FORMATS = ["txt", "json", "csv", "pdf"];
const VIEW_MODES = ["infinite", "byDay"];

// --- VIRTUOSO WINDOW SIZE ---
const PAGE_SIZE = 30; // How many to fetch per page


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


export default function ProjectMessages({ project, projectMap, projects, projectsLoading }) {
  // UI state
  const [open, setOpen] = React.useState(false)
  const [viewMode, setViewMode] = useState("byDay");
  const [selectedDate, setSelectedDate] = useState(null);
  const [tagFilter, setTagFilter] = useState([]);
  const [availableTags, setAvailableTags] = useState([]);
  const [tagDialogOpen, setTagDialogOpen] = useState(null);
  const [projectDialogOpen, setProjectDialogOpen] = useState(null);
  const [displayMonth, setDisplayMonth] = useState(new Date());
  const [calendarStatus, setCalendarStatus] = useState({});
  // Message data
  const [messages, setMessages] = useState([]); // always sorted oldest → newest
  const [loading, setLoading] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [loadingNewer, setLoadingNewer] = useState(false);
  const [atStart, setAtStart] = useState(false);
  const [atEnd, setAtEnd] = useState(false);

  // Used to force Virtuoso to scroll to bottom/top on filter/view change
  const virtuosoRef = useRef(null);

  // --- Fetch available tags for this project ---
  useEffect(() => {
    fetch(`/api/projects/${project._id}/tags`)
      .then(res => res.json())
      .then(data => setAvailableTags(data.tags || []));
  }, [project._id]);

  // --- Initial load or filter change ---
  useEffect(() => {
    setLoading(true);
    let url;
    if (viewMode === "byDay" && selectedDate) {
      const dateStr = selectedDate.toISOString().slice(0,10);
      url = `/api/messages/by_day?date=${dateStr}&project_id=${project._id}`;
    } else if (viewMode === "infinite") {
      url = `/api/messages?project_id=${project._id}&limit=${PAGE_SIZE}`;
    }
    if (tagFilter.length > 0) {
      url += tagFilter.map(t => `&tag=${encodeURIComponent(t)}`).join('');
    }
    fetch(url)
      .then(res => res.json())
      .then(data => {
        setMessages(data.messages || []);
        setAtStart(false);
        setAtEnd(false);
        // After reload, scroll to bottom (latest message)
        if (virtuosoRef.current) {
          // Virtuoso will scroll to bottom if we set initialTopMostItemIndex
          virtuosoRef.current.scrollToIndex({ index: (data.messages?.length || 1) - 1, align: "end", behavior: "auto" });
        }
      })
      .finally(() => setLoading(false));
  }, [project._id, selectedDate, viewMode, tagFilter]);

  // --- Message actions (reuse your existing ones) ---
  const onDelete = (message_id, markDeleted) => handleDelete(setMessages, message_id, markDeleted);
  const onTogglePrivate = (message_id, makePrivate) => handleTogglePrivate(setMessages, message_id, makePrivate);
  const onToggleHidden = (message_id, makeHidden) => handleToggleHidden(setMessages, message_id, makeHidden);
  const onToggleRemembered = (message_id, makeRemembered) => handleToggleRemembered(setMessages, message_id, makeRemembered);
  const onSetProject = (message_id, project_id) => setProject(setMessages, message_id, project_id);
  const onClearProject = (message_id) => clearProject(setMessages, message_id);
  const onAddTag = (message_id, tag) => addTag(setMessages, message_id, tag);
  const onRemoveTag = (message_id, tag) => removeTag(setMessages, message_id, tag);

  // --- Infinite scroll: load older/newer logic ---
  const loadOlderMessages = async () => {
      console.log("loading older")
    if (loadingOlder || atStart || messages.length === 0) return;
    setLoadingOlder(true);
    const oldest = messages[0];
    let url = `/api/messages?project_id=${project._id}&limit=${PAGE_SIZE}&before=${encodeURIComponent(oldest.timestamp || oldest.created_at || oldest._id)}`;
    if (tagFilter.length > 0) {
      url += tagFilter.map(t => `&tag=${encodeURIComponent(t)}`).join('');
    }
    const res = await fetch(url);
    const data = await res.json();
    if (!data.messages || data.messages.length === 0) setAtStart(true);
    setMessages(prev => [...(data.messages || []), ...prev]);
    setLoadingOlder(false);
  };

  const loadNewerMessages = async () => {
    if (loadingNewer || atEnd || messages.length === 0) return;
    setLoadingNewer(true);
    const newest = messages[messages.length - 1];
    let url = `/api/messages?project_id=${project._id}&limit=${PAGE_SIZE}&after=${encodeURIComponent(newest.timestamp || newest.created_at || newest._id)}`;
    if (tagFilter.length > 0) {
      url += tagFilter.map(t => `&tag=${encodeURIComponent(t)}`).join('');
    }
    const res = await fetch(url);
    const data = await res.json();
    if (!data.messages || data.messages.length === 0) setAtEnd(true);
    setMessages(prev => [...prev, ...(data.messages || [])]);
    setLoadingNewer(false);
  };

  // --- Export logic placeholder ---
  function handleExport(format) {
    // Implement export logic: use messages, project, etc.
  }

  // --- Filtering ---
  const filteredMessages = tagFilter.length === 0
    ? messages
    : messages.filter(msg =>
        (msg.user_tags || []).some(tag => tagFilter.includes(tag))
      );

  useEffect(() => {
    setCalendarStatus({});
    const { start, end } = getMonthRange(displayMonth);

    let params = `project_id=${encodeURIComponent(project._id)}&start=${start}&end=${end}`;
    tagFilter.forEach(t => {
      params += `&tag=${encodeURIComponent(t)}`;
    });

    fetch(`/api/messages/calendar_status_simple?${params}`)
      .then(res => res.json())
      .then(data => {
        setCalendarStatus(data.days || {});
      });
  }, [project, displayMonth, tagFilter]);


  return (
    <div className="flex flex-col h-full">
      {/* Top bar: filters, export, view mode */}
      <div className="sticky top-0 z-10 bg-neutral-950 border-b border-neutral-800 p-2 flex flex-col md:flex-row gap-4 items-start">
        <div className="flex gap-2 items-center">
{/*          <span className="text-sm">View:</span>
          <select value={viewMode} onChange={e => setViewMode(e.target.value)}>
            <option value="infinite">Infinite Scroll</option>
            <option value="byDay">By Day</option>
          </select>
*/}
        </div>
        {viewMode === "byDay" && (
          <div>
            <Label htmlFor="date" className="px-1">
            Select Day
            </Label>
              <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    id="date"
                    className="w-36 justify-between font-normal"
                  >
                    {selectedDate ? selectedDate.toLocaleDateString() : "Select date"}
                    <ChevronDownIcon />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto overflow-hidden p-0" align="start">
                    <DayPicker
                      mode="single"
                      selected={selectedDate}
                      onSelect={setSelectedDate}
                        classNames={{
                        months: "bg-neutral-900 text-neutral-100 rounded-lg shadow p-2",
                        caption_label: "text-purple-300 font-semibold",
                        day_selected: "bg-purple-700 text-white",
                        day: "hover:bg-purple-800/60"
                        }}
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
                            </PopoverContent>
              </Popover>
          </div>
        )}
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-sm">Tags:</span>
          {availableTags.map(tag => (
            <button
              key={tag.tag}
              className={`px-2 py-1 rounded-full text-xs
                ${tagFilter.includes(tag.tag)
                  ? "bg-purple-700 text-white"
                  : "bg-neutral-800 text-purple-200 hover:bg-purple-800"}
              `}
              onClick={() => setTagFilter(tf =>
                tf.includes(tag.tag) ? tf.filter(t => t !== tag.tag) : [...tf, tag.tag]
              )}
            >#{tag.tag}
            <span className="ml-1 text-neutral-400">{tag.count}</span>
            </button>
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

      {/* Message list: Virtuoso does all the scrolling magic! */}
      <div className="flex-1 min-h-[300px] bg-neutral-900">
        {loading && (
          <div className="text-neutral-400 text-center py-6">Loading...</div>
        )}
        {!loading && filteredMessages.length === 0 && (
          <div className="text-neutral-500 italic text-center py-6">
            &lt;No messages found for this filter.&gt;
          </div>
        )}
        {!loading && filteredMessages.length > 0 && (
            <Virtuoso
              style={{ height: 400, width: "100%" }}
              initialTopMostItemIndex={filteredMessages.length - 1}
              data={filteredMessages}
              itemContent={(index, msg) => (
                <MessageItem
                  key={msg.message_id || index}
                  msg={msg}
                  projectMap={projectMap}
                  projects={projects}
                  projectsLoading={projectsLoading}
                  tagDialogOpen={tagDialogOpen}
                  setTagDialogOpen={setTagDialogOpen}
                  projectDialogOpen={projectDialogOpen}
                  setProjectDialogOpen={setProjectDialogOpen}
                  onDelete={onDelete}
                  onTogglePrivate={onTogglePrivate}
                  onToggleHidden={onToggleHidden}
                  onToggleRemembered={onToggleRemembered}
                  onSetProject={onSetProject}
                  onClearProject={onClearProject}
                  onAddTag={onAddTag}
                  onRemoveTag={onRemoveTag}
                />
              )}
            startReached={viewMode === "infinite" ? loadOlderMessages : undefined}
            endReached={viewMode === "infinite" ? loadNewerMessages : undefined}
            overscan={200} // buffer pixels above/below for smoother scroll
            components={{
              Header: () =>
                loadingOlder ? (
                  <div className="text-center text-xs text-neutral-400 py-2">Loading older messages...</div>
                ) : atStart ? (
                  <div className="text-center text-xs text-neutral-400 py-2">— Beginning of project —</div>
                ) : null,
              Footer: () =>
                loadingNewer ? (
                  <div className="text-center text-xs text-neutral-400 py-2">Loading newer messages...</div>
                ) : atEnd ? (
                  <div className="text-center text-xs text-neutral-400 py-2">— Latest message —</div>
                ) : null,
            }}
          />
        )}
      </div>
    </div>
  );
}