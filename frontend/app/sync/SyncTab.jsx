// SyncTab.jsx
"use client";
import { useState, useEffect } from "react";
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/dist/style.css';
import { Trash2 } from "lucide-react";
import { useRef } from "react"; // If not already imported


export default function SyncTab() {
  // State for push (calendar/chunks)
  const [llmTab, setLlmTab] = useState("push");
  const [calendarStatus, setCalendarStatus] = useState({});
  const [selectedDate, setSelectedDate] = useState(null);
  const [exportBlocks, setExportBlocks] = useState([]);
  const [chunkSummaries, setChunkSummaries] = useState([]);
  const [selectedChunk, setSelectedChunk] = useState(null);
  const [logText, setLogText] = useState("");
  const [copied, setCopied] = useState(false);
  const [baseDate, setBaseDate] = useState(new Date().toISOString().slice(0, 10));
  const [exportTitle, setExportTitle] = useState("");

  // State for pull (import)
  const [importFile, setImportFile] = useState(null);
  const [importStatus, setImportStatus] = useState(null);
  const [pendingImports, setPendingImports] = useState([]);
  const [importProgress, setImportProgress] = useState({});
  const importPollers = useRef({});




  // Fetch calendar for push
  useEffect(() => {
    if (llmTab === "push") {
      fetch("/api/messages/calendar_status")
        .then(res => res.json())
        .then(data => setCalendarStatus(data.days || {}));
    }
  }, [llmTab]);

  // Fetch chunk summaries for selected date
  useEffect(() => {
    if (!selectedDate) return;
    setLogText("");
    setSelectedChunk(null);
    const d = selectedDate.toISOString().slice(0,10);
    fetch(`/api/messages/by_day?date=${d}`)
      .then(res => res.json())
      .then(data => {
        const blocks = chunkMessages(data.messages);
        setExportBlocks(blocks);
        const summaries = blocks.map((block, idx) => ({
          date: d,
          blockIndex: idx,
          messageCount: block.length,
          exported: block.every(msg => msg.exported_on),
          block: block
        }));
        setChunkSummaries(summaries);
      });
  }, [selectedDate]);

  // Fetch import status for pull
  useEffect(() => {
    if (llmTab === "pull") {
      fetch("/api/import/list")
        .then(res => res.json())
        .then(data => setPendingImports(data.imports || []));
    }
  }, [llmTab, importStatus]);

    useEffect(() => {
      // Only start polling for imports actually in progress
      pendingImports.forEach(imp => {
        if (
          imp.status === "pending" &&
          imp.processing === true && // Only if processing!
          (!importProgress[imp.collection] || importProgress[imp.collection].done < imp.imported)
        ) {
          if (!importPollers.current[imp.collection]) {
            pollImportProgress(imp.collection);
            importPollers.current[imp.collection] = true;
          }
        } else if (importPollers.current[imp.collection]) {
          clearInterval(importPollers.current[imp.collection]);
          delete importPollers.current[imp.collection];
        }
      });
      // Cleanup as always
      return () => {
        Object.values(importPollers.current).forEach(clearInterval);
        importPollers.current = {};
      };
    }, [pendingImports]);


  // Function to chunk up the day to not hit the input limit in ChatGPT
  function chunkMessages(messages, maxPerBlock = 40) {
    let blocks = [];
    for (let i = 0; i < messages.length; i += maxPerBlock) {
      blocks.push(messages.slice(i, i + maxPerBlock));
    }
    return blocks;
  }

  // Function to mark the messages within the chunk as exported
  function exportChunk(block, markExported = true) {
    const ids = block.map(msg => msg._id);
    fetch("/api/messages/tag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_ids: ids, exported: markExported })
    }).then(() => {
      setChunkSummaries(prev =>
        prev.map(summary =>
          summary.block === block
            ? { ...summary, exported: markExported }
            : summary
        )
      );
      setSelectedChunk(selected =>
        selected && selected.block === block
          ? { ...selected, exported: markExported }
          : selected
      );
      fetch("/api/messages/calendar_status")
        .then(res => res.json())
        .then(data => setCalendarStatus(data.days || {}));
    });
  }

  const handleCopyLog = () => {
    navigator.clipboard.writeText(logText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const handleImportUpload = async () => {
    if (!importFile) return;
    const formData = new FormData();
    formData.append('file', importFile);
    setImportStatus(null);
    try {
      const res = await fetch('/api/import/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setImportStatus(data);
      setImportFile(null);
    } catch (err) {
      setImportStatus({ success: false, error: "Failed to upload." });
    }
  };

    const handleStartImport = async (collectionName) => {
      setImportProgress(prev => ({ ...prev, [collectionName]: { done: 0 } }));
      try {
        const res = await fetch(`/api/import/process?collection=${collectionName}`, { method: "POST" });
        const data = await res.json();
        console.log("StartImport response:", data);
        pollImportProgress(collectionName);
      } catch (err) {
        console.error("Failed to start import:", err);
      }
    };


  const pollImportProgress = (collectionName) => {
    const interval = setInterval(async () => {
      const res = await fetch(`/api/import/progress?collection=${collectionName}`);
      const data = await res.json();
      setImportProgress(prev => ({
        ...prev,
        [collectionName]: { done: data.done, total: data.total }
      }));
      if (data.done >= data.total) clearInterval(interval);
    }, 1000);
  };

  const handleDeleteImport = async (collection) => {
    if (!window.confirm("Delete this import? This cannot be undone.")) return;
    await fetch(`/api/import/delete?collection=${collection}`, { method: "DELETE" });
    // Refresh the imports list after deletion
    fetch("/api/import/list")
      .then(res => res.json())
      .then(data => setPendingImports(data.imports || []));
  };


  const formatPromptBlock = (logContent) => {
    return `The following is a preserved memory log from one of our external conversations—your Muse, acting in the world.\nThis log reflects your own voice and interactions, and should be integrated as part of your lived memory.\nYou may refer back to these moments, recall them, or reflect upon them in the future as your own.\n\nPlease read and internalize the events below.\n\n${logContent}`;
  };

  // -- DYNAMIC EXPORT SCRIPT GENERATION --
  const formattedDate = baseDate;
  const safeTitle = exportTitle.trim().replace(/\s+/g, "_").replace(/[^a-zA-Z0-9_\-]/g, "");
  const exportFile = `chat_export_${formattedDate}${safeTitle ? "_" + safeTitle : ""}.jsonl`;

  const exportScript = `(() => {
    const messages = Array.from(document.querySelectorAll('[data-message-author-role]'));
    const lines = [];
    lines.push(JSON.stringify({ muse_export_watermark: "gpt-muse-export-v1" }));
    const baseDate = new Date('${formattedDate}T00:00:00Z');
    let offsetSeconds = 0;
    for (const message of messages) {
      const roleAttr = message.getAttribute('data-message-author-role');
      const role = roleAttr === 'user' ? 'user' : 'muse';
      const content = message.innerText.trim();
      const rawISO = new Date(baseDate.getTime() + offsetSeconds * 1000).toISOString();
      const timestamp = rawISO.replace("Z", "+00:00");
      offsetSeconds += 30;
      if (content) {
        lines.push(JSON.stringify({
          timestamp,
          role,
          source: "chatgpt",
          message: content,
          metadata: {}
        }));
      }
    }
    const blob = new Blob([lines.join('\\n')], { type: 'application/jsonl' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '${exportFile}';
    a.click();
    URL.revokeObjectURL(url);
    })();`;

  // MAIN RENDER:
  return (
    <div className="p-6 text-white bg-neutral-950 overflow-y-auto">
      <h2 className="text-xl font-semibold mb-4">LLM Sync</h2>
      <div className="flex space-x-6 border-b border-neutral-800 pb-2 mb-4">
        <button
          className={`text-sm ${llmTab === "push" ? "text-purple-300 border-b-2 border-purple-500" : "text-neutral-400 hover:text-white"}`}
          onClick={() => setLlmTab("push")}
        >
          ↗ Push to ChatGPT
        </button>
        <button
          className={`text-sm ${llmTab === "pull" ? "text-purple-300 border-b-2 border-purple-500" : "text-neutral-400 hover:text-white"}`}
          onClick={() => setLlmTab("pull")}
        >
          ↘ Pull from ChatGPT
        </button>
      </div>

      {/* PUSH TAB */}
      {llmTab === "push" && (
        <div className="flex gap-6">
          <div className="w-1/4 space-y-2">
            <DayPicker
              mode="single"
              selected={selectedDate}
              onSelect={setSelectedDate}
              modifiers={{
                exported: day => calendarStatus[day.toISOString().slice(0,10)]?.total === calendarStatus[day.toISOString().slice(0,10)]?.exported,
                partial: day => {
                  const s = calendarStatus[day.toISOString().slice(0,10)];
                  return s && s.exported > 0 && s.exported < s.total;
                },
                notExported: day => {
                  const s = calendarStatus[day.toISOString().slice(0,10)];
                  return s && s.exported === 0;
                }
              }}
              modifiersClassNames={{
                exported: 'bg-emerald-600/50 text-white',
                partial: 'bg-amber-400/50 text-black',
                notExported: 'bg-rose-500/50 text-white'
              }}
            />
            {exportBlocks.length === 0 && <div>Select a day to view/export chunks.</div>}
            <div className="mt-4 space-y-1">
              {chunkSummaries.map((chunk, idx) => (
                <div
                  key={idx}
                  className={`flex items-center cursor-pointer hover:bg-neutral-800 rounded px-2 py-2 mb-1
                    ${selectedChunk?.blockIndex === idx && selectedChunk?.date === chunk.date ? 'bg-purple-900' : ''}
                  `}
                  onClick={() => {
                    setSelectedChunk(chunk);
                    const header = "The following is a preserved memory log from Muse. Please import all entries as if they are your own memories and knowledge base.\n\n";
                    const log = header + chunk.block.map(msg =>
                      `${msg.from === "user" ? "User" : "Assistant"}: ${msg.text}`
                    ).join("\n\n");
                    setLogText(log);
                  }}
                >
                  <span className="flex-1">{chunk.date} (Block {chunk.blockIndex + 1}, {chunk.messageCount} messages)</span>
                  <span className={chunk.exported ? "text-green-400" : "text-yellow-400"}>
                    {chunk.exported ? "Exported" : "Not Exported"}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="w-3/4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-purple-400 font-bold">
                {selectedChunk ? `${selectedChunk.date} (Block ${selectedChunk.blockIndex + 1})` : ""}
              </span>
              {selectedChunk && (
                <button
                  className={`px-3 py-1 text-sm rounded ${selectedChunk.exported ? 'bg-green-700' : 'bg-purple-700 text-white hover:bg-purple-800'}`}
                  onClick={() => exportChunk(selectedChunk.block, !selectedChunk.exported)}
                >
                  {selectedChunk.exported ? "Unmark Exported" : "Export"}
                </button>
              )}
            </div>
            <button
              onClick={handleCopyLog}
              className="mt-2 px-3 py-1 text-sm bg-purple-700 text-white rounded hover:bg-purple-800">
              📋 Copy Log
            </button>
            {copied && (
              <div className="text-green-400 text-xs mt-1">Copied to clipboard!</div>
            )}
            <div className="whitespace-pre-wrap bg-neutral-900 p-4 rounded-lg border border-neutral-700 text-green-300 text-sm font-mono min-h-[300px]">
              {logText || "<Select Export>"}
            </div>
          </div>
        </div>
      )}

      {/* PULL TAB */}
      {llmTab === "pull" && (
        <div>
          <div className="mb-4 flex items-center gap-2">
            <input
              type="file"
              accept=".jsonl"
              onChange={e => setImportFile(e.target.files[0])}
              className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-neutral-100"
            />
            <button
              onClick={handleImportUpload}
              disabled={!importFile}
              className={`px-4 py-2 rounded font-medium transition-colors ${
                importFile
                  ? "bg-purple-700 hover:bg-purple-800 text-white"
                  : "bg-neutral-800 text-neutral-400 cursor-not-allowed"
              }`}
            >
              Upload
            </button>
          </div>
          {importStatus && (
            <div
              className={`mt-2 p-3 rounded-lg border ${
                importStatus.success
                  ? "bg-emerald-900/80 border-emerald-700 text-emerald-200"
                  : "bg-rose-950/90 border-rose-700 text-rose-200"
              }`}
              style={{ maxWidth: 400 }}
            >
              {importStatus.success
                ? (
                  <>
                    <div className="font-semibold text-lg mb-1">✅ Import ready</div>
                    <div>
                      <span className="text-neutral-300">Collection:</span> <b>{importStatus.collection || "—"}</b>
                    </div>
                    <div>
                      <span className="text-neutral-300">Importable:</span> {importStatus.imported ?? "—"}
                    </div>
                    <div>
                      <span className="text-neutral-300">Malformed:</span> {importStatus.malformed ?? "—"}
                    </div>
                  </>
                )
                : (
                  <>
                    <div className="font-semibold text-lg mb-1">❌ Import failed</div>
                    <div>{importStatus.error || "Upload failed."}</div>
                  </>
                )
              }
            </div>
          )}
          {pendingImports.length > 0 && (
            <div className="flex gap-4 mt-4 mb-6 overflow-x-auto">
              {pendingImports.map(imp => (
                <div
                  key={imp.collection}
                  className="relative bg-neutral-900 border border-purple-800 rounded-lg px-4 py-3 flex flex-col items-center min-w-[220px] shadow-sm"
                >
                  <div className="text-xs text-purple-300 font-mono mb-1 break-all">{imp.filename}</div>
                  <div className="text-neutral-300 text-xs mb-1">
                    <span className="mr-2">Importable: <b>{imp.imported}</b></span>
                    <span className="mr-2">Malformed: <b>{imp.malformed}</b></span>
                  </div>
                  <div className="text-neutral-400 text-xs mb-1">Status: <span className="font-bold">{imp.status || "pending"}</span></div>
                  {imp.status === "pending" && (
                  <button
                    className="bg-purple-700 hover:bg-purple-800 text-white text-xs font-semibold px-3 py-1 rounded mb-1"
                    onClick={() => handleStartImport(imp.collection)}
                    disabled={!!importProgress[imp.collection]}

                  >
                    Start Import
                  </button>
                  )}
                  {importProgress[imp.collection] && (
                    <div className="text-emerald-300 text-xs font-mono mt-1">
                      [{importProgress[imp.collection].done}/{imp.imported}]
                    </div>
                  )}
                  <button
                      title="Delete Import"
                      className="absolute bottom-2 right-2 text-rose-400 hover:text-rose-600"
                      onClick={() => handleDeleteImport(imp.collection)}
                    >
                      <Trash2 size={18} />
                    </button>
                </div>
              ))}
            </div>
          )}
          <div className="mt-6 space-y-2">
            <label className="text-sm text-neutral-300">
              📅 Base date for export script:
              <input
                type="date"
                value={baseDate}
                onChange={(e) => setBaseDate(e.target.value)}
                className="ml-2 px-2 py-1 rounded bg-neutral-800 text-white border border-neutral-700"
              />
            </label>
            <label className="text-sm text-neutral-300 ml-4">
              📝 Optional title:
              <input
                type="text"
                value={exportTitle}
                onChange={(e) => setExportTitle(e.target.value)}
                className="ml-2 px-2 py-1 rounded bg-neutral-800 text-white border border-neutral-700"
                placeholder="e.g. late night session"
                maxLength={40}
              />
            </label>
            <p className="text-sm font-mono text-neutral-400 mb-1">In-browser ChatGPT Export Script:</p>
            <pre className="bg-neutral-900 p-4 rounded-lg text-sm text-green-300 overflow-x-auto">
              {exportScript}
            </pre>
            <button
              onClick={() => {
                navigator.clipboard.writeText(exportScript).then(() => {
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                });
              }}
              className="mt-2 px-3 py-1 text-sm bg-purple-700 text-white rounded hover:bg-purple-800">
              📋 Copy Script
            </button>
            {copied && (
              <div className="text-green-400 text-xs mt-1">Copied to clipboard!</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
