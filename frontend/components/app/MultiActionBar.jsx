// components/MessageActionsBar.jsx
import React, { useState } from "react";



const ACTIONS = [
  { value: "", label: "Select action…" },
  { value: "forget", label: "Forget messages" },
  { value: "restore", label: "Restore messages" },
  { value: "hide", label: "Hide messages" },
  { value: "unhide", label: "Unhide messages" },
  { value: "private", label: "Set Private" },
  { value: "public", label: "Set Public" },
  { value: "set_project", label: "Add to project…" },
  { value: "add_tags", label: "Add tags…" },
  { value: "remove_tags", label: "Remove tags…" },
];


export default function MessageActionsBar({
  multiSelectEnabled,
  onToggleMultiSelect,
  selectedCount,
  onAction,
  disabled
}) {
  const [selectedAction, setSelectedAction] = useState("");


  const hasSelection = selectedCount >= 0;
  const isDisabled = disabled || !multiSelectEnabled || !hasSelection;
  const canApply = !isDisabled && !!selectedAction;

  const needsPanel = (action) =>
    action === "set_project" ||
    action === "add_tags" ||
    action === "remove_tags";

  const isPanelAction = needsPanel(selectedAction);
  const buttonLabel = isPanelAction ? "Next" : "Apply";

  const handleActionChange = (e) => {
    const value = e.target.value;
    setSelectedAction(value);
  };

  const handleApply = () => {
    if (!canApply) return;

    // Parent decides whether this opens a dialog or runs immediately.
    onAction(selectedAction, {});
  };

  return (
    <div className="flex items-center gap-3">
      {/* Multi-select toggle */}
      <div className="flex items-center gap-2 text-sm text-neutral-300">
        <span>Multi-select</span>

        <button
          className={`relative inline-flex items-center w-12 h-6 rounded-full transition-colors duration-300 px-2
            ${multiSelectEnabled ? "bg-purple-600" : "bg-neutral-700"}`}
          onClick={() => onToggleMultiSelect(!multiSelectEnabled)}
          aria-label="Toggle multi-select"
          disabled={disabled}
        >
          <span className="text-[10px] text-white mr-2">
            {multiSelectEnabled ? selectedCount : ""}
          </span>

          <span
            className={`w-4 h-4 rounded-full bg-white transition-transform duration-300
              ${multiSelectEnabled ? "translate-x-1" : "-translate-x-2"}`}
          />
        </button>
      </div>

      {/* Action select */}
      <select
        className="bg-neutral-800 text-sm text-neutral-100 border border-neutral-600 rounded px-2 py-1 disabled:opacity-50"
        value={selectedAction}
        onChange={(e) => setSelectedAction(e.target.value)}
        disabled={isDisabled}
      >
        {ACTIONS.map((a) => (
          <option key={a.value || "none"} value={a.value}>
            {a.label}
          </option>
        ))}
      </select>

      {/* Apply button */}
      <button
        className="px-2 py-1 text-sm rounded bg-purple-600 text-white disabled:opacity-40 disabled:cursor-not-allowed"
        onClick={handleApply}
        disabled={!canApply}
      >
        {buttonLabel}
      </button>
    </div>
  );
}