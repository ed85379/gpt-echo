"use client";

import { useState, useEffect, useRef } from "react";
import { Remarkable } from 'remarkable';
import { Eye } from 'lucide-react';
import { EyeOff } from 'lucide-react';
import { EyeClosed } from 'lucide-react';
import { Tags } from 'lucide-react';
import { Shredder } from 'lucide-react';
import { SquareX } from 'lucide-react';
import { linkify } from 'remarkable/linkify';
import { useConfig } from '../hooks/ConfigContext';
import { assignMessageId } from '../utils/utils';

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
  const chatEndRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const audioCtxRef = useRef(null);
  const audioSourceRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const { museProfile, museProfileLoading } = useConfig();
  const museName = museProfile?.name?.[0]?.content ?? "Muse";

const md = new Remarkable({
  html: false, // Don’t allow raw HTML from LLM
  breaks: true, // Soft line breaks
  linkTarget: "_blank",
  typographer: true,
});
md.use(linkify);

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

    const MESSAGE_LIMIT = 10;

const loadMessages = async (before = null) => {
  setLoadingMore(true);

  let prevScrollHeight = null;
  let prevScrollTop = null;

  // Only care about previous scroll position if loading history
  if (before && scrollContainerRef.current) {
    prevScrollHeight = scrollContainerRef.current.scrollHeight;
    prevScrollTop = scrollContainerRef.current.scrollTop;
  }

  let url = `/api/messages?limit=${MESSAGE_LIMIT}&sources=frontend&sources=reminder`;
  if (before) url += `&before=${encodeURIComponent(before)}`;
  const res = await fetch(url);
  const data = await res.json();

  if (before) {
    setMessages(prev => [...data.messages, ...prev]);
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
    setMessages(data.messages);
    setScrollToBottom(true); // Scroll when loading initial/latest
  }
  if (data.messages.length < MESSAGE_LIMIT) setHasMore(false);
  setLoadingMore(false);
};


    useEffect(() => {
      loadMessages();
      // eslint-disable-next-line
    }, []);

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
            setMessages((prev) => [
              ...prev,
              {
                from: "muse",
                text,
                message_id,
                timestamp: new Date().toISOString(),
              }
            ]);

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

    function handleDelete(message_id, markDeleted) {
      setScrollToBottom(false);
      fetch("/api/tag_message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_ids: [message_id], is_deleted: markDeleted })
      })
      .then(() => {
        // Update your message state/UI to reflect deletion
        setMessages(prev =>
          prev.map(m =>
            m.message_id === message_id ? { ...m, is_deleted: markDeleted } : m
          )
        );
      });
    }

    function handleTogglePrivate(message_id, makePrivate) {
      setScrollToBottom(false);
      fetch("/api/tag_message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_ids: [message_id], is_private: makePrivate })
      })
      .then(() => {
        // Update your message state/UI to reflect privacy
        setMessages(prev =>
          prev.map(m =>
            m.message_id === message_id ? { ...m, is_private: makePrivate } : m
          )
        );
      });
    }

    function handleToggleRemembered(message_id, makeRemembered) {
    setScrollToBottom(false);
    fetch("/api/tag_message", {
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
      setScrollToBottom(false);
      fetch("/api/tag_message", {
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
      setScrollToBottom(false);
      fetch("/api/tag_message", {
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
  setMessages(prev => [
    ...prev,
    {
      id: message_id,         // for React keys, etc.
      message_id,             // for backend/db
      text: message,
      timestamp,
      role,
      source,
    }
  ]);

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
            const { scrollTop } = e.target;
            if (scrollTop === 0 && hasMore && !loadingMore && messages.length > 0) {
              // Get the timestamp of the oldest message
              const oldest = messages[0]?.timestamp;
              if (oldest) {
                await loadMessages(oldest);
              }
            }
          }}
        >
  {!hasMore && (
    <div className="text-sm text-neutral-400 italic text-center mt-2">
      That’s the beginning. Want more? <a href="/memory" className="underline">Visit the Memory Page</a>
    </div>
  )}
        {connecting && (
          <div className="text-sm text-neutral-400">Reconnecting…</div>
        )}
        {messages.map((msg, idx) => {
          let renderedHTML = "";
          try {
            renderedHTML = md.render((msg.text || "").trim());
          } catch (e) {
            renderedHTML = "<em>[Failed to render markdown]</em>";
            console.error("Remarkable error:", e, msg.text);
          }


          const isPrivate = !!msg.is_private;
          const isRemembered = !!msg.remembered;
          const isDeleted = !!msg.is_deleted;
          const userTags = msg.user_tags?.filter(t => t !== "private" && t !== "deleted" && t !== "remembered") || [];
          const bubbleWidth = "max-w-[80%]";
          // Determine alignment for user vs. muse
          const rightAlign = msg.from === "user" || msg.role === "user";

          return (
                    <div
                      key={idx}
                      className={`space-y-1 flex flex-col ${rightAlign ? "items-end" : "items-start"}`}
                    >
                  {/* Metadata + bubble container, shares max-width and ml-auto for right-aligned */}
                  <div className={`${bubbleWidth} ${rightAlign ? "ml-auto" : ""}`}>
                    {/* Metadata always left-aligned within container */}
                    <div className="text-xs text-neutral-400">{rightAlign ? "You" : museName}</div>
                    <div className="text-xs text-neutral-500">{formatTimestamp(msg.timestamp)}</div>

              {/* Bubble container with relative and group */}
                <div
                  className={`relative group text-sm px-3 py-2 rounded-lg whitespace-pre-wrap ${
                    rightAlign
                      ? "bg-neutral-800 text-white self-start" // self-start makes it left-aligned in the flex-col
                      : "bg-purple-950 text-purple-100"
                  }`}
                >
                  <div
                    className="prose prose-invert max-w-none"
                    dangerouslySetInnerHTML={{ __html: renderedHTML }}
                  />

                  {/* Tagging bar (appears on hover) */}
                  <div className="absolute bottom-2 right-3 hidden group-hover:flex gap-2 z-10">
                    <button
                      onClick={() => setTagDialogOpen(msg.message_id)}
                      title="Tag message"
                      className="text-neutral-400 hover:text-purple-300 transition-colors"
                      style={{ background: "none", border: "none", cursor: "pointer" }}
                    >
                      <Tags size={18} />
                    </button>
                    {/* Remembered toggle */}
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
                    {/* Private toggle */}
                    <button
                      onClick={() => handleTogglePrivate(msg.message_id, !isPrivate)}
                      title={isPrivate ? "Set as public" : "Mark as private"}
                      className={`transition-colors ${isPrivate ? "text-purple-400" : "text-neutral-400"} hover:text-purple-300`}
                      style={{ background: "none", border: "none", cursor: "pointer" }}
                    >
                      {isPrivate ? <EyeClosed size={18} /> : <Eye size={18} />}
                    </button>
                    {/* Delete */}
                    <button
                      onClick={() => handleDelete(msg.message_id, !isDeleted)}
                      title={isDeleted ? "Undelete message" : "Delete message"}
                      className="text-neutral-400 hover:text-red-400 transition-colors"
                      style={{ background: "none", border: "none", cursor: "pointer" }}
                    >
                      {isDeleted ? <SquareX size={18} /> : <Shredder size={18} />}
                    </button>
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
                  {isPrivate && (
                    <span className="bg-neutral-700 text-xs text-purple-300 px-2 py-0.5 rounded-full flex items-center gap-1">
                      <EyeOff size={14} className="inline" /> Private
                    </span>
                  )}
                  {isRemembered && (
                      <span className="bg-neutral-700 text-xs text-purple-300 px-2 py-0.5 rounded-full flex items-center gap-1">
                          <CandleHolderLit size={14} className="inline" /> Remembered
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
