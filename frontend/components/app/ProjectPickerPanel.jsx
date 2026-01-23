// components/ProjectPickerPanel.jsx
import React, { useState } from "react";


export default function ProjectPickerPanel({ projects, onConfirm, onCancel }) {
  const [selectedProjectId, setSelectedProjectId] = useState("");

  return (
    <div className="inline-flex items-center gap-2 bg-neutral-900 border border-neutral-700 rounded px-3 py-2 shadow-lg">
      <span className="text-sm text-neutral-200 whitespace-nowrap">
        Project select:
      </span>

      <select
        className="bg-neutral-800 text-sm text-neutral-100 border border-neutral-600 rounded px-2 py-1"
        value={selectedProjectId}
        onChange={(e) => setSelectedProjectId(e.target.value)}
      >
        <option value="">Clear project</option>
        {projects.map((p) => (
          <option key={p.id || p._id} value={p.id || p._id}>
            {p.name}
          </option>
        ))}
      </select>

      <button
        className="px-2 py-1 text-sm rounded bg-purple-600 text-white disabled:opacity-40"
        onClick={() => onConfirm(selectedProjectId)}

      >
        OK
      </button>

      <button
        className="px-2 py-1 text-xs rounded border border-neutral-600 text-neutral-300"
        onClick={onCancel}
      >
        Cancel
      </button>
    </div>
  );
}