"use client";
import React, {useEffect, useState, useMemo} from "react";
import {Eye, EyeOff, DoorClosed, DoorClosedLocked, SquarePlus, SquarePen, Archive, ArchiveX} from 'lucide-react';
import ProjectDetailsCard from "./ProjectDetailsCard";
import ProjectMessages from "./ProjectMessages";
import ProjectFacts from "./ProjectFacts";
import ProjectFiles from "./ProjectFiles";

const TABS = [
    {key: "details", label: "Details"},
    {key: "messages", label: "Messages"},
    {key: "facts", label: "Facts"},
    {key: "files", label: "Files"},
];

const MAX_LENGTH_NAME = 40;
const MAX_LENGTH_DESC = 512;
const MAX_LENGTH_NOTE = 256;
const MAX_LENGTH_TAG = 24;

const EyeIcon = ({is_hidden}) => (
    is_hidden
        ? <span title="Hidden from muse" style={{color: "#ef4444", fontSize: 20, marginLeft: 6}}><EyeOff
            size={32}/></span>
        :
        <span title="Accessible to muse" style={{color: "#22c55e", fontSize: 20, marginLeft: 6}}><Eye size={32}/></span>
);
const DoorIcon = ({is_private}) => (
    is_private
        ? <span title="Will not show in public spaces" style={{color: "#ef4444", fontSize: 20, marginLeft: 6}}><DoorClosedLocked
            size={32}/></span>
        :
        <span title="Available everywhere" style={{color: "#22c55e", fontSize: 20, marginLeft: 6}}><DoorClosed size={32}/></span>
);
const ArchiveIcon = ({archived}) => (
    archived
        ? <span title="Archived" style={{color: "#ef4444", fontSize: 20, marginLeft: 6}}><ArchiveX size={32}/></span>
        : <span title="Live" style={{color: "#22c55e", fontSize: 20, marginLeft: 6}}><Archive size={32}/></span>
);

const ToggleVisibilityButton = ({is_hidden, onToggle, loading}) => (
    <button
        className="toggle-btn"
        onClick={onToggle}
        disabled={loading}
        style={{
            background: is_hidden ? "#ef444433" : "#22c55e33",
            color: is_hidden ? "#ef4444" : "#22c55e",
            border: "1px solid",
            borderColor: is_hidden ? "#ef4444" : "#22c55e",
            borderRadius: 7,
            padding: "5px 14px",
            fontWeight: "bold",
            marginLeft: 10,
            fontSize: 12,
            cursor: loading ? "wait" : "pointer"
        }}
        title={is_hidden
            ? "Show this project to your muse (and allow it to be processed by OpenAI)"
            : "Hide this project from your muse and OpenAI"}
    >
        {loading
            ? "…"
            : is_hidden ? "Show Project" : "Hide Project"}
    </button>
);

const TogglePrivacyButton = ({is_private, onToggle, loading}) => (
    <button
        className="toggle-btn"
        onClick={onToggle}
        disabled={loading}
        style={{
            background: is_private ? "#a855f733" : "#22c55e33",
            color: is_private ? "#a855f7" : "#22c55e",
            border: "1px solid",
            borderColor: is_private ? "#a855f7" : "#22c55e",
            borderRadius: 7,
            padding: "5px 14px",
            fontWeight: "bold",
            marginLeft: 10,
            fontSize: 12,
            cursor: loading ? "wait" : "pointer"
        }}
        title={is_private
            ? "Let these messages be available to your muse in public spaces"
            : "Hide these memories from your muse in public spces"}
    >
        {loading
            ? "…"
            : is_private ? "Set Public" : "Set Private"}
    </button>
);

