// components/TagPanel.jsx
import React, { useState } from "react";

export default function TagPanel({ mode, existingTags, onConfirm, onCancel }) {
  const [input, setInput] = useState("");
  const [tags, setTags] = useState([]);

  const handleAddFromInput = () => {
    const raw = input.trim();
    if (!raw) return;

    const parts = raw.split(/[,\s]+/).filter(Boolean);
    setTags((prev) => Array.from(new Set([...prev, ...parts])));
    setInput("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddFromInput();
    }
  };

  const handleRemoveTag = (tag) => {
    setTags((prev) => prev.filter((t) => t !== tag));
  };

  const handleConfirm = () => {
    onConfirm(tags);
  };

  const title =
    mode === "add"
      ? "Add tags to selected messages"
      : "Remove tags from selected messages";

  const sourceTags = mode === "remove" ? existingTags : tags;

  return (
    <div className="bg-neutral-900 border border-neutral-700 rounded p-3 shadow-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-neutral-200">{title}</span>
        <button
          className="text-xs text-neutral-400 hover:text-neutral-200"
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>

      {mode === "add" && (
        <div className="flex items-center gap-2 mb-2">
          <input
            className="flex-1 bg-neutral-800 text-sm text-neutral-100 border border-neutral-600 rounded px-2 py-1"
            placeholder="Type tags, press Enter (space or comma-separated)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="px-2 py-1 text-sm rounded bg-purple-600 text-white"
            onClick={handleAddFromInput}
          >
            Add
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-2 max-h-32 overflow-y-auto">
        {sourceTags.length === 0 ? (
          <span className="text-xs text-neutral-500">
            {mode === "add"
              ? "No tags added yet."
              : "No tags found on selected messages."}
          </span>
        ) : (
          sourceTags.map((tag) => (
            <button
              key={tag}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-neutral-800 text-neutral-100 border border-neutral-600 hover:bg-neutral-700"
              onClick={() =>
                mode === "remove" ? handleRemoveTag(tag) : undefined
              }
            >
              <span>{tag}</span>
              {mode === "remove" && <span className="text-neutral-400">×</span>}
            </button>
          ))
        )}
      </div>

      {mode === "add" && (
        <button
          className="px-2 py-1 text-sm rounded bg-purple-600 text-white disabled:opacity-40"
          onClick={handleConfirm}
          disabled={tags.length === 0}
        >
          OK
        </button>
      )}

      {mode === "remove" && (
        <button
          className="px-2 py-1 text-sm rounded bg-purple-600 text-white disabled:opacity-40"
          onClick={() => onConfirm(sourceTags)}
          disabled={sourceTags.length === 0}
        >
          Remove selected tags
        </button>
      )}
    </div>
  );
}