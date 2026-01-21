"use client";
import React from "react";
import { useState, useEffect, useRef } from "react";
import { Remarkable } from 'remarkable';
import {
  Eye,
  EyeOff,
  EyeClosed,
  DoorClosed,
  DoorClosedLocked,
  Tags,
  Shredder,
  SquareX,
  History,
  Slash
  } from 'lucide-react';
import { BookDashed, BookMarked, ArrowBigDownDash, Paperclip, Pin, Sparkles } from 'lucide-react';
import { linkify } from 'remarkable/linkify';
import { useConfig } from '@/hooks/ConfigContext';
import { assignMessageId, toPythonIsoString, fileToBase64, trimMessages } from '@/utils/utils';
import { useMemo } from "react";
import MessageItem from "@/components/app/MessageItem";
import { handleDelete, handleTogglePrivate, handleToggleHidden, handleToggleRemembered } from "@/utils/messageActions";
import { setProject, clearProject, addTag, removeTag } from "@/utils/messageActions";

function HistoryOffIcon(props) {
  return (
    <span className="relative inline-flex h-4 w-4" {...props}>
      <History className="absolute inset-0" />
      <Slash className="absolute inset-0" />
    </span>
  );
}

const ChatTab = (
  {
    setSpeaking,
    selectedProjectId,
    focus,
    autoAssign,
    injectedFiles,
    files,
    setInjectedFiles,
    handlePinToggle,
    ephemeralFiles,
    setEphemeralFiles,
    handleEphemeralUpload
  }
) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [autoTTS, setAutoTTS] = useState(false);
  const [lastTTS, setLastTTS] = useState(null);
  const [thinking, setThinking] = useState(false);
  const [connecting, setConnecting] = useState(true);
  const [isTTSPlaying, setIsTTSPlaying] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [scrollToBottom, setScrollToBottom] = useState(true);
  const [tagDialogOpen, setTagDialogOpen] = useState(null); // message id or null
  const [newTag, setNewTag] = useState("");
  const [projectDialogOpen, setProjectDialogOpen] = useState(null); // message id or null
  const [newProject, setNewProject] = useState("");
  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [scrollToMessageId, setScrollToMessageId] = useState(null);
  const [scrollTargetNode, setScrollTargetNode] = useState(null);
  const [atBottom, setAtBottom] = useState(true);

  const chatEndRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const audioCtxRef = useRef(null);
  const audioSourceRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const messageRefs = useRef({});
  const { museProfile, museProfileLoading, uiPollstates } = useConfig();
  const { states } = uiPollstates || {};
  const museName = museProfile?.name?.[0]?.content ?? "Muse";
  const [timeSkipOverride, setTimeSkipOverride] = useState(null);
  const timeSkipActive =
  timeSkipOverride !== null
    ? timeSkipOverride
    : Boolean(states?.time_skip?.active);
  const INITIAL_RENDERED_MESSAGES = 10;  // On reload, after chat, etc.
  const ACTIVE_WINDOW_LIMIT = 10;         // After new message
  const SCROLLBACK_LIMIT = 30;            // After scroll up
  const MAX_RENDERED_MESSAGES = 30;      // Max after scroll loading "more"
  const MESSAGE_LIMIT = 10;              // How many to load per scroll/page
  const visibleMessages = messages.slice(-MAX_RENDERED_MESSAGES);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  const mode = "chat";
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

  const handleFileInputChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    handleEphemeralUpload(file); // Use your upload logic here!
    e.target.value = "";
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) handleEphemeralUpload(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handlePaste = (e) => {
    if (!e.clipboardData || !e.clipboardData.items) return;

    // Look for image files in the clipboard
    for (let i = 0; i < e.clipboardData.items.length; i++) {
      const item = e.clipboardData.items[i];
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile();
        if (file) {
          handleEphemeralUpload(file);
          // Optionally: prevent image from being pasted as base64 text into textarea
          e.preventDefault();
        }
      }
    }
  };

  const ACCEPTED_TYPES = [
    ".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".js", ".ts", ".py", ".java", ".c", ".cpp", ".cs", ".go", ".rb", ".php",
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp"
  ];

  useEffect(() => {
    if (scrollTargetNode) {
      scrollTargetNode.scrollIntoView({ behavior: "smooth", block: "start" });
      setScrollTargetNode(null);
      setScrollToMessageId(null);
    }
  }, [scrollTargetNode]);

  const handleReadAloudClick = () => {
    if (isTTSPlaying) {
      // STOP logic
      window.speechSynthesis.cancel();
      setIsTTSPlaying(false);
    } else {
      // START logic
      speak(textToRead, () => setIsTTSPlaying(false)); // pass a callback when done
      setIsTTSPlaying(true);
    }
  };

  const playPing = () => {
    const audio = new window.Audio("/ping.mp3");
    audio.play();
  };

  const formatTimestamp = (utcString) => {
    if (!utcString) return "";
    const dt = new Date(utcString);
    return dt.toLocaleString(); // Respects user timezone/locales
  };

  async function handleClearTimeSkip() {
    try {
      // optimistic UI: flip it *now*
      setTimeSkipOverride(false);

      await fetch("/api/time_skip/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      loadMessages()
      // optional: once the next poll confirms, you can clear override
      // setTimeSkipOverride(null);
    } catch (err) {
      console.error("Error clearing time skip:", err);
      // if you want to be fancy, roll back:
      setTimeSkipOverride(null);
    }
  }
  useEffect(() => {
    if (timeSkipOverride === null) return;

    const backendActive = Boolean(states?.time_skip?.active);

    // if backend has caught up with our optimistic value, drop override
    if (backendActive === timeSkipOverride) {
      setTimeSkipOverride(null);
    }
  }, [states?.time_skip?.active, timeSkipOverride]);

  const loadMessages = async (before = null) => {
    setLoadingMore(true);

    let prevScrollHeight = null;
    let prevScrollTop = null;

    // Only care about previous scroll position if loading history
    if (before && scrollContainerRef.current) {
      prevScrollHeight = scrollContainerRef.current.scrollHeight;
      prevScrollTop = scrollContainerRef.current.scrollTop;
    }

    let url = `/api/messages?limit=${INITIAL_RENDERED_MESSAGES}&sources=frontend&sources=chatgpt&sources=reminder&sources=discovery&sources=whispergate`;
    if (before) url += `&before=${encodeURIComponent(before)}`;
    const res = await fetch(url);
    const data = await res.json();

    if (before) {
      setMessages(prev => trimMessages([...data.messages, ...prev], SCROLLBACK_LIMIT));
      setScrollToBottom(false); // Don't scroll when loading history

      // After next render, restore the scroll position so the previous top message stays in place
      setTimeout(() => {
        requestAnimationFrame(() => {
          if (scrollContainerRef.current && prevScrollHeight !== null && prevScrollTop !== null) {
            const newScrollHeight = scrollContainerRef.current.scrollHeight;
            scrollContainerRef.current.scrollTop = newScrollHeight - prevScrollHeight + prevScrollTop;
          }
        });
      }, 0);
    } else {
      setMessages(trimMessages(data.messages, ACTIVE_WINDOW_LIMIT));
      //setScrollToBottom(true); // Scroll when loading initial/latest
    }
    if (data.messages.length === SCROLLBACK_LIMIT) setHasMore(false);
      setLoadingMore(false);
  };


  useEffect(() => {
    loadMessages();
    // eslint-disable-next-line
  }, []);


  useEffect(() => {
    if (scrollToBottom) {
      chatEndRef.current?.scrollIntoView({behavior: "smooth"});
    }
  }, [messages, scrollToBottom]);

  // WebSocket with auto-reconnect
  useEffect(() => {
    let cancelled = false;
    function connectWebSocket() {
      setConnecting(true);
      const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
      const wsHost = window.location.host;
      const wsPath = "/ws"; // or whatever your backend WebSocket endpoint is
      const ws = new WebSocket(`${wsProtocol}://${wsHost}${wsPath}`);
      wsRef.current = ws;

      const tryRegister = () => {
        if (ws.readyState === 1) {
          ws.send(JSON.stringify({ listen_as: "frontend" }));
          setConnecting(false);
        } else if (!cancelled) {
          setTimeout(tryRegister, 50);
        }
      };
      tryRegister();

      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "muse_message") {
          const text = data.message;
          const message_id = data.message_id;
          const project_id = data.project_id;
          setMessages((prev) =>
            trimMessages([
              ...prev,
              {
                from: "muse",
                text,
                message_id,
                timestamp: new Date().toISOString(),
                project_id
              }
            ], ACTIVE_WINDOW_LIMIT)
          );
          setScrollToMessageId(message_id);  // <-- Flag for scroll

          setLastTTS(text);
          setThinking(false);
          if (autoTTS) {

            await speak(text, () => setIsTTSPlaying(false));
          } else {
            playPing();
          }
        }
      };


      ws.onclose = () => {
        if (!cancelled) {
          setConnecting(true);
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 1500);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connectWebSocket();

    return () => {
      cancelled = true;
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [autoTTS]);

  useEffect(() => {
    if (scrollToBottom) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (scrollToMessageId && messageRefs.current[scrollToMessageId]) {
      messageRefs.current[scrollToMessageId].current?.scrollIntoView({ behavior: "smooth", block: "start" });
      setScrollToMessageId(null);
    }
  }, [scrollToMessageId, messages]);

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




  const mergedFiles = [
    ...ephemeralFiles.map(f => ({
      id: f.id,
      name: f.name,
      type: f.type,
      size: f.size,
      file: f.file,
      source: "ephemeral",
    })),
    ...injectedFiles
      .filter(({ id }) => {
        // Exclude any injected files that are also in ephemeralFiles, if you ever overlap
        return !ephemeralFiles.some(f => f.id === id);
      })
      .map(({ id: fileId, pinned }) => {
        const file = files.find(f => f.id === fileId);
        if (!file) return null;
        return {
          id: fileId,
          name: file.name,
          type: file.type,
          size: file.size,
          pinned,
          source: "injected",
          file,
        };
      })
  ].filter(Boolean);

  const clearEphemeralFiles = () => {
    setInjectedFiles(prev => prev.filter(f => f.pinned));
    setEphemeralFiles([]);
  };


  const handleSubmit = async () => {
    if (!input.trim()) return;
    const allFiles = [
      ...injectedFiles,
      ...ephemeralFiles.map(f => ({
        name: f.name,
        type: f.type,
        // add other fields if you want, but 'name' is usually the key for prompt
      }))
    ];

    const filenamesBlock = allFiles.length
      ? '\n' + allFiles.map(f => `[file: ${f.name}]`).join('\n')
      : '';
    const timestamp = toPythonIsoString();
    const role = "user";
    const source = "frontend";
    const message = input + (filenamesBlock ? '\n' + filenamesBlock : '');
    const project_id = (autoAssign && selectedProjectId) ? selectedProjectId : "";
    const ephemeralPayload = await Promise.all(
      ephemeralFiles.map(async (f) => ({
        name: f.name,
        type: f.type,
        size: f.size,
        data: await fileToBase64(f.file),
        encoding: "base64"
      }))
    );

    // 1. Generate the message_id (async)//
    const message_id = await assignMessageId({
      timestamp,
      role,
      source,
      message
    });

    // 2. Add to UI state immediately (so it’s taggable, traceable, etc.)//
    setMessages(prev =>
      trimMessages([
        ...prev,
        {
          id: message_id,
          message_id,
          text: message,
          timestamp,
          role,
          source,
          project_id
        }
      ], ACTIVE_WINDOW_LIMIT)
    );

    setInput("");
    setThinking(true);
    setScrollToBottom(true);

    // 3. Send the message to the backend, including timestamp
    await fetch("/api/talk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: message,
        timestamp,
        message_id,
        project_id: selectedProjectId,
        auto_assign: autoAssign,
        blend_ratio: focus,
        injected_files: injectedFiles.map(f => f.id),
        ephemeral_files: ephemeralPayload
      }),
    });

    // 4. Clean up ephemerals (only keep pinned) //
    clearEphemeralFiles();
  };

  const speak = async (text, onDone) => {
    setSpeaking(true);
    setIsTTSPlaying(true);

    // If audio is playing, stop it
    if (audioSourceRef.current) {
      try {
        audioSourceRef.current.stop();
      } catch (e) {}
      audioSourceRef.current = null;
    }
    if (audioCtxRef.current) {
      try {
        audioCtxRef.current.close();
      } catch (e) {}
      audioCtxRef.current = null;
    }

    const response = await fetch("/api/tts/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      setSpeaking(false);
      setIsTTSPlaying(false);
      if (onDone) onDone();
      return;
    }
    const reader = response.body.getReader();
    const audioCtx = new window.AudioContext();
    audioCtxRef.current = audioCtx; // Track for stopping
    const source = audioCtx.createBufferSource();
    audioSourceRef.current = source; // Track for stopping
    const chunks = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(...value);
    }

    const buffer = new Uint8Array(chunks).buffer;
    audioCtx.decodeAudioData(buffer, (decoded) => {
      if (!audioCtxRef.current) return; // canceled before playback started
      source.buffer = decoded;
      source.connect(audioCtx.destination);
      source.start(0);
      source.onended = () => {
        setSpeaking(false);
        setIsTTSPlaying(false);
        audioSourceRef.current = null;
        audioCtxRef.current = null;
        if (onDone) onDone();
      };
    });
  };


  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="relative flex flex-col h-full ">
      <div className="flex gap-2 items-center mt-4">
        <label className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={autoTTS}
            onChange={(e) => setAutoTTS(e.target.checked)}
            disabled={thinking || connecting}
          />
          <span className="text-sm text-neutral-300">Auto-TTS</span>
        </label>
        <button
          onClick={() => {
            if (isTTSPlaying) {
              // Stop current audio
              if (audioSourceRef.current) {
                try {
                  audioSourceRef.current.stop();
                } catch (e) {}
                audioSourceRef.current = null;
              }
              if (audioCtxRef.current) {
                try {
                  audioCtxRef.current.close();
                } catch (e) {}
                audioCtxRef.current = null;
              }
              setIsTTSPlaying(false);
              setSpeaking(false);
            } else if (lastTTS && !connecting) {
              speak(lastTTS, () => setIsTTSPlaying(false));
            }
          }}
          className="text-sm text-purple-300 hover:underline"
          disabled={connecting || !lastTTS}
        >
          {isTTSPlaying ? "⏹️ Stop" : "▶️ Play"}
        </button>
      </div>
        {!atBottom && (
        <button
          type="button"
          onClick={() => {
            chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
          }}
          className="
            absolute
            bottom-28
            left-1/2
            -translate-x-1/2
            z-20
            bg-purple-700 text-white px-3 py-1 rounded-full shadow-lg
            hover:bg-purple-800 transition
          "
        >
          <ArrowBigDownDash />
        </button>
      )}
      <div
        ref={scrollContainerRef}
        className="mt-4 flex-1 min-h-0 overflow-y-auto relative"
        onScroll={async (e) => {
          const { scrollTop, scrollHeight, clientHeight } = e.target;
          if (scrollTop + clientHeight >= scrollHeight - 10) {
            setAtBottom(true);
          } else {
            setAtBottom(false);
          }
          if (scrollTop === 0 && hasMore && !loadingMore && messages.length > 0) {
            // Get the timestamp of the oldest message //
            const oldest = messages[0]?.timestamp;
            if (oldest) {
              await loadMessages(oldest);
            }
          }
        }}
      >

        <div className="text-sm text-neutral-400 italic text-center mt-2">
          That’s the beginning. Visit the History Tab for more.
        </div>
        {connecting && (
          <div className="text-sm text-neutral-400">Reconnecting…</div>
        )}
        {visibleMessages.map((msg, idx) => {
          if (!messageRefs.current[msg.message_id]) {
            messageRefs.current[msg.message_id] = React.createRef();
          }
          return (
            <MessageItem
              key={msg.message_id || idx}
              ref={messageRefs.current[msg.message_id]}
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
            />
          );
        })}
        {thinking && (
          <div className="text-sm text-neutral-500 italic">
            {museName} is thinking...
          </div>
        )}
        <div ref={chatEndRef} />
      </div>
      <div className="mt-2 shrink-0">
      {mergedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {mergedFiles.map(f => {
            // Icon logic
            let Icon;
            let iconTitle;
            let tileBg = "";
            let badge = null;

            if (f.source === "ephemeral") {
              Icon = /* your ephemeral icon, e.g. */ Sparkles || PaperAirplaneIcon;
              iconTitle = "Ephemeral file (not saved)";
              tileBg = "bg-blue-950/80 border border-blue-300";

            } else if (f.pinned) {
              Icon = Pin;
              iconTitle = "Pinned file";
              tileBg = "bg-purple-900 border-2 border-purple-500";
            } else {
              Icon = Paperclip;
              iconTitle = "Injected file";
              tileBg = "bg-white/10 border border-white/15";
            }

            return (
              <span
                key={f.id}
                className={`
                  flex items-center px-2 py-1 rounded-md shadow-sm text-xs font-medium
                  transition hover:bg-white/20 cursor-default select-none
                  ${tileBg}
                  text-purple-100 max-w-[200px] backdrop-blur-[2px]
                `}
              >
                {/* Icon */}
                <Icon
                  className={`w-4 h-4 shrink-0 mr-1 ${
                    f.pinned
                      ? "text-yellow-300 opacity-100"
                      : f.source === "ephemeral"
                      ? "text-blue-300 opacity-90"
                      : "text-purple-300 opacity-70"
                  }`}
                  strokeWidth={2}
                  title={iconTitle}
                />

                {/* File name (with badge for ephemeral) */}
                <span className="truncate max-w-[120px]">
                  {f.name.length > 32 ? f.name.slice(0, 29) + "..." : f.name}
                </span>
                {badge}

                {/* Remove button */}
                <button
                  onClick={() => {
                    if (f.source === "ephemeral") {
                      setEphemeralFiles(files => files.filter(x => x.id !== f.id));
                    } else {
                      setInjectedFiles(prev => prev.filter(x => x.id !== f.id));
                    }
                  }}
                  aria-label={`Remove ${f.name}`}
                  className="
                    ml-2
                    text-purple-300 hover:text-red-400
                    text-base font-bold
                    focus:outline-none
                    transition
                    px-0.5 leading-none
                  "
                  type="button"
                  tabIndex={0}
                >
                  ×
                </button>
                {/* Pin toggle only for injected */}
                {f.source === "injected" && (
                  <button
                    onClick={() => handlePinToggle(f.id)}
                    aria-label={f.pinned ? `Unpin ${f.name}` : `Pin ${f.name}`}
                    className="ml-1 focus:outline-none"
                    type="button"
                    tabIndex={0}
                    title={f.pinned ? "Unpin file" : "Pin file"}
                    style={{ background: "none", border: 0, padding: 0, display: "flex", alignItems: "center" }}
                  >
                    <Pin
                      className={`w-4 h-4 shrink-0 ${
                        f.pinned
                          ? "text-yellow-300 opacity-100"
                          : "text-purple-300 opacity-60"
                      }`}
                      strokeWidth={2}
                    />
                  </button>
                )}
              </span>
            );
          })}
        </div>
      )}
      <div className="flex gap-1 items-stretch w-full">
        {/* Textarea wrapper is the flex child now */}
        <div className="relative flex-1 min-w-0">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={3}
            className="w-full p-2 pr-9 rounded-lg bg-neutral-800 text-white resize-none border border-neutral-700 focus:border-purple-500 focus:outline-none"
            placeholder={`Say something to ${museName}...`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onPaste={handlePaste}
            style={{
              background: dragActive ? "#a78bfa22" : undefined,
              border: dragActive ? "2px dashed #a78bfa" : undefined,
              borderRadius: dragActive ? 10 : undefined,
              transition: "border 0.15s, background 0.15s"
            }}
          />

          {/* Time-skip badge in the textarea corner */}
          {timeSkipActive && (
            <button
              className="absolute top-2 right-2 flex h-7 w-7 items-center justify-center
                         rounded-md text-neutral-300 hover:text-purple-200
                         bg-transparent hover:bg-neutral-800/40"
              title="Return to present (clear time filter)"
              onClick={handleClearTimeSkip}
            >
              <HistoryOffIcon className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Attach button: tall, narrow */}
        <button
          type="button"
          className="
            flex items-center justify-center
            bg-neutral-900 border border-purple-600
            rounded-lg
            px-0
            py-2
            h-full
            w-[42px]
            hover:bg-purple-950/30 transition
            text-purple-300
            focus:outline-none
            select-none
            shadow-sm
          "
          style={{
            minHeight: "90px", // Or match the Send button's actual height
          }}
          onClick={() => fileInputRef.current && fileInputRef.current.click()}
          aria-label="Attach file"
          tabIndex={0}
        >
          <Paperclip className="w-5 h-5" strokeWidth={2.2} />
        </button>

        {/* Send button: unchanged, big & square */}
        <button
          onClick={handleSubmit}
          className="
            bg-purple-700
            text-white
            px-6
            py-4
            rounded-lg
            hover:bg-purple-800
            h-full
          "
          style={{
            minHeight: "90px", // Or match the Send button's actual height
          }}
        >
          Send
        </button>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          style={{ display: "none" }}
          onChange={handleFileInputChange}
          multiple={false}
        />
      </div>
      </div>
    </div>
  );
};

export default ChatTab;
