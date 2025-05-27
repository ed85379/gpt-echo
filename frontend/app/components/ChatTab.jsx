"use client";

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";

const ChatTab = ({ setSpeaking }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [autoTTS, setAutoTTS] = useState(false);
  const [lastTTS, setLastTTS] = useState(null);
  const [museName, setMuseName] = useState("Muse");
  const [thinking, setThinking] = useState(false);
  const [connecting, setConnecting] = useState(true);
  const [isTTSPlaying, setIsTTSPlaying] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [scrollToBottom, setScrollToBottom] = useState(true);



  const chatEndRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const audioCtxRef = useRef(null);
  const audioSourceRef = useRef(null);
  const scrollContainerRef = useRef(null);


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

  let url = `http://localhost:5000/api/messages?limit=${MESSAGE_LIMIT}`;
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


  // Fetch Muse profile for name
  useEffect(() => {
    fetch("http://localhost:5000/api/profile")
      .then((res) => res.json())
      .then((data) => {
        const profile = JSON.parse(data.profile);
        setMuseName(profile.name || "Muse");
      });
  }, []);

  // WebSocket with auto-reconnect
  useEffect(() => {
    let cancelled = false;
    function connectWebSocket() {
      setConnecting(true);
      const ws = new WebSocket("ws://localhost:5000/ws");
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
            setMessages((prev) => [
              ...prev,
              {
                from: "muse",
                text,
                timestamp: new Date().toISOString(),
              }
            ]);

            setLastTTS(text);
            setThinking(false);
            if (autoTTS) {
              window.speechSynthesis.cancel(); // Cancel browser TTS if in use (optional, for browser TTS only)
              setIsTTSPlaying(true);
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


  const handleSubmit = async () => {
    if (!input.trim()) return;
    setMessages((prev) => [
      ...prev,
      {
        from: "user",
        text: input,
        timestamp: new Date().toISOString(),
      }
    ]);
    setInput("");
    setThinking(true);
    await fetch("http://localhost:5000/api/talk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: input }),
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

          const response = await fetch("http://localhost:5000/api/tts/stream", {
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
      <div className="flex gap-2 items-center">
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
              setIsTTSPlaying(true);
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
        {messages.map((msg, idx) => (
          <div key={idx} className="space-y-1">
            <div className="text-xs text-neutral-400">
              {msg.from === "user" ? "You" : museName}
            </div>
            <div className="text-xs text-neutral-500">
              {formatTimestamp(msg.timestamp)}
            </div>
            <div
              className={`text-sm px-3 py-2 rounded-lg max-w-[80%] whitespace-pre-wrap ${
                msg.from === "user"
                  ? "bg-neutral-800 text-white self-end ml-auto"
                  : "bg-purple-950 text-purple-100"
              }`}
            >
              <div className="prose prose-invert max-w-none">
                <ReactMarkdown
                  components={{
                    code({ node, inline, children, ...props }) {
                      return inline ? (
                        <code className="bg-neutral-800 text-purple-300 px-1 py-0.5 rounded text-sm">
                          {children}
                        </code>
                      ) : (
                        <pre className="bg-neutral-900 text-purple-100 p-4 rounded-lg overflow-x-auto">
                          <code>{children}</code>
                        </pre>
                      );
                    }
                  }}
                >
                  {msg.text}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        ))}
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
          className="flex-1 p-2 rounded-lg bg-neutral-800 text-white resize-none"
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
