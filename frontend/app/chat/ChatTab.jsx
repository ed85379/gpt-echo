"use client";
import React from "react";
import { useState, useEffect, useRef } from "react";
import { Remarkable } from 'remarkable';
import { Eye, EyeOff, EyeClosed, Tags, Shredder, SquareX } from 'lucide-react';
import { BookDashed, BookMarked, ArrowBigDownDash, } from 'lucide-react';
import { linkify } from 'remarkable/linkify';
import { useConfig } from '../hooks/ConfigContext';
import { assignMessageId } from '../utils/utils';
import { useMemo } from "react";
import MessageItem from "../components/MessageItem";
import { handleDelete, handleTogglePrivate, handleToggleRemembered } from "../utils/messageActions";
import { setProject, clearProject, addTag, removeTag } from "../utils/messageActions";


const ChatTab = ({ setSpeaking }) => {
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
  const { museProfile, museProfileLoading } = useConfig();
  const museName = museProfile?.name?.[0]?.content ?? "Muse";
  const INITIAL_RENDERED_MESSAGES = 10;  // On reload, after chat, etc.
  const ACTIVE_WINDOW_LIMIT = 10;         // After new message
  const SCROLLBACK_LIMIT = 30;            // After scroll up
  const MAX_RENDERED_MESSAGES = 30;      // Max after scroll loading "more"
  const MESSAGE_LIMIT = 10;              // How many to load per scroll/page
  const visibleMessages = messages.slice(-MAX_RENDERED_MESSAGES);
      // "Bind" each handler to local state
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
    window.speechSynthesis.cancel(); // (or your audio.stop())
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

const loadMessages = async (before = null) => {
  setLoadingMore(true);

  let prevScrollHeight = null;
  let prevScrollTop = null;

  // Only care about previous scroll position if loading history
  if (before && scrollContainerRef.current) {
    prevScrollHeight = scrollContainerRef.current.scrollHeight;
    prevScrollTop = scrollContainerRef.current.scrollTop;
  }

  let url = `/api/messages?limit=${INITIAL_RENDERED_MESSAGES}&sources=frontend&sources=reminder`;
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

function trimMessages(arr, limit) {
  return arr.slice(-limit);
}

function Paragraph({ children }) {
  // If the child is a <pre>, render it directly, don't wrap in <p>
  if (
    children &&
    React.Children.count(children) === 1 &&
    children[0]?.type === "pre"
  ) {
    return children[0];
  }
  return <p>{children}</p>;
}

    useEffect(() => {
      if (scrollToBottom) {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
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
            setMessages((prev) =>
              trimMessages([
                ...prev,
                {
                  from: "muse",
                  text,
                  message_id,
                  timestamp: new Date().toISOString(),
                }
              ], ACTIVE_WINDOW_LIMIT)
            );
            setScrollToMessageId(message_id);  // <-- Flag for scroll

            setLastTTS(text);
            setThinking(false);
            if (autoTTS) {
              //window.speechSynthesis.cancel(); // Cancel browser TTS if in use (optional, for browser TTS only)

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


function toPythonIsoString(date = new Date()) {
  // Pad milliseconds if needed
  const pad = (n, width = 2) => n.toString().padStart(width, '0');
  const yyyy = date.getUTCFullYear();
  const mm = pad(date.getUTCMonth() + 1);
  const dd = pad(date.getUTCDate());
  const hh = pad(date.getUTCHours());
  const min = pad(date.getUTCMinutes());
  const ss = pad(date.getUTCSeconds());
  const ms = pad(date.getUTCMilliseconds(), 3);

  // If you want microseconds, append '000' or use a polyfill
  return `${yyyy}-${mm}-${dd}T${hh}:${min}:${ss}.${ms}000+00:00`;
}

const handleSubmit = async () => {
  if (!input.trim()) return;

  const timestamp = toPythonIsoString();
  const role = "user";
  const source = "frontend";
  const message = input;

  // 1. Generate the message_id (async)
  const message_id = await assignMessageId({
    timestamp,
    role,
    source,
    message
  });

  // 2. Add to UI state immediately (so it’s taggable, traceable, etc.)
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
      timestamp,            // Add this line!
      message_id            // (optional, but recommended for full parity)
    }),
  });
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
    <div className="flex flex-col h-full space-y-4">
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

      <div
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto space-y-2"
          onScroll={async (e) => {
            const { scrollTop, scrollHeight, clientHeight } = e.target;
              if (scrollTop + clientHeight >= scrollHeight - 10) {
                setAtBottom(true);
              } else {
                setAtBottom(false);
              }
            if (scrollTop === 0 && hasMore && !loadingMore && messages.length > 0) {
              // Get the timestamp of the oldest message
              const oldest = messages[0]?.timestamp;
              if (oldest) {
                await loadMessages(oldest);
              }
            }
          }}
        >
      {!atBottom && (
      <div className="absolute bottom-24 left-1/2 transform -translate-x-1/2 z-50">
        <button
          className="bg-purple-700 text-white px-3 py-1 rounded-full shadow-lg hover:bg-purple-800 transition"
          onClick={() => {
            chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
          }}
        >
          <ArrowBigDownDash />
        </button>
      </div>
    )}

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
                          onToggleRemembered={onToggleRemembered}
                          onSetProject={onSetProject}
                          onClearProject={onClearProject}
                          onAddTag={onAddTag}
                          onRemoveTag={onRemoveTag}
                      />
                  );
                }
            )}


        {thinking && (
          <div className="text-sm text-neutral-500 italic">
            {museName} is thinking...
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
          className="flex-1 p-2 rounded-lg bg-neutral-800 text-white resize-none border border-neutral-700 focus:border-purple-500 focus:outline-none"
          placeholder={`Say something to ${museName}...`}
        />
        <button
          onClick={handleSubmit}
          className="bg-purple-700 text-white px-4 py-2 rounded-lg hover:bg-purple-800"
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatTab;
