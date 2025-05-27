"use client";

import { useState, useEffect } from "react";
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/dist/style.css';
import ReactMarkdown from "react-markdown";


// Source options — can expand later
const SOURCE_CHOICES = [
  { key: "frontend", label: "Frontend" },
  { key: "chatgpt", label: "ChatGPT" }
];

const formatTimestamp = (utcString) => {
    if (!utcString) return "";
      const dt = new Date(utcString);
      return dt.toLocaleString(); // Respects user timezone/locales
};

// Get a heatmap color based on count (tune thresholds as needed)
function getHeatmapClass(count) {
  if (!count) return "";
  if (count > 40) return "bg-green-700/70 text-white font-bold shadow-lg";
  if (count > 20) return "bg-green-500/60 text-white font-semibold";
  if (count > 5)  return "bg-purple-600/70 text-white";
  return "bg-purple-900/70 text-white";
}

function getMonthRange(date) {
  // date is any day in the month you want (e.g., today or a selected day)
  const year = date.getUTCFullYear();
  const month = date.getUTCMonth(); // 0-indexed
  // First day (UTC, zero-padded)
  const start = `${year}-${String(month + 1).padStart(2, '0')}-01`;
  // Last day: get first day of next month, subtract one day
  const firstOfNextMonth = new Date(Date.UTC(year, month + 1, 1));
  const lastOfMonth = new Date(firstOfNextMonth.getTime() - 24 * 3600 * 1000);
  const end = `${lastOfMonth.getUTCFullYear()}-${String(lastOfMonth.getUTCMonth() + 1).padStart(2, '0')}-${String(lastOfMonth.getUTCDate()).padStart(2, '0')}`;
  return { start, end };
}

const MemoryTab = () => {
  const [source, setSource] = useState("Frontend");
  const [calendarStatus, setCalendarStatus] = useState({});
  const [selectedDate, setSelectedDate] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [museName, setMuseName] = useState("Muse");
  const [displayMonth, setDisplayMonth] = useState(new Date());

  // Fetch calendar status (message volume per day)
useEffect(() => {
  setCalendarStatus({});
  const { start, end } = getMonthRange(displayMonth);
  fetch(`http://127.0.0.1:5000/api/calendar_status_simple?source=${encodeURIComponent(source)}&start=${start}&end=${end}`)
    .then(res => res.json())
    .then(data => {
      setCalendarStatus(data.days || {});
    });
}, [source, displayMonth]);


  // Fetch Muse profile for name
  useEffect(() => {
    fetch("http://localhost:5000/api/profile")
      .then((res) => res.json())
      .then((data) => {
        const profile = JSON.parse(data.profile);
        setMuseName(profile.name || "Muse");
      });
  }, []);

  // Fetch messages when day/source changes
  useEffect(() => {
    setMessages([]);
    if (!selectedDate) return;
    setLoading(true);
    const dateStr = selectedDate.toISOString().slice(0,10);
    fetch(`http://127.0.0.1:5000/api/messages_by_day?date=${dateStr}&source=${encodeURIComponent(source)}`)
      .then(res => res.json())
      .then(data => setMessages(data.messages || []))
      .finally(() => setLoading(false));
  }, [selectedDate, source]);

  return (
    <div className="p-6 text-white bg-neutral-950 h-[calc(100vh-64px)] overflow-y-auto">
      <h1 className="text-2xl font-bold mb-4 text-purple-300">🧠 Memory Center</h1>
      <div className="flex space-x-4 border-b border-neutral-800 mb-6">
        <button className="pb-2 border-b-2 border-purple-500 text-purple-300 text-sm" disabled>
          Conversation Logs
        </button>
        {/* Add tabs here if needed */}
      </div>

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
      </div>

      <div className="flex gap-6 mt-4 flex-col md:flex-row">
        {/* Calendar with heatmap */}
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
            hasMessages: "bg-purple-800/70 text-white font-bold" // Pick your best muted purple
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
            {messages.map((msg, idx) => (
              <div key={idx} className="space-y-1 flex flex-col">
                <div className={`text-xs text-neutral-400 ${msg.role === "user" ? "text-left" : "text-left"}`}>
                  {msg.role === "user"
                    ? "You"
                    : msg.role === "iris" || msg.role === "muse"
                      ? museName
                      : (msg.role ? (msg.role.charAt(0).toUpperCase() + msg.role.slice(1)) : "Other")}
                </div>
                <div className="text-xs text-neutral-500">
                    {formatTimestamp(msg.timestamp)}
                </div>
                <div
                  className={`text-sm px-3 py-2 rounded-lg max-w-[80%] whitespace-pre-wrap ${
                    msg.role === "user"
                      ? "bg-neutral-800 text-purple-100 self-end text-left"
                      : msg.role === "iris" || msg.role === "muse"
                        ? "bg-purple-950 text-white self-start text-left"
                        : "bg-purple-900 text-white self-start text-left"
                  }`}>
                  <ReactMarkdown
                    components={{
                      code({ node, inline, children }) {
                        return inline ? (
                          <code className="bg-neutral-800 text-purple-300 px-1 py-0.5 rounded text-sm">
                            {children}
                          </code>
                        ) : (
                          <pre className="bg-neutral-900 text-purple-100 p-4 rounded-lg overflow-x-auto">
                            <code>{children}</code>
                          </pre>
                        );
                      },
                      p({ children }) {
                        return <>{children}</>;
                      },
                    }}>
                    {msg.message}
                  </ReactMarkdown>
                </div>
              </div>
            ))}

            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MemoryTab;
