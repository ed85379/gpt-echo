import { useState, useEffect } from "react";
import { RefreshCw, Pin } from 'lucide-react';

// Helper for pretty file sizes
function humanFileSize(bytes) {
  const thresh = 1024;
  if (Math.abs(bytes) < thresh) return bytes + " B";
  const units = ["KB", "MB", "GB", "TB"];
  let u = -1;
  do {
    bytes /= thresh;
    ++u;
  } while (Math.abs(bytes) >= thresh && u < units.length - 1);
  return bytes.toFixed(1) + " " + units[u];
}

export default function ProjectsPanel({
  projects,
  project,
  fetchProjects,
  selectedProjectId,
  setSelectedProjectId,
  focus,
  setFocus,
  autoAssign,
  setAutoAssign,
  injectedFiles,
  setInjectedFiles,
  files,
  fetchFiles,
  filesLoading,
  setFilesLoading,
  filesError,
  handlePinToggle
}) {

  // UI handlers
  const handleFocusChange = val => setFocus(val);

  const handleAutoAssignChange = () => setAutoAssign(a => !a);

const handleInjectToggle = (fid, name) => {
  setInjectedFiles(prev => {
    const exists = prev.find(f => f.id === fid);
    if (exists) {
      return prev.filter(f => f.id !== fid);
    } else {
      return [...prev, { id: fid, name, pinned: false }];
    }
  });
};

const isInjected = fid => injectedFiles.some(f => f.id === fid);
const isPinned = fid => injectedFiles.some(f => f.id === fid && f.pinned);

  return (
    <div className="p-2 text-neutral-200">
        {/* Project Dropdown */}
        <div className="mb-4 flex items-center gap-2">
          <span className="mr-2 font-semibold text-purple-300">Select Project:</span>
          <select
            className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm"
            value={selectedProjectId}
            onChange={e => setSelectedProjectId(e.target.value)}
            onFocus={fetchProjects}
          >
            <option value="">(Select...)</option>
            {projects
              .filter(proj => !proj.hidden) // Only show non-hidden projects
              .map(proj => (
                <option key={proj._id} value={proj._id}>
                  {proj.name}
                </option>
              ))
            }
          </select>
          {/* Note about hidden projects */}
          {projects.filter(proj => proj.hidden).length > 0 && (
            <span className="text-xs text-neutral-500">
              ({projects.filter(proj => proj.hidden).length} hidden project{projects.filter(proj => proj.hidden).length > 1 ? 's' : ''})
            </span>
          )}
        </div>

      {!project && (
        <div className="text-neutral-400">
          Select a project to view files and settings.
        </div>
      )}

      {project && (
        <>
        {/* Focus */}
        <div className="mb-4 flex flex-col items-center">
          <div className="text-purple-300 font-semibold mb-1">Focus</div>
          <div className="flex items-center gap-2">
            <span className="text-neutral-400 text-xs w-10 text-right">Global</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={focus}
              onChange={e => handleFocusChange(Number(e.target.value))}
              className="accent-purple-500 flex-1"
              style={{ width: 120 }}
            />
            <span className="text-neutral-400 text-xs w-10">Project</span>
          </div>
        </div>

        {/* Auto-assign */}
        <div className="mb-4 flex items-center gap-2">
          <input
            type="checkbox"
            checked={autoAssign}
            onChange={handleAutoAssignChange}
            className="accent-purple-500"
            id="autoAssignToggle"
          />
          <label
            htmlFor="autoAssignToggle"
            className="text-purple-300 font-semibold select-none cursor-pointer"
          >
            Auto-assign messages to this project
          </label>
        </div>

          {/* Files in project */}
          <div className="mb-4">
            <div className="flex items-center mb-2 font-semibold text-purple-300">
              <span>Files in Project:</span>
              {
                filesLoading ? (
                  <svg className="ml-2 animate-spin h-5 w-5 text-purple-400" /* ...spinner SVG... */ />
              ) : (
              <button
                type="button"
                className="ml-2 p-1 rounded hover:bg-neutral-800 transition-colors"
                title="Refresh file list"
                onClick={fetchFiles}
                aria-label="Refresh file list"
              >
                <RefreshCw size={18} className="text-purple-400 hover:rotate-90 transition-transform" />
              </button>
                )
            }
            </div>
            {filesLoading && <div className="text-neutral-500">Loading files…</div>}
            {filesError && <div className="text-red-400">{filesError}</div>}
            <ul className="space-y-1">
            {files.map(file => {
              const injected = isInjected(file.id);
              const pinned = isPinned(file.id);

              return (
                <li key={file.id} className="flex items-center gap-2 text-neutral-200">
                  <span className="flex-1">
                    {file.name}
                    {file.size ? (
                      <span className="ml-2 text-neutral-500 text-xs">
                        {humanFileSize(file.size)}
                      </span>
                    ) : null}
                  </span>
                  {/* Inject/Remove Toggle */}
                  <button
                    className={`px-2 py-0.5 rounded text-xs font-semibold
                      ${injected
                        ? "bg-purple-600 text-purple-100"
                        : "bg-neutral-800 text-purple-300 hover:bg-purple-600 hover:text-purple-100"
                      }`}
                    onClick={() => handleInjectToggle(file.id, file.name)}
                    type="button"
                  >
                    {injected ? "Injected" : "Inject"}
                  </button>
                  {/* Pin Toggle — only enabled if injected */}
                  <button
                    className={`px-2 py-0.5 rounded text-xs font-semibold flex items-center
                      ${pinned
                        ? "bg-purple-700 text-purple-100 border border-purple-300"
                        : "bg-neutral-700 text-purple-200 hover:bg-purple-600 hover:text-purple-100"
                      }
                      ${!injected ? "opacity-50 cursor-not-allowed" : ""}
                    `}
                    onClick={() => injected && handlePinToggle(file.id)}
                    disabled={!injected}
                    type="button"
                    aria-label={pinned ? `Unpin ${file.name}` : `Pin ${file.name}`}
                    title={pinned ? "Unpin file (keeps it only for this session)" : "Pin file (make persistent until unpinned)"}
                  >
                    <Pin className={`w-4 h-4 ${pinned ? "text-purple-200" : "text-purple-400"}`} strokeWidth={2} />
                  </button>
                </li>
              );
            })}
              {(!filesLoading && files.length === 0) && (
                <li className="text-neutral-500">No files in this project yet.</li>
              )}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}