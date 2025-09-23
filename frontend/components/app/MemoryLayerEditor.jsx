import { useState } from "react";

export default function MemoryLayerEditor({
  entries = [],
  onUpdate,
  onTogglePin,
  onRecycle,
  onDelete,
  onAdd
}) {
  const [editing, setEditing] = useState(null);

  // Sort pinned first, then by updated_on (newest last_updated last)
  const sorted = [...entries]
    .filter(e => !e.is_deleted)
    .sort((a, b) => {
      if (a.is_pinned && !b.is_pinned) return -1;
      if (!a.is_pinned && b.is_pinned) return 1;
      return new Date(a.updated_on) - new Date(b.updated_on);
    });

  return (
    <div className="space-y-2">
      {sorted.map(entry => (
        <div
          key={entry.id}
          className={`flex items-start gap-2 p-2 rounded ${
            entry.is_pinned ? "bg-purple-900/30 border border-purple-600" : "bg-neutral-900"
          }`}
        >
          {/* Action buttons */}
          <div className="flex flex-col gap-1">
            <button
              onClick={() => onTogglePin(entry.id, !entry.is_pinned)}
              className="text-yellow-300 hover:text-yellow-500 text-xs font-bold"
              title={entry.is_pinned ? "Unpin" : "Pin"}
            >
              {entry.is_pinned ? "📌" : "📍"}
            </button>
            <button
              onClick={() => onRecycle(entry.id)}
              className="text-yellow-400 hover:text-yellow-600 text-xs font-bold"
              title="Recycle"
            >
              ♻
            </button>
          </div>

          {/* Editable text */}
          <textarea
            value={editing?.id === entry.id ? editing.value : entry.text}
            onChange={e => setEditing({ id: entry.id, value: e.target.value })}
            onBlur={() => {
              if (editing && editing.id === entry.id) {
                if (editing.value !== entry.text) {
                  onUpdate(entry.id, editing.value);
                }
                setEditing(null);
              }
            }}
            className="flex-1 bg-neutral-800 border border-neutral-700 rounded px-2 py-1 text-sm text-white resize-y"
            rows={Math.max(2, entry.text.split("\n").length)}
          />

          {/* Last updated */}
          <span className="text-xs text-neutral-500 whitespace-nowrap self-end">
            {entry.updated_on
              ? new Date(entry.updated_on).toLocaleString()
              : ""}
          </span>
        </div>
      ))}

      {/* Add Entry */}
      <button
        onClick={onAdd}
        className="mt-2 px-2 py-1 bg-purple-700 text-white rounded text-xs"
      >
        + Add Entry
      </button>

      {/* Show recycled entries */}
      {entries.some(e => e.is_deleted) && (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm text-neutral-400 hover:text-neutral-200">
            View Recycled Entries
          </summary>
          <div className="mt-2 space-y-2">
            {entries
              .filter(entry => entry.is_deleted)
              .map(entry => (
                <div
                  key={entry.id}
                  className="flex items-center gap-2 bg-neutral-800 p-2 rounded opacity-70"
                >
                  <span className="flex-1 text-neutral-400 text-sm line-through">
                    {entry.text}
                  </span>
                  <span className="text-xs text-neutral-500 whitespace-nowrap">
                    {entry.updated_on
                      ? new Date(entry.updated_on).toLocaleString()
                      : ""}
                  </span>
                  <button
                    onClick={() => onDelete(entry.id)}
                    className="text-red-400 hover:text-red-600 text-xs font-bold"
                  >
                    ✕ Delete
                  </button>
                </div>
              ))}
          </div>
        </details>
      )}
    </div>
  );
}