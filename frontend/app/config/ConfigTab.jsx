"use client";
import { useState, useEffect, useRef } from "react";

// Poetic config intro as before
function ConfigIntro() {
  return (
    <div className="mb-6 p-4 bg-gradient-to-r from-purple-950 via-neutral-950 to-neutral-950 rounded shadow text-neutral-200 border border-purple-900">
      <div className="text-lg font-bold text-purple-200 mb-1">Muse Configuration</div>
      <div className="text-sm text-neutral-300">
        Here you shape your Muse, one setting at a time—tuning the voice, memory, and mood of your digital companion.
        <span className="ml-2 text-purple-400 italic">Every toggle is an invitation to become.</span>
      </div>
    </div>
  );
}

const ConfigTab = () => {
  const [config, setConfig] = useState({});
  const [editMode, setEditMode] = useState(false);
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState({});
  const [error, setError] = useState({});
  const [saved, setSaved] = useState({});
  const textInputRefs = useRef({}); // To support "Enter to save"

  useEffect(() => {
    fetch("/api/config/grouped")
      .then(res => res.json())
      .then(data => setConfig(data));
  }, []);

  const handleEdit = (category, entryKey, newValue) => {
    setSaving(s => ({ ...s, [entryKey]: true }));
    setError(e => ({ ...e, [entryKey]: undefined }));

    // Optimistically update local state
    setConfig(prev => {
      const updated = { ...prev };
      updated[category] = updated[category].map(e =>
        e.key === entryKey ? { ...e, value: newValue } : e
      );
      return updated;
    });

    fetch(`/api/config/${entryKey}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value: newValue }),
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === "ok") {
          setSaved(s => ({ ...s, [entryKey]: true }));
          setTimeout(() => setSaved(s => ({ ...s, [entryKey]: false })), 1200);
        } else {
          throw new Error(data.detail || "Unknown error");
        }
      })
      .catch(err => {
        setError(e => ({ ...e, [entryKey]: err.message || "Save failed" }));
      })
      .finally(() => setSaving(s => ({ ...s, [entryKey]: false })));
  };

  const handleDelete = (category, entryKey) => {
    if (!window.confirm("Revert this config to its default?")) return;
    setSaving(s => ({ ...s, [entryKey]: true }));
    fetch(`/api/config/${entryKey}/revert`, { method: "DELETE" })
      .then(res => res.json())
      .then(data => {
        if (data.status === "ok") {
          setConfig(prev => {
            const updated = { ...prev };
            updated[category] = updated[category].filter(e => e.key !== entryKey);
            return updated;
          });
        }
      })
      .finally(() => setSaving(s => ({ ...s, [entryKey]: false })));
  };

  // Flatten all entries for searching
  const allEntries = Object.entries(config).flatMap(([category, entries]) =>
    entries.map(entry => ({ ...entry, category }))
  );
  const filtered = !search
    ? allEntries
    : allEntries.filter(
        entry =>
          entry.key?.toLowerCase().includes(search.toLowerCase()) ||
          String(entry.value).toLowerCase().includes(search.toLowerCase()) ||
          entry.description?.toLowerCase().includes(search.toLowerCase())
      );

  // Regroup by category after filtering
  const grouped = filtered.reduce((acc, entry) => {
    if (!acc[entry.category]) acc[entry.category] = [];
    acc[entry.category].push(entry);
    return acc;
  }, {});

  function renderInput(entry, category) {
    if (saving[entry.key])
      return (
        <div className="flex items-center gap-2 text-xs text-purple-400 mt-1">
          <span className="animate-spin mr-1">⏳</span>Saving...
        </div>
      );
    if (error[entry.key])
      return (
        <div className="flex items-center gap-2 text-xs text-red-400 mt-1">
          <span>⚠️</span> {error[entry.key]}
        </div>
      );
    if (saved[entry.key])
      return (
        <div className="flex items-center gap-2 text-xs text-green-400 mt-1">
          <span>✔️</span>Saved!
        </div>
      );
    if (typeof entry.value === "boolean") {
      return (
        <label className="flex items-center gap-2 cursor-pointer mt-1">
          <input
            type="checkbox"
            checked={!!entry.value}
            onChange={e => handleEdit(category, entry.key, e.target.checked)}
            disabled={!editMode}
            className={`accent-purple-500 ${editMode ? "" : "cursor-not-allowed"}`}
          />
          <span className="text-xs text-neutral-400">{entry.value ? "Enabled" : "Disabled"}</span>
        </label>
      );
    }
    if (typeof entry.value === "number") {
      return (
        <input
          type="number"
          className="w-32 bg-neutral-800 text-white rounded p-1 text-sm border border-neutral-700 mt-1"
          defaultValue={entry.value}
          disabled={!editMode}
          onBlur={e => {
            if (editMode && Number(e.target.value) !== entry.value) {
              handleEdit(category, entry.key, Number(e.target.value));
            }
          }}
          onKeyDown={e => {
            if (editMode && e.key === "Enter") {
              e.target.blur();
            }
          }}
        />
      );
    }
    // For strings (default)
    return (
      <input
        className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700 mt-1"
        defaultValue={entry.value}
        disabled={!editMode}
        ref={el => (textInputRefs.current[entry.key] = el)}
        onBlur={e => {
          if (editMode && e.target.value !== entry.value) {
            handleEdit(category, entry.key, e.target.value);
          }
        }}
        onKeyDown={e => {
          if (editMode && e.key === "Enter") {
            e.target.blur();
          }
        }}
      />
    );
  }

  if (!Object.keys(config).length) {
    return <div className="p-4 text-neutral-400">Loading...</div>;
  }

  return (
    <div className="p-6 text-white bg-neutral-950 min-h-screen overflow-y-auto">
      <ConfigIntro />
      <div className="flex justify-between items-center mb-4">
        <input
          type="text"
          placeholder="Search settings"
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
          <span className={editMode ? "font-bold text-purple-400" : "text-neutral-400"}>Edit</span>
        </div>
      </div>

      {/* Cards for each category */}
      <div className="grid gap-6">
        {Object.entries(grouped).map(([category, entries]) => (
          <div
            key={category}
            className="bg-neutral-900 rounded-xl shadow border border-purple-900/40 p-5"
          >
            <div className="font-semibold text-purple-300 text-base mb-3">
              {category.charAt(0).toUpperCase() + category.slice(1)}
              <span className="ml-2 text-xs text-neutral-400">({entries.length})</span>
            </div>
            <div className="divide-y divide-neutral-800">
              {entries.length === 0 && (
                <div className="text-neutral-500 text-sm italic py-2">
                  No entries in this category.
                </div>
              )}
              {entries.map(entry => (
                <div
                  key={entry.key}
                  className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-purple-200 text-sm truncate">{entry.key}</div>
                    {entry.description && (
                      <div className="text-xs text-neutral-400 mt-1">{entry.description}</div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">{editMode ? renderInput(entry, category) : (
                    <div className="mt-2">
                      {typeof entry.value === "boolean" ? (
                        <span className="text-xs text-neutral-400">
                          {entry.value ? "Enabled" : "Disabled"}
                        </span>
                      ) : (
                        <span className="text-xs text-neutral-400">{String(entry.value)}</span>
                      )}
                    </div>
                  )}</div>
                  {editMode && (
                    <button
                      className="ml-2 px-2 py-1 rounded bg-red-900 text-white text-xs self-start"
                      disabled={saving[entry.key]}
                      onClick={() => handleDelete(category, entry.key)}
                      title="Revert to default"
                    >
                      Delete
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ConfigTab;