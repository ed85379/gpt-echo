"use client";
import { useState, useEffect } from "react";

const ProjectFacts = ({ project }) => {
  const [cortex, setCortex] = useState([]);
  const [editMode, setEditMode] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!project) return;
    const params = new URLSearchParams({
      type: "fact",
      project_id: project._id
    }).toString();

    fetch(`/api/cortex/query?${params}`)
      .then(res => res.json())
      .then(data => {
        setCortex(data); // Flat array from API
      });
  }, [project._id]);

  // --- Keep these handlers as-is (just use entry._id now) ---
  const getDisplayDate = (entry) => {
    const dateVal = entry.created_at || entry.timestamp;
    if (!dateVal) return "—";
    try {
      const iso = typeof dateVal === "string"
        ? dateVal
        : dateVal.toISOString
        ? dateVal.toISOString()
        : String(dateVal);
      return new Date(iso).toLocaleString();
    } catch {
      return String(dateVal);
    }
  };

  const handleDelete = (entryId) => {
    if (!window.confirm("Are you sure you want to delete this entry?")) return;
    fetch(`/api/cortex/${entryId}`, {
      method: "DELETE",
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "ok") {
          setCortex((prev) => prev.filter(e => e._id !== entryId));
        }
      });
  };

  const handleEdit = (entryId, newText) => {
    fetch(`/api/cortex/${entryId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: newText }),
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === "ok") {
          setCortex(prev => prev.map(e =>
            e._id === entryId ? { ...e, text: newText, updated: new Date().toISOString() } : e
          ));
        }
      });
  };

  // --- Filter entries for search ---
  const entries = (Array.isArray(cortex) ? cortex : []).filter(
    entry => !search || (entry.text && entry.text.toLowerCase().includes(search.toLowerCase()))
  );

  // --- Render UI (as in my last message) ---
  return (
    <div className="p-6 text-white bg-neutral-950 overflow-y-auto">
      {/* Search and Edit Mode Controls */}
      <div className="flex items-center gap-2 mb-3">
        <input
          type="text"
          placeholder="Search"
          className="bg-neutral-900 text-neutral-200 px-2 py-1 rounded text-xs border border-neutral-700"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div className="flex items-center gap-2">
          <span className={editMode ? "text-neutral-400" : "font-bold text-purple-400"}>Read Only</span>
          <button
            className={`relative inline-block w-12 h-6 rounded-full transition-colors duration-300
              ${editMode ? "bg-purple-600" : "bg-neutral-700"}`}
            onClick={() => setEditMode(e => !e)}
            aria-label="Toggle Edit Mode"
          >
            <span className={`absolute left-1 top-1 w-4 h-4 rounded-full bg-white transition-transform duration-300
              ${editMode ? "translate-x-6" : ""}`}/>
          </button>
          <span className={editMode ? "font-bold text-purple-400" : "text-neutral-400"}>Edit Entries</span>
        </div>
      </div>

      {/* Facts List */}
      <div className="space-y-2">
        {entries.length === 0 && (
          <div className="text-neutral-500 text-sm italic">
            No facts found for this project.
          </div>
        )}
        {entries.map(entry => (
          <div key={entry._id} className="bg-neutral-900 rounded px-4 py-2 border border-neutral-700">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-semibold">
                  {(entry.text || "").slice(0, 120)}
                  {(entry.text || "").length > 120 && "…"}
                </div>
                <div className="text-xs text-neutral-400">
                  <span className="text-xs text-neutral-500">
                    Added: {getDisplayDate(entry)}
                  </span>
                  {entry.updated && ` | Edited: ${new Date(entry.updated).toLocaleString()}`}
                </div>
              </div>
              {editMode && (
                <button
                  className="ml-2 px-2 py-1 rounded bg-red-900 text-white text-xs"
                  onClick={() => handleDelete(entry._id)}
                >
                  Delete
                </button>
              )}
            </div>
            {editMode && (
              <textarea
                defaultValue={entry.text}
                className="w-full bg-neutral-800 text-white rounded mt-2 p-2 text-sm border border-neutral-700"
                rows={2}
                onBlur={e => {
                  if (e.target.value !== entry.text) {
                    handleEdit(entry._id, e.target.value);
                  }
                }}
              />
            )}
            {/* Tags and Metadata */}
            {(Array.isArray(entry.tags) && entry.tags.length > 0) || (entry.metadata && Object.keys(entry.metadata).length > 0) ? (
              <div className="flex flex-wrap items-center gap-4 mt-2">
                {Array.isArray(entry.tags) && entry.tags.length > 0 && (
                  <div className="flex gap-2 items-center">
                    <span className="text-xs text-neutral-400">Tags:</span>
                    {entry.tags.map(tag => (
                      <span key={tag} className="px-2 py-0.5 rounded bg-purple-900 text-purple-200 text-xs font-mono">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                {entry.metadata && Object.keys(entry.metadata).length > 0 && (
                  <div className="flex gap-2 items-center">
                    <span className="text-xs text-neutral-400">Meta:</span>
                    <span className="text-xs text-neutral-300 font-mono">
                      {Object.entries(entry.metadata)
                        .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`)
                        .join(" | ")}
                    </span>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ProjectFacts;