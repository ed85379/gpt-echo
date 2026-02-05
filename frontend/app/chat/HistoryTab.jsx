// app/chat/HistoryTab.jsx
"use client";
import { useState, useEffect, useCallback, useMemo } from "react";
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/dist/style.css';
// Hooks
import { useConfig } from '@/hooks/ConfigContext';
// Components
import MessageItem from "@/components/app/MessageItem";
import MultiActionBar from "@/components/app/MultiActionBar"
import ProjectPickerPanel from "@/components/app/ProjectPickerPanel"
import TagPanel from "@/components/app/TagPanel"
// Utils
import {
    handleDelete,
    handleTogglePrivate,
    handleToggleHidden,
    handleToggleRemembered,
    handleMultiAction
  } from "@/utils/messageActions";
import { getMonthRange } from "@/utils/utils";

// General props and functions
const SOURCE_CHOICES = [
  { key: "frontend", label: "Frontend" },
  { key: "chatgpt", label: "ChatGPT" },
  { key: "discord", label: "Discord" }
];

const HistoryTab = (
  {
    // General and nav
    audioControls,

    // Project & Threads
    threads,
    threadMap,
    projects,
    project,
    fetchProjects,
    projectMap,
    projectsLoading,

    // Message Actions
    clearSelectionAndExit,
    setSelectedMessageIds,
    onReturnToThisMoment,
    createThreadWithMessages,
    multiSelectEnabled,
    selectedMessageIds,
    showProjectPanel,
    setShowProjectPanel,
    showTagPanel,
    setShowTagPanel,
    showThreadPanel,
    setShowThreadPanel,
    handleToggleMultiSelect,
    handleToggleSelect,
    handleCreateThread,
    handleJoinThread,
    handleLeaveThread,
    tagDialogOpen,
    setTagDialogOpen,
    handleConfirmProject,
    handleConfirmTagsAdd,
    handleConfirmTagsRemove,
    existingTagsForSelection,
  }
) => {
  // Initial states
  const [source, setSource] = useState("Frontend");
  const [messages, setMessages] = useState([]);

  // ------------------------------------
  // Message Filters
  // ------------------------------------
  const [projectFilter, setProjectFilter] = useState("")
  const [tagFilter, setTagFilter] = useState([]);
  const [availableTags, setAvailableTags] = useState([]);
  const [tagsExpanded, setTagsExpanded] = useState(false);
  const hasTags = availableTags.length > 0;
  const [showHidden, setShowHidden] = useState(false)
  const [showForgotten, setShowForgotten] = useState(false)
  const [showPrivate, setShowPrivate] = useState(false)
  const [search, setSearch] = useState("")
  const selectedTagObjects = availableTags.filter(t =>
    tagFilter.includes(t.tag)
  );

  const { museProfile, museProfileLoading } = useConfig();
  const museName = museProfile?.name?.[0]?.content ?? "Muse";
  const mode = "history";


  // 1. Base: apply left-column filters (AND) to messages
  const baseFiltered = useMemo(
    () =>
      messages.filter(msg => {
        // Project filter (AND)
        if (projectFilter && msg.project_id !== projectFilter) return false;

        // Hidden / Forgotten / Private flags (AND)
        if (!showHidden && msg.is_hidden) return false;
        if (!showForgotten && msg.is_deleted) return false;
        if (!showPrivate && msg.is_private) return false;

        return true;
      }),
    [messages, projectFilter, showHidden, showForgotten, showPrivate, search]
  );

  // 2. Helpers for right-column filters (OR)
  const matchesSearch = msg => {
    const term = search.trim().toLowerCase();
    if (!term) return false;

    const haystack = [
      msg.text || "",
      msg.role || "",
      msg.user_name || "",
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(term);
  };

  const matchesAnyTag = msg => {
    if (tagFilter.length === 0) return false;
    const tags = msg.user_tags || [];
    return tags.some(tag => tagFilter.includes(tag));
  };

  // 3. Final filteredMessages:
  //    baseFiltered (AND) + (search OR tags) on top
  const filteredMessages = useMemo(
    () => {
      const hasSearch = !!search.trim();
      const hasTags = tagFilter.length > 0;

      // No OR filters → just return the AND-filtered base set
      if (!hasSearch && !hasTags) return baseFiltered;

      // Otherwise, within that base set, keep anything that matches
      // search OR tags
      return baseFiltered.filter(msg =>
        (hasSearch && matchesSearch(msg)) ||
        (hasTags && matchesAnyTag(msg))
      );
    },
    [baseFiltered, search, tagFilter]
  );

  useEffect(() => {
    fetch("/api/messages/user_tags")
      .then(res => res.json())
      .then(data => setAvailableTags(data.tags || []));
  }, []);
  // ------------------------------------
  // End - Message Filters
  // ------------------------------------

  // ------------------------------------
  // Calendar Functions and Message Load
  // ------------------------------------

  const [calendarStatus, setCalendarStatus] = useState({});
  const [selectedDate, setSelectedDate] = useState(null);

  const [loading, setLoading] = useState(false);
  const [displayMonth, setDisplayMonth] = useState(new Date());

  useEffect(() => {
    setCalendarStatus({});
    const { start, end } = getMonthRange(displayMonth);

    let params = `source=${encodeURIComponent(source)}&start=${start}&end=${end}`;

    // Project filter
    if (projectFilter) {
      params += `&project_id=${encodeURIComponent(projectFilter)}`;
    }

    // Flags – decide how you want to represent them to the backend.
    // Example: send booleans for "include_hidden", etc.
    params += `&include_hidden=${showHidden ? "1" : "0"}`;
    params += `&include_forgotten=${showForgotten ? "1" : "0"}`;
    params += `&include_private=${showPrivate ? "1" : "0"}`;

    // Tags (OR within the day, as you already do)
    tagFilter.forEach(t => {
      params += `&tag=${encodeURIComponent(t)}`;
    });

    fetch(`/api/messages/calendar_status_simple?${params}`)
      .then(res => res.json())
      .then(data => {
        setCalendarStatus(data.days || {});
      });
  }, [
    source,
    displayMonth,
    tagFilter,
    projectFilter,
    showHidden,
    showForgotten,
    showPrivate,
  ]);

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

  // ------------------------------------
  // End - Calendar Functions and Message Load
  // ------------------------------------


  // ------------------------------------
  // Message Actions States and Functions
  // ------------------------------------
  const [projectDialogOpen, setProjectDialogOpen] = useState(null)
  const onHistoryMultiAction = (action, options = {}) => {
    console.log("onMultiAction called with:", action);
    switch (action) {
      case "set_project":
        console.log(">>> setting showProjectPanel = true");
        setShowProjectPanel(true);
        break;
      case "add_tags":
        console.log(">>> setting showTagPanel = 'add'");
        setShowTagPanel("add");
        break;
      case "remove_tags":
        console.log(">>> setting showTagPanel = 'remove'");
        setShowTagPanel("remove");
        break;
      default:
        // simple actions go straight through
        handleMultiAction(setMessages, selectedMessageIds, action, options);
        clearSelectionAndExit();
    }
  };

  // ------------------------------------
  // End - Message Actions States and Functions
  // ------------------------------------


  return (
    <div className="p-6 h-full flex flex-col min-h-0">
      {/* Main content: left = calendar + filters, right = search + log */}
      <div className="flex-1 flex flex-col md:flex-row gap-6 min-h-0">
        {/* LEFT COLUMN: Calendar + Filters */}
        <div className="w-full md:w-1/4 flex flex-col gap-0 min-h-0">
          {/* Calendar */}
          <div className="origin-top-left scale-95">
            <DayPicker
              mode="single"
              month={displayMonth}
              onMonthChange={setDisplayMonth}
              selected={selectedDate}
              onSelect={setSelectedDate}
              modifiers={{
                hasMessages: day => {
                  const d = day.toISOString().slice(0, 10);
                  return !!calendarStatus[d];
                }
              }}
              modifiersClassNames={{
                hasMessages: "bg-purple-800/70 text-white font-bold"
              }}
              className="rdp-custom"
            />
          </div>

          {/* Filters block */}
          <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-1 text-neutral-300 pr-1">
            <div className="font-semibold text-neutral-200">Filters</div>

              {/* Source */}
              <label className="flex items-center gap-2 text-sm text-neutral-300">
                <span className="whitespace-nowrap">Source:</span>
                <select
                  value={source}
                  onChange={e => setSource(e.target.value)}
                  className="flex-1 px-2 py-1 rounded bg-neutral-900 text-white border border-neutral-700"
                >
                  {SOURCE_CHOICES.map(opt => (
                    <option key={opt.key} value={opt.key}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>

              {/* Project */}
              <label className="flex items-center gap-2 text-sm text-neutral-300">
                <span className="whitespace-nowrap">Project:</span>
                <select
                  value={projectFilter}
                  onChange={e => setProjectFilter(e.target.value)}
                  className="flex-1 px-2 py-1 rounded bg-neutral-900 text-white border border-neutral-700"
                >
                  <option value="">All</option>
                  {projects.map(p => (
                    <option key={p._id} value={p._id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>

            {/* Visibility box — you can later swap "Include" to your Include <-> Only switch */}
            <div className="mt-1 border border-neutral-700 rounded p-2">
              {/*}<div className="text-xs uppercase tracking-wide text-neutral-400 mb-1">
                Visibility
              </div>*/}
              <div className="text-xs text-neutral-300 mb-1">
                Show: (excluded by default)
              </div>
              <div className="text-xs flex gap-3">
                <label>
                  <input
                    type="checkbox"
                    className="mr-1 accent-purple-600"
                    checked={showPrivate}
                    onChange={e => setShowPrivate(e.target.checked)}
                  />
                  Private
                </label>
                <label>
                  <input
                    type="checkbox"
                    className="mr-1 accent-purple-600"
                    checked={showHidden}
                    onChange={e => setShowHidden(e.target.checked)}
                  />
                  Hidden
                </label>
                <label>
                  <input
                    type="checkbox"
                    className="mr-1 accent-purple-600"
                    checked={showForgotten}
                    onChange={e => setShowForgotten(e.target.checked)}
                  />
                  Forgotten
                </label>

              </div>
            </div>

            {/* Tags area — placeholder for future scrollable tag cloud */}
            <div className="mt-1">
                {/* Future: Sort control (Alpha / Count) */}
                {/* <div className="text-xs text-neutral-500">
                  Sort: Alpha / Count
                    </div> */}
              <div className="flex flex-wrap gap-2 items-center">
                <span className="text-sm text-neutral-300">Filter by tag:</span>
                  {tagFilter.length > 0 && (
                  <button
                    className="ml-2 px-2 py-1 bg-neutral-700 text-purple-200 rounded hover:bg-neutral-600"
                    onClick={() => setTagFilter([])}
                  >
                    Clear
                  </button>
                )}
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
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Search + MultiActionBar + Conversation Log */}
        <div className="w-full md:w-3/4 flex flex-col min-h-0">
          {/* Header row: Search + MultiActionBar */}
          <div className="mb-3 flex flex-col md:flex-row gap-2 items-start md:items-center justify-between">
            {/* Search (only above the log) */}
            <label className="flex items-center gap-2 text-sm text-neutral-300">
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="flex-1 px-2 py-1 rounded bg-neutral-900 text-white border border-neutral-700"
                placeholder="Search text…"
              />
            </label>

            {/* MultiActionBar (always visible) */}
            <div className="w-full md:w-auto flex justify-end">
              <MultiActionBar
                multiSelectEnabled={multiSelectEnabled}
                onToggleMultiSelect={handleToggleMultiSelect}
                selectedCount={selectedMessageIds.length}
                onAction={onHistoryMultiAction}
                disabled={null}
                setShowProjectPanel={setShowProjectPanel}
                setShowTagPanel={setShowTagPanel}
              />
              {/* Overlay row for complex actions */}
              {showProjectPanel && (
                <div className="absolute right-9 top-25 mt-9 z-20 flex justify-end">
                  {console.log(">>> ProjectPickerPanel block is rendering")}
                  <ProjectPickerPanel
                    projects={projects}
                    onConfirm={handleConfirmProject}
                    onCancel={() => setShowProjectPanel(false)}
                  />
                </div>
              )}

              {showTagPanel && (
                <div className="absolute right-9 top-25 mt-9 z-20 flex justify-end">
                  <TagPanel
                    mode={showTagPanel}
                    existingTags={existingTagsForSelection}
                    onConfirm={
                      showTagPanel === "add"
                        ? handleConfirmTagsAdd
                        : handleConfirmTagsRemove
                    }
                    onCancel={() => setShowTagPanel(null)}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Conversation Log panel */}
          <div className="flex-1 bg-neutral-900 p-4 rounded-lg border border-neutral-700 flex flex-col min-h-0">
            <div className="flex-1 min-h-0 overflow-y-auto space-y-2">
              {!selectedDate && !loading && (
                <div className="w-full h-64 text-neutral-500 text-sm font-mono flex items-center justify-center">
                  &lt;Select a date to view conversation log&gt;
                </div>
              )}

              {loading && (
                <div className="w-full h-24 text-neutral-400 text-center flex items-center justify-center">
                  Loading...
                </div>
              )}

              {!loading && selectedDate && filteredMessages.length === 0 && (
                <div className="w-full h-64 text-neutral-500 text-sm font-mono flex items-center justify-center">
                  &lt;No messages found for this day.&gt;
                </div>
              )}

              {!loading && filteredMessages.length > 0 && (
                <div className="space-y-2">
                  {filteredMessages.map((msg, idx) => (
                    <MessageItem
                      key={msg.message_id || idx}
                      msg={msg}
                      setMessages={setMessages}
                      projects={projects}
                      projectsLoading={projectsLoading}
                      projectMap={projectMap}
                      tagDialogOpen={tagDialogOpen}
                      setTagDialogOpen={setTagDialogOpen}
                      projectDialogOpen={projectDialogOpen}
                      setProjectDialogOpen={setProjectDialogOpen}
                      museName={museName}
                      setShowThreadPanel={setShowThreadPanel}
                      mode={mode}
                      audioControls={audioControls}
                      onReturnToThisMoment={onReturnToThisMoment}
                      multiSelectEnabled={multiSelectEnabled}
                      isSelected={selectedMessageIds.includes(msg.message_id)}
                      onToggleSelect={handleToggleSelect}
                      createThreadWithMessages={createThreadWithMessages}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HistoryTab;