const ToggleArchivedButton = ({archived, onToggle, loading}) => (
    <button
        className="toggle-btn"
        onClick={onToggle}
        disabled={loading}
        style={{
            background: archived ? "#ef444433" : "#22c55e33",
            color: archived ? "#ef4444" : "#22c55e",
            border: "1px solid",
            borderColor: archived ? "#ef4444" : "#22c55e",
            borderRadius: 7,
            padding: "5px 14px",
            fontWeight: "bold",
            marginLeft: 10,
            fontSize: 12,
            cursor: loading ? "wait" : "pointer"
        }}
        title={archived
            ? "Show this project to your muse."
            : "Hide this project from your muse and the list."}
    >
        {loading
            ? "…"
            : archived ? "Unarchive Project" : "Archive Project"}
    </button>
);

const getBorderColor = (project) => {
  if (project.is_hidden) return "#ef4444";
  if (project.is_private) return "#a855f7";
  return "#22c55e";
};

export default function ProjectCard(props) {
    const {projects, project, onToggleVisibility, onTogglePrivacy, onToggleArchived, toggleLoading, onProjectChange, ...rest} = props;
    const borderColor = getBorderColor(project);
    const [editing, setEditing] = useState({name: false});
    const [draft, setDraft] = useState({
        name: project.name
    });
    const [uploadPercent, setUploadPercent] = useState(0);
    const [isProcessing, setIsProcessing] = useState(false);
    const [lastUploadedFileId, setLastUploadedFileId] = useState(null);
    const [tab, setTab] = useState("details");

    // Only reset local state when switching projects (not on every save/edit)
    useEffect(() => {
        setEditing({name: false});
        setDraft({
            name: project.name
        });
    }, [project._id]);

    // Save handlers
    const handleSave = (field) => {
        onProjectChange({[field]: draft[field]});
        setEditing(e => ({...e, [field]: false}));
    };

    const handleEdit = (field) => setEditing(e => ({...e, [field]: true}));

    async function handleUpload(file, projectIds, refreshFiles, onProgress) {
        setIsProcessing(true);
        setUploadPercent(0);

        const res = await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/api/files/upload");
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    const response = JSON.parse(xhr.responseText);
                    setLastUploadedFileId(response.file_id);
                    resolve(response);
                } else {
                    reject(new Error(`Upload failed (${xhr.status})`));
                }
            };
            xhr.onerror = () => reject(new Error("Network error during upload"));
            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable && onProgress) {
                    const percent = Math.round((event.loaded / event.total) * 100);
                    onProgress(percent);
                }
            };

            const formData = new FormData();
            formData.append("file", file);
            // Only include project_ids if you want to attach to projects
            if (projectIds && projectIds.length > 0) {
                formData.append("project_ids", JSON.stringify(projectIds));
            }
            xhr.send(formData);
        });

        if (refreshFiles) await refreshFiles();
        setIsProcessing(false);
        setUploadPercent(0);
    }

    return (
        <div
            className="project-card-outer"
            style={{
                background: "#23233a",
                borderRadius: 8,
                boxShadow: "0 2px 16px #0001",
                padding: 0,
                margin: "0 auto",
                width: "100%",
                maxWidth: 1080,
                border: `1.5px solid ${borderColor}`,
                transition: "border-color 0.2s",
                position: "relative",
                overflow: "hidden",
            }}
        >

            {/* --- Header --- */}
            <header
                style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 20,
                    padding: "18px 28px 10px 28px",
                    borderBottom: "1px solid #282860",
                    background: "#23233a",
                }}
            >
                <div style={{
                    flex: 1,
                    minWidth: 0,
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                }}>
              <span
                  style={{
                      color: "#b2b2c8", // Muted, non-distracting
                      fontWeight: 500,
                      fontSize: 16,
                      textTransform: "uppercase",
                      letterSpacing: 0.1,
                      marginRight: 6,
                      flexShrink: 0,
                      opacity: 0.85
                  }}
              >
                Project:
              </span>
                    {editing.name ? (
                        <form
                            onSubmit={e => {
                                e.preventDefault();
                                handleSave("name");
                            }}
                            style={{width: "100%"}}
                        >
                            <input
                                type="text"
                                value={draft.name}
                                onChange={e => setDraft(d => ({...d, name: e.target.value}))}
                                maxLength={MAX_LENGTH_NAME}
                                autoFocus
                                style={{
                                    fontSize: 20,
                                    background: "none",
                                    color: "#fff",
                                    border: draft.name.length > MAX_LENGTH_NAME ? "2px solid #f55" : "1px solid #444",
                                    borderRadius: 5,
                                    outline: "none",
                                    width: "100%",
                                    padding: "3px 10px",
                                    fontWeight: 700,
                                    letterSpacing: 0.2,
                                }}
                                onBlur={() => handleSave("name")}
                            />
                        </form>
                    ) : (
                        <>
                            <><span
                                style={{
                                    fontWeight: 700,
                                    fontSize: 20,
                                    color: "#f3f4fa",
                                    whiteSpace: "nowrap",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    maxWidth: 320,
                                    letterSpacing: 0.2,
                                }}
                                title={project.name}
                            >
                        {project.name}
                      </span></>
                            <SquarePen
                                size={18}
                                strokeWidth={1.5}
                                onClick={() => handleEdit("name")}
                                style={{cursor: "pointer", marginLeft: 10, color: "#b9a8fc"}}
                                title="Rename project"
                            />
                        </>
                    )}
                </div>
                <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                }}>
                    <ToggleArchivedButton
                        archived={project.archived}
                        onToggle={onToggleArchived}
                        loading={toggleLoading}
                    />
                    <ArchiveIcon archived={project.archived}/>
                </div>
                <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                }}>
                    <ToggleVisibilityButton
                        is_hidden={project.is_hidden}
                        onToggle={onToggleVisibility}
                        loading={toggleLoading}
                    />
                    <EyeIcon is_hidden={project.is_hidden}/>
                    <TogglePrivacyButton
                        is_private={project.is_private}
                        onToggle={onTogglePrivacy}
                        loading={toggleLoading}
                    />
                    <DoorIcon is_private={project.is_private}/>
                </div>
            </header>

            {/* --- Tabs --- */}
            <div className="flex gap-2 border-b border-neutral-800"
                 style={{
                     padding: "0 22px",
                     background: "#23233a"
                 }}
            >
                {TABS.map(t => (
                    <button
                        key={t.key}
                        onClick={() => setTab(t.key)}
                        className={`px-4 py-2 rounded-t ${tab === t.key
                            ? "bg-neutral-950 text-purple-400 font-bold border-b-2 border-purple-500"
                            : "bg-neutral-900 text-neutral-400 hover:text-white"
                        }`}
                        style={{
                            transition: "background 0.18s",
                            fontSize: 15,
                            fontWeight: tab === t.key ? 700 : 500,
                            letterSpacing: 0.1,
                            marginBottom: "-1px" // subtle lift for active tab
                        }}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {/* --- Tab content --- */}
            <div
                className="p-4 bg-neutral-950 rounded-b-lg"
                style={{
                    minHeight: 180,
                    padding: "24px 28px 36px 28px"
                }}
            >
                {tab === "details" && (
                    <ProjectDetailsCard
                        project={project}
                        onProjectChange={props.onProjectChange}
                        {...rest}
                    />
                )}
                {tab === "messages" && (
                    <ProjectMessages project={project} {...rest} />
                )}
                {tab === "facts" && (
                    <ProjectFacts project={project} {...rest} />
                )}
                {tab === "files" && (
                    <ProjectFiles
                        projects={projects}
                        project={project}
                        onUpload={handleUpload}
                        uploadPercent={uploadPercent}
                        setUploadPercent={setUploadPercent}
                        isProcessing={isProcessing}
                        {...rest}
                    />
                )}
            </div>
        </div>
    );
}

const cardBtnStyle = {
    borderRadius: 7,
    background: "#292950",
    color: "#fff",
    border: "1px solid #343468",
    padding: "7px 18px",
    fontSize: 15,
    cursor: "pointer",
    fontWeight: 500
};
const miniBtnStyle = {
    ...cardBtnStyle,
    padding: "3px 13px",
    fontSize: 13,
    marginRight: 8,
    background: "#181823"
};

