
"use client";
import { useState, useEffect, useCallback, useMemo } from "react";
// Hooks
import { useConfig } from '@/hooks/ConfigContext';
// Components
import MessageItem from "@/components/app/MessageItem";
import MultiActionBar from "@/components/app/MultiActionBar"
// Utils
import {
    handleDelete,
    handleMultiAction,
  } from "@/utils/messageActions";



const RecycleBin = (
  {
    // Feature flags
    enableTTS,
    enablePublic,
    enableSync,
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
    multiSelectEnabled,
    selectedMessageIds,
    handleToggleMultiSelect,
    handleToggleSelect,
    setChatMessages,
    setThreadMessages,
    setShowProjectPanel,
    setShowTagPanel,
  }
) => {
  // Initial states

  const [deletedMessages, setDeletedMessages] = useState([]);
  const [paging, setPaging] = useState({ before_id: null, after_id: null, limit: 30 });
  const [loading, setLoading] = useState(false);
  const [atOldest, setAtOldest] = useState(false);
  const [atNewest, setAtNewest] = useState(false);


  const { museProfile, museProfileLoading } = useConfig();
  const museName = museProfile?.name?.[0]?.content ?? "Muse";
  const mode = "forgotten";

  function loadDeletedMessages({ beforeId = null, afterId = null, direction = null } = {}) {
    setLoading(true);

    const params = new URLSearchParams();
    params.set("limit", paging.limit);
    if (beforeId) params.set("before_id", beforeId);
    if (afterId) params.set("after_id", afterId);

    fetch(`/api/messages/deleted?${params.toString()}`)
      .then(res => res.json())
      .then(data => {
        const msgs = data.messages || [];

        if (!msgs.length) {
          if (direction === "older") setAtOldest(true);
          if (direction === "newer") setAtNewest(true);
          return;
        }

        setDeletedMessages(msgs);
        setPaging(data.paging || { before_id: null, after_id: null, limit: paging.limit });

        // We moved, so we’re not at that edge anymore.
        if (direction === "older") setAtNewest(false);
        if (direction === "newer") setAtOldest(false);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    setDeletedMessages([]);
    setPaging({ before_id: null, after_id: null, limit: 30 });
    setAtOldest(false);
    setAtNewest(false);
    loadDeletedMessages();
  }, []);


  // ------------------------------------
  // Message Actions States and Functions
  // ------------------------------------
  const [projectDialogOpen, setProjectDialogOpen] = useState(null)
  const [threadPanelOpen, setThreadPanelOpen] = useState(null);
  const onForgottenMultiAction = (action, options = {}) => {
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
      case "add_threads":
        console.log(">>> setting showThreadPanel = 'add'");
        setShowThreadPanel("add");
        break;
      case "remove_threads":
        console.log(">>> setting showThreadPanel = 'remove'");
        setShowThreadPanel("remove");
        break;
      default:
        // simple actions go straight through
        handleMultiAction(setHistoryMessages, setThreadMessages, setChatMessages, selectedMessageIds, action, options);
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
        <div className="w-full md:w-full flex flex-col min-h-0">
          <div className="recycle-bin-pagination">
            <button
              disabled={loading || atOldest || !paging.before_id}
              onClick={() => loadDeletedMessages({ beforeId: paging.before_id, direction: "older" })}
            >
              Older
            </button>

            <button
              disabled={loading || atNewest || !paging.after_id}
              onClick={() => loadDeletedMessages({ afterId: paging.after_id, direction: "newer" })}
            >
              Newer
            </button>
          </div>

          {/* Conversation Log panel */}
          <div className="flex-1 bg-neutral-900 p-4 rounded-lg border border-neutral-700 flex flex-col min-h-0">
            <div className="flex-1 min-h-0 overflow-y-auto space-y-2">


              {loading && (
                <div className="w-full h-24 text-neutral-400 text-center flex items-center justify-center">
                  Loading...
                </div>
              )}

              {!loading && deletedMessages.length === 0 && (
                <div className="w-full h-64 text-neutral-500 text-sm font-mono flex items-center justify-center">
                  &lt;No messages found.&gt;
                </div>
              )}

              {!loading && deletedMessages.length > 0 && (
                <div className="space-y-2">
                  {deletedMessages.map((msg, idx) => (
                    <MessageItem
                      key={msg.message_id || idx}
                      enableTTS={enableTTS}
                      audioControls={audioControls}
                      msg={msg}
                      setMessages={setDeletedMessages}
                      setAltMessages={setChatMessages}
                      threads={threads}
                      setThreadMessages={setThreadMessages}
                      clearSelectionAndExit={clearSelectionAndExit}
                      projects={projects}
                      projectsLoading={projectsLoading}
                      projectMap={projectMap}
                      museName={museName}
                      mode={mode}
                      audioControls={audioControls}
                      multiSelectEnabled={multiSelectEnabled}
                      isSelected={selectedMessageIds.includes(msg.message_id)}
                      onToggleSelect={handleToggleSelect}
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

export default RecycleBin;
