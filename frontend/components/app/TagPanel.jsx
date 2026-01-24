// components/TagPanel.jsx
import React, { useState } from "react";

export default function TagPanel({ mode, existingTags = [], onConfirm, onCancel }) {
  const [input, setInput] = useState("");
  const [tags, setTags] = useState([]);
  const [selectedForRemoval, setSelectedForRemoval] = useState([]);

  const handleAddFromInput = () => {
    const raw = input.trim();
    if (!raw) return;

    const parts = raw.split(/[,\s]+/).filter(Boolean);
    setTags(prev => Array.from(new Set([...prev, ...parts])));
    setInput("");
  };

  const handleKeyDown = e => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddFromInput();
    }
  };

  const handleRemoveTag = tag => {
    setTags(prev => prev.filter(t => t !== tag));
  };

  const toggleSelectedForRemoval = tag => {
    setSelectedForRemoval(prev =>
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  const handleConfirmAdd = () => {
    onConfirm(tags);
  };

  const handleConfirmRemove = () => {
    onConfirm(selectedForRemoval);
  };

  const title =
    mode === "add"
      ? "Add tags to selected messages"
      : "Remove tags from selected messages";

  return (
    <div className="w-[420px] bg-neutral-900 border border-neutral-700 rounded p-3 shadow-lg">
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-sm text-neutral-200">{title}</span>
        <button
          className="px-2 py-1 text-xs rounded border border-neutral-600 text-neutral-300"
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
            onChange={e => setInput(e.target.value)}
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

      {/* Tag chips */}
      {mode === "add" && (
        <div className="flex flex-wrap gap-2 mb-2 max-h-32 overflow-y-auto">
          {tags.length === 0 ? (
            <span className="text-xs text-neutral-500">
              No tags added yet.
            </span>
          ) : (
            tags.map(tag => (
              <button
                key={tag}
                className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-neutral-800 text-neutral-100 border border-neutral-600 hover:bg-neutral-700"
                onClick={() => handleRemoveTag(tag)}
              >
                <span>{tag}</span>
                <span className="text-neutral-400">×</span>
              </button>
            ))
          )}
        </div>
      )}

      {mode === "remove" && (
        <div className="flex flex-wrap gap-2 mb-2 max-h-32 overflow-y-auto">
          {existingTags.length === 0 ? (
            <span className="text-xs text-neutral-500">
              No tags found on selected messages.
            </span>
          ) : (
            existingTags.map(tag => {
              const isSelected = selectedForRemoval.includes(tag);
              return (
                <button
                  key={tag}
                  className={`flex items-center gap-1 px-2 py-1 text-xs rounded-full border ${
                    isSelected
                      ? "bg-red-700 text-white border-red-500"
                      : "bg-neutral-800 text-neutral-100 border-neutral-600 hover:bg-neutral-700"
                  }`}
                  onClick={() => toggleSelectedForRemoval(tag)}
                >
                  <span>{tag}</span>
                  <span
                    className={
                      isSelected ? "text-red-200" : "text-neutral-400"
                    }
                  >
                    ×
                  </span>
                </button>
              );
            })
          )}
        </div>
      )}

      {/* Footer buttons */}
      {mode === "add" && (
        <button
          className="px-2 py-1 text-sm rounded bg-purple-600 text-white disabled:opacity-40"
          onClick={handleConfirmAdd}
          disabled={tags.length === 0}
        >
          OK
        </button>
      )}

      {mode === "remove" && (
        <button
          className="px-2 py-1 text-sm rounded bg-purple-600 text-white disabled:opacity-40"
          onClick={handleConfirmRemove}
          disabled={selectedForRemoval.length === 0}
        >
          Remove selected tags
        </button>
      )}
    </div>
  );
}