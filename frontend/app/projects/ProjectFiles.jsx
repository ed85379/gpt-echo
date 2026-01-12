// ProjectFiles.jsx
import React, { useRef, useState, useEffect, useCallback } from "react";
import { LoaderCircle, ChevronRight, ChevronDown } from "lucide-react";
import {
  ViewFileDialog,
  AttachDialog,
  DetachDialog,
  DeleteDialog,
} from "@/components/app/Dialogs";

const ACCEPTED_TYPES = [
  ".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".js", ".ts", ".py", ".java", ".c", ".cpp", ".cs", ".go", ".rb", ".php",
  ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp"
];

function Spinner({ size = 24 }) {
  return <LoaderCircle className="animate-spin text-violet-400" size={size} />;
}

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

function getDisplayType(file) {
  if (!file) return "unknown";
  const { mimetype = "", name = "" } = file;
  if (!mimetype || mimetype === "application/octet-stream") {
    if (/\.(txt|md|csv|json|js|ts|py|java|c|cpp|cs|go|rb|php|yaml|yml)$/i.test(name)) return "text";
    if (/\.(jpg|jpeg|png|gif|bmp|webp)$/i.test(name)) return "image";
    if (/\.(pdf)$/i.test(name)) return "pdf";
    if (/\.(mp3|wav|ogg)$/i.test(name)) return "audio";
    if (/\.(mp4|mov|avi|webm)$/i.test(name)) return "video";
    return "unknown";
  }
  if (mimetype.startsWith("image/")) return "image";
  if (mimetype.startsWith("text/")) return "text";
  if (mimetype === "application/pdf") return "pdf";
  if (mimetype.startsWith("audio/")) return "audio";
  if (mimetype.startsWith("video/")) return "video";
  return "unknown";
}

function getFileUrl(file) {
  return `/api/files/${file.id}/raw`;
}

export default function ProjectFiles({
  projects,
  project,
  onUpload,
  isProcessing,
  uploadPercent,
  setUploadPercent,
  onDelete,
}) {
  const fileInputRef = useRef();
  const [dragActive, setDragActive] = useState(false);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Dialog state
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [currentFile, setCurrentFile] = useState(null);
  const [fileContent, setFileContent] = useState(null);

  const [attachDialogOpen, setAttachDialogOpen] = useState(false);
  const [unlinkedFiles, setUnlinkedFiles] = useState([]);
  const [attachLoading, setAttachLoading] = useState(false);

  const [detachDialogOpen, setDetachDialogOpen] = useState(false);
  const [detachingFile, setDetachingFile] = useState(null);

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingFile, setDeletingFile] = useState(null);

  const projectId = project._id;

  // Fetch files for this project
  const fetchFiles = useCallback(() => {
    if (!project || !project._id) {
      setFiles([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    fetch(`/api/projects/${project._id}/files`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        const files = (data.files || []).map(f => ({
          id: f._id,
          name: f.filename || f.name || "",
          mimetype: f.mimetype || "application/octet-stream",
          size: f.size || 0,
          caption: f.caption || "",
          uploaded_on: f.uploaded_on || "",
          description: f.description || "",
          tags: f.tags || [],
        }));
        setFiles(files);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load files.");
        setFiles([]);
        setLoading(false);
      });
  }, [project && project._id]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  // Fetch unlinked files (not attached to this project)
  async function fetchUnlinkedFiles() {
    setAttachLoading(true);
    try {
      const params = new URLSearchParams({
        project_id: projectId,
        mode: "exclude"
      });
      const res = await fetch(`/api/files?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to fetch files");
      const data = await res.json();
      setUnlinkedFiles((data.files || []).map(f => ({
        id: f._id,
        name: f.filename || f.name || "",
        mimetype: f.mimetype || "application/octet-stream",
        size: f.size || 0,
        uploaded_on: f.uploaded_on || "",
        tags: f.tags || [],
        project_ids: f.project_ids || [],
      })));
    } finally {
      setAttachLoading(false);
    }
  }

  function getProjectName(projectsArray, pid) {
    if (!Array.isArray(projectsArray) || !pid) return pid;
    const proj = projectsArray.find(p => p._id === pid);
    return proj && proj.name ? proj.name : pid;
  }

  // Dialog openers
  const handleView = (file) => {
    setCurrentFile(file);
    setViewDialogOpen(true);
  };
  const handleAttachOpen = async () => {
    await fetchUnlinkedFiles();
    setAttachDialogOpen(true);
  };
  const handleDetach = (file) => {
    setDetachingFile(file);
    setDetachDialogOpen(true);
  };
  const handleDeleteOpen = (file) => {
    setDeletingFile(file);
    setDeleteDialogOpen(true);
  };

  // Dialog actions
  const handleAttach = async (file) => {
    await fetch(`/api/projects/${projectId}/files`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_id: file.id }),
    });
    fetchFiles();
    await fetchUnlinkedFiles();
    setAttachDialogOpen(false);
  };

  const handleDetachConfirm = async () => {
    if (!detachingFile) return;
    await fetch(`/api/projects/${projectId}/files`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_id: detachingFile.id, action: "detach" }),
    });
    fetchFiles();
    setDetachDialogOpen(false);
    setDetachingFile(null);
  };


  const handleDelete = async (file) => {
    await fetch(`/api/files/${file.id}`, {
      method: "DELETE"
      // No need for headers or body unless your API expects them (yours does not)
    });
    fetchFiles();
    setDeleteDialogOpen(false);
  };

  const handleDeleteConfirm = async () => {
    if (!deletingFile) return;
    await fetch(`/api/files/${deletingFile.id}`, {
      method: "DELETE"
    });
    fetchFiles();
    setDeleteDialogOpen(false);
    setDeletingFile(null);
  };

  // File upload logic
  const handleUpload = (file) => {
    onUpload && onUpload(file, [project._id], fetchFiles);
  };


  // Drag and drop logic
  const handleFileInputChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    handleUpload(file);
    e.target.value = "";
  };
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };
  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  // Fetch file content for view dialog
  useEffect(() => {
    async function fetchContent() {
      setFileContent(null);
      if (!currentFile || getDisplayType(currentFile) !== "text") return;
      try {
        const url = getFileUrl(currentFile);
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to load file");
        const text = await res.text();
        setFileContent(text);
      } catch (e) {
        setFileContent("Could not load file content.");
      }
    }
    if (viewDialogOpen) fetchContent();
  }, [currentFile, project, viewDialogOpen]);

  // Placeholder for other handlers (Update, History, etc.)
  const handleHistory = (file) => { /* TODO */ };
  const handleUpdate = (file) => { /* TODO */ };

  const DRAGDROP_HEIGHT = 72;

  return (
    <div className="project-files">
      <div style={{ marginBottom: "1em", display: "flex", gap: 12, alignItems: "flex-start" }}>
        <div>
          <button
            onClick={() => fileInputRef.current && fileInputRef.current.click()}
            type="button"
            className="px-4 py-1.5 border border-violet-300 rounded-md text-violet-300
              bg-transparent font-medium hover:bg-violet-950/20 transition outline-none
              cursor-pointer select-none"
          >
            Upload New File
          </button>
          <div
            onDrop={isProcessing ? undefined : handleDrop}
            onDragOver={isProcessing ? undefined : handleDragOver}
            onDragLeave={isProcessing ? undefined : handleDragLeave}
            style={{
              border: dragActive ? "2px dashed #a78bfa" : "2px dashed #888",
              borderRadius: 10,
              padding: 0,
              background: dragActive ? "#a78bfa22" : "#23233a",
              color: dragActive ? "#a78bfa" : "#bbb",
              textAlign: "center",
              cursor: isProcessing ? "default" : "pointer",
              transition: "border 0.15s, background 0.15s, color 0.15s",
              minWidth: 200,
              height: DRAGDROP_HEIGHT,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative"
            }}
          >
            {isProcessing ? (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <Spinner size={20} />
                <span style={{
                  marginTop: 8,
                  color: "#a78bfa",
                  fontSize: 14,
                  fontWeight: 500
                }}>
                  Processing…
                </span>
              </div>
            ) : (
              <span style={{ width: "100%" }}>
                {dragActive ? "Drop file here" : "Or drag & drop a file here"}
              </span>
            )}
          </div>
        </div>
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "flex-start", marginLeft: 10,
          minWidth: 180,
          maxWidth: 180
        }}>
          <button
            onClick={handleAttachOpen}
            type="button"
            className="px-4 py-1.5 border border-violet-300 rounded-md text-violet-300
              bg-transparent font-medium hover:bg-violet-950/20 transition outline-none
              cursor-pointer select-none"
          >
            Attach Existing File
          </button>
          <details style={{ display: "block", marginTop: 10, maxWidth: 220 }}>
            <summary style={{
              fontSize: "0.82em",
              color: "#a78bfa",
              cursor: "pointer",
              textDecoration: "underline dotted"
            }}>
              Accepted types
            </summary>
            <span style={{
              fontSize: "0.62em",
              color: "#bbb",
              marginLeft: 4,
              display: "block",
              marginTop: 4,
              wordBreak: "normal",
              whiteSpace: "normal",
              lineHeight: 1.5
            }}>
              {ACCEPTED_TYPES.join("  ")}
            </span>
          </details>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES.join(",")}
            style={{ display: "none" }}
            onChange={handleFileInputChange}
            multiple={false}
          />
        </div>
        <span
          style={{
            marginLeft: "1em",
            fontSize: "0.9em",
            color: "#888",
            lineHeight: 1.4,
            display: "inline-block",
            verticalAlign: "middle",
            borderLeft: "2px solid #a78bfa22",
            paddingLeft: "1em",
            background: "rgba(80, 60, 120, 0.04)",
            borderRadius: "0 6px 6px 0"
          }}
        >
          <strong style={{ color: "#a78bfa", fontWeight: 500 }}>What happens to uploaded files?</strong>
          <br />
          <span>
            Text and converted PDFs become part of your Muse’s memory, and can be referenced at any time unless the project is hidden.
            You’ll also find them ready to insert manually from your Chat panel.
            Images and other files are listed in Project Facts, and may be referenced when the project is in focus.
            <br />Files can be attached to multiple projects.
          </span>
        </span>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          fontWeight: 700,
          color: "#b4b2d8",
          padding: "0.32em 0 0.15em 0",
          fontSize: 15,
          letterSpacing: 0.01,
          borderBottom: "1.5px solid #282860",
          background: "transparent",
          gap: 0,
        }}
      >
        <span style={{ width: 32, display: "inline-block" }} />
        <span style={{ flex: 2, minWidth: 0 }}>File Name</span>
        <span style={{ flex: 1, minWidth: 90, textAlign: "left" }}>Type</span>
        <span style={{ flex: 1, minWidth: 40, textAlign: "right" }}>Size</span>
        <span style={{ flex: 1, minWidth: 120, textAlign: "right" }}>Uploaded</span>
      </div>

      {loading ? (
        <div style={{ color: "#aaa", margin: "1em 0" }}>Loading files…</div>
      ) : error ? (
        <div style={{ color: "#d33", margin: "1em 0" }}>{error}</div>
      ) : (
        <ul className="file-list" style={{ listStyle: "none", padding: 0 }}>
          {files.length === 0 && (
            <li style={{ color: "#888" }}>No files uploaded yet.</li>
          )}
          {files.map((file) => (
            <li
              key={file.id}
              style={{
                borderBottom: "1px solid #282860",
                marginBottom: 0,
                position: "relative",
              }}
            >
              <details>
                <summary
                  style={{
                    display: "flex",
                    alignItems: "center",
                    cursor: "pointer",
                    padding: "0.5em 0",
                    userSelect: "none",
                    outline: "none",
                    transition: "background 0.15s",
                  }}
                  tabIndex={0}
                  onKeyDown={e => {
                    if (e.key === "Enter" || e.key === " ") e.currentTarget.click();
                  }}
                >
                  {/* Chevron */}
                  <span
                    aria-hidden="true"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      width: 32,
                      justifyContent: "center",
                      fontSize: 20,
                      color: "#a78bfa",
                      transition: "transform 0.18s",
                    }}
                  >
                    <span className="chevron-right" style={{ display: "inline" }}>
                      <ChevronRight size={20} />
                    </span>
                    <span className="chevron-down" style={{ display: "none" }}>
                      <ChevronDown size={20} />
                    </span>
                  </span>
                  <span style={{ flex: 2, minWidth: 0, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {file.name}
                  </span>
                  <span style={{ flex: 1, minWidth: 90, color: "#aaa", fontWeight: 400, textAlign: "left" }}>
                    {file.mimetype}
                  </span>
                  <span style={{ flex: 1, minWidth: 40, fontSize: "0.9em", color: "#666", textAlign: "right" }}>
                    {humanFileSize(file.size)}
                  </span>
                  <span style={{ flex: 1, minWidth: 120, fontSize: "0.9em", color: "#999", textAlign: "right" }}>
                    {file.uploaded_on ? new Date(file.uploaded_on).toLocaleString() : "—"}
                  </span>
                </summary>
                {/* Expandable action bar */}
                <div
                  style={{
                    background: "rgba(80, 60, 120, 0.06)",
                    borderRadius: "0 0 10px 10px",
                    padding: "16px 28px 12px 52px",
                    marginTop: 2,
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 14,
                    alignItems: "center",
                    borderTop: "1px solid #282860",
                  }}
                >
                  <button title="Preview file contents" key={file.id} onClick={() => handleView(file)}>
                    View
                  </button>
                  <button title="Show revision history" onClick={() => handleHistory(file)}>
                    History
                  </button>
                  {/*}<button title="Replace this file" onClick={() => handleUpdate(file)}>
                    Update
                  </button> */}
                  <button title="Detach from this project" onClick={() => handleDetach(file)}>
                    Detach
                  </button>
                  <button
                    title="Delete everywhere"
                    style={{
                      color: "#f36",
                      borderColor: "#f36",
                      fontWeight: 500,
                      background: "rgba(220, 30, 80, 0.07)",
                    }}
                    onClick={() => handleDeleteOpen(file)}
                  >
                    Delete
                  </button>
                </div>
                {/* --- Icon swap logic (pure CSS) --- */}
                <style>
                  {`
                    li > details > summary .chevron-right { display: inline; }
                    li > details[open] > summary .chevron-right { display: none; }
                    li > details > summary .chevron-down { display: none; }
                    li > details[open] > summary .chevron-down { display: inline; }
                  `}
                </style>
              </details>
            </li>
          ))}
        </ul>
      )}

      {/* --- Modular Dialogs --- */}
      <ViewFileDialog
        open={viewDialogOpen}
        onClose={() => setViewDialogOpen(false)}
        file={currentFile}
        fileContent={fileContent}
        projectId={projectId}
        getDisplayType={getDisplayType}
        getFileUrl={getFileUrl}
      />
      <AttachDialog
        open={attachDialogOpen}
        onOpenChange={setAttachDialogOpen}
        loading={attachLoading}
        files={unlinkedFiles}
        projectId={projectId}
        projects={projects}
        onAttach={handleAttach}
        fetchUnlinkedFiles={fetchUnlinkedFiles}
        getProjectName={getProjectName}
        humanFileSize={humanFileSize}
      />
      <DetachDialog
        open={detachDialogOpen}
        onClose={() => {
          setDetachDialogOpen(false);
          setDetachingFile(null);
        }}
        file={detachingFile}
        onDetach={handleDetachConfirm}
      />
      <DeleteDialog
        open={deleteDialogOpen}
        onClose={() => {
          setDeleteDialogOpen(false);
          setDeletingFile(null);
        }}
        file={deletingFile}
        onDelete={handleDeleteConfirm}
      />
    </div>
  );
}