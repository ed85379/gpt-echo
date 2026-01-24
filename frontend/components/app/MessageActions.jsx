// MessageActions.jsx
"use client";

import React, { useState } from "react";
import { CandleHolderLit } from "@/utils/messageActions";
import {
  Tags,
  Eye,
  EyeOff,
  EyeClosed,
  DoorClosed,
  DoorClosedLocked,
  Shredder,
  SquareX,
  BookMarked,
  History,
  Slash,
  Check
  } from "lucide-react";

function HistoryOffIcon(props) {
  return (
    <span className="relative inline-flex h-4 w-4" {...props}>
      <History className="absolute inset-0" />
      <Slash className="absolute inset-0" />
    </span>
  );
}

export default function MessageActions({
  msg,
  projects = [],
  projectsLoading = false,
  projectMap = {},
  onSetProject,
  onClearProject,
  onAddTag,
  onRemoveTag,
  onTogglePrivate,
  onToggleHidden,
  onToggleRemembered,
  onDelete,
  tagDialogOpen,           // message_id or null
  setTagDialogOpen,
  projectDialogOpen,       // message_id or null
  setProjectDialogOpen,
  mode,
  onReturnToThisMoment,
  multiSelectEnabled,
  isSelected,
  onToggleSelect
}) {
  // Local input state for new tag field
  const [newTag, setNewTag] = useState("");

  // Defensive: never let both dialogs be open for the same message
  function openTagDialog() {
    setProjectDialogOpen(null);
    setTagDialogOpen(msg.message_id);
  }
  function openProjectDialog() {
    setTagDialogOpen(null);
    setProjectDialogOpen(msg.message_id);
  }

  const isPrivate = !!msg.is_private;
  const isHidden = !!msg.is_hidden;
  const isRemembered = !!msg.remembered;
  const isDeleted = !!msg.is_deleted;
  const inProject = msg.project_id;
  const userTags =
    (msg.user_tags || []).filter(
      t => t !== "private" && t !== "hidden" && t !== "deleted" && t !== "remembered" && t !== "project"
    ) || [];
  const baseContainerClasses =
  "absolute right-2 bottom-2 mb-1 mr-1 flex items-center justify-end gap-2";

  if (multiSelectEnabled) {
    const baseButtonClasses =
      "w-5 h-5 rounded border flex items-center justify-center shadow-sm";
    const unselectedClasses =
      "border-purple-500 bg-neutral-800 hover:bg-neutral-700";
    const selectedClasses =
      "bg-purple-600 border-purple-300";

    const buttonClasses =
      baseButtonClasses +
      " " +
      (isSelected ? selectedClasses : unselectedClasses);

    return (
      <div className="absolute right-2 bottom-2 flex items-center justify-end gap-2">
        <button className={buttonClasses} onClick={onToggleSelect}>
          {isSelected && <Check className="w-3 h-3 text-white" />}
        </button>
      </div>
    );
  }

  // --- Render ---
  return (
    <>
      {/* Action Button Bar (appears on hover) */}
      <div className="absolute bottom-2 right-3 hidden group-hover:flex gap-2 z-10">
        {/* Project assign button */}
        <button
          onClick={openProjectDialog}
          title={inProject ? "Change project" : "Add to project"}
          className="text-neutral-400 hover:text-purple-300 transition-colors"
          style={{ background: "none", border: "none", cursor: "pointer" }}
        >
          <BookMarked size={18} />
        </button>
        {/* Tag dialog button */}
        <button
          onClick={openTagDialog}
          title="Tag message"
          className="text-neutral-400 hover:text-purple-300 transition-colors"
          style={{ background: "none", border: "none", cursor: "pointer" }}
        >
          <Tags size={18} />
        </button>
        {/* Remembered toggle */}
        <button
          onClick={() => onToggleRemembered(msg.message_id, !isRemembered)}
          title={isRemembered ? "Unhighlight message in memory" : "Highlight message in memory"}
          className={`transition-colors ${isRemembered ? "text-purple-400" : "text-neutral-400"} hover:text-purple-300`}
          style={{ background: "none", border: "none", cursor: "pointer" }}
        >
          <CandleHolderLit
            className={`transition-colors ${isRemembered ? "text-purple-400" : "text-neutral-400"} hover:text-purple-300`}
          />
        </button>
        {/* Divider between clusters */}
        <span className="mx-1 h-3 border-l self-center border-neutral-400" aria-hidden="true" />
        {/* Private toggle */}
        <button
          onClick={() => onTogglePrivate(msg.message_id, !isPrivate)}
          title={isPrivate ? "Set as public" : "Mark as private"}
          className={`transition-colors ${isPrivate ? "text-purple-400" : "text-neutral-400"} hover:text-purple-300`}
          style={{ background: "none", border: "none", cursor: "pointer" }}
        >
          {isPrivate ? <DoorClosedLocked size={18} /> : <DoorClosed size={18} />}
        </button>
        {/* Hidden toggle */}
        <button
          onClick={() => onToggleHidden(msg.message_id, !isHidden)}
          title={isHidden ? "Set as visible" : "Mark as hidden"}
          className={`transition-colors ${isHidden ? "text-purple-400" : "text-neutral-400"} hover:text-purple-300`}
          style={{ background: "none", border: "none", cursor: "pointer" }}
        >
          {isHidden ? <EyeClosed size={18} /> : <Eye size={18} />}
        </button>
        {/* Delete */}
        <button
          onClick={() => onDelete(msg.message_id, !isDeleted)}
          title={isDeleted ? "Restore message" : "Forget message"}
          className="text-neutral-400 hover:text-red-400 transition-colors"
          style={{ background: "none", border: "none", cursor: "pointer" }}
        >
          {isDeleted ? <SquareX size={18} /> : <Shredder size={18} />}
        </button>
        {mode === "history" && !isDeleted && !isHidden && (
          <>
            <span
              className="mx-1 h-3 border-l self-center border-neutral-400"
              aria-hidden="true"
            />
            {onReturnToThisMoment && (
              <button
                onClick={() => onReturnToThisMoment(msg.message_id)}
                title="Return to this moment..."
                className="transition-colors text-neutral-400 hover:text-purple-300"
                style={{ background: "none", border: "none", cursor: "pointer" }}
              >
                <History size={18} />
              </button>
            )}
          </>
        )}
      </div>

      {/* --- Tag Dialog --- */}
      {tagDialogOpen === msg.message_id && (
        <div className="absolute z-20 right-10 bottom-2 bg-neutral-900 p-4 rounded-lg shadow-lg w-64">
          <div className="mb-2 font-semibold text-purple-100">Edit Tags</div>
          {/* List current tags */}
          <div className="flex flex-wrap gap-1 mb-2">
            {userTags.map(tag => (
              <span
                key={tag}
                className="bg-purple-800 text-xs text-purple-100 px-2 py-0.5 rounded-full flex items-center"
              >
                {tag}
                <button
                  className="ml-1 text-purple-300 hover:text-red-300"
                  onClick={() => onRemoveTag(msg.message_id, tag)}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
          {/* Add new tag */}
          <div className="flex">
            <input
              type="text"
              className="flex-1 rounded px-2 py-1 text-sm bg-neutral-800 text-white border-none outline-none"
              value={newTag}
              onChange={e => setNewTag(e.target.value)}
              placeholder="Add tag..."
              onKeyDown={e => {
                if (e.key === "Enter" && newTag.trim()) {
                  onAddTag(msg.message_id, newTag.trim());
                  setNewTag("");
                }
              }}
            />
            <button
              className="ml-2 text-purple-300 hover:text-purple-100"
              onClick={() => {
                if (newTag.trim()) {
                  onAddTag(msg.message_id, newTag.trim());
                  setNewTag("");
                }
              }}
            >
              Add
            </button>
          </div>
          {/* Close button */}
          <button
            className="absolute top-1 right-2 text-xs text-neutral-500 hover:text-purple-200"
            onClick={() => setTagDialogOpen(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* --- Project Dialog --- */}
      {projectDialogOpen === msg.message_id && (
        <div className="absolute z-30 right-10 bottom-2 bg-neutral-900 p-4 rounded-lg shadow-lg w-64">
          <div className="mb-2 font-semibold text-purple-100">Assign Project</div>
          {projectsLoading ? (
            <div className="text-neutral-400 text-sm">Loading projects…</div>
          ) : projects.length === 0 ? (
            <div className="text-neutral-500 text-sm">No projects found.</div>
          ) : (
            <ul className="max-h-40 overflow-y-auto space-y-1">
              {projects.map(proj => (
                <li key={proj._id}>
                  <button
                    className={`w-full text-left px-2 py-1 rounded ${
                      msg.project_id === proj._id
                        ? "bg-purple-700 text-white"
                        : "bg-neutral-800 text-purple-100 hover:bg-purple-900"
                    }`}
                    onClick={() => {
                      onSetProject(msg.message_id, proj._id);
                      setProjectDialogOpen(null);
                    }}
                  >
                    <span className="font-semibold">{proj.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {msg.project_id && (
            <button
              className="mt-2 w-full px-2 py-1 rounded bg-neutral-700 text-purple-200 hover:bg-red-800"
              onClick={() => {
                onClearProject(msg.message_id);
                setProjectDialogOpen(null);
              }}
            >
              Remove from project
            </button>
          )}
          <button
            className="absolute top-1 right-2 text-xs text-neutral-500 hover:text-purple-200"
            onClick={() => setProjectDialogOpen(null)}
          >
            ✕
          </button>
        </div>
      )}

    </>
  );
}