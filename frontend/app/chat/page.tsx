"use client";
import { useState, useEffect, useCallback } from "react";
import ChatTab from './ChatTab';
import HistoryTab from './HistoryTab';
import { useConfig } from '@/hooks/ConfigContext';
import PresencePanel from './PresencePanel';
import MotdBar from './MotdBar';
import TabbedToolPanel from './TabbedToolPanel';

const TABS = [
  { key: "chat", label: "Chat" },
  { key: "history", label: "History" }
];

export default function ChatPage() {
  const [activeTab, setActiveTab] = useState("chat");
  const [speaking, setSpeaking] = useState(false);
  const [projects, setProjects] = useState([]);
  const [projectMap, setProjectMap] = useState({});
  const { uiStates, loading: uiStatesLoading } = useConfig();
  const initialProjectId = uiStates?.projects?.project_id ?? "";
  const motd = uiStates?.motd?.text ?? "";


  const handleReturnToThisMoment = async (message_id: string) => {
    const res = await fetch(`/api/time_skip/${message_id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      console.error("Failed to set time skip");
      return;
    }


    // optional: maybe navigate back to Chat tab
    setActiveTab("chat");

  };

  const fetchProjects = async () => {
    const res = await fetch("/api/projects");
    const data = await res.json();
    setProjects(data.projects || []);
    // Build a file map for quick lookups
    const files = {};
    for (const proj of data.projects || []) {
      for (const fid of (proj.file_ids || [])) {
        if (!files[fid]) files[fid] = { name: fid }; // You would actually want to fetch file metadata
      }
    }
    setProjectMap({ projects: Object.fromEntries((data.projects || []).map(p => [p._id, p])), files });
  };
  useEffect(() => { fetchProjects(); }, []);

  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [project, setProject] = useState(null);
  const [focus, setFocus] = useState(0.5);
  const [autoAssign, setAutoAssign] = useState(false);
  const [injectedFiles, setInjectedFiles] = useState([]);
  const [ephemeralFiles, setEphemeralFiles] = useState([]);
  // File list state, loading, and error
  const [files, setFiles] = useState([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [filesError, setFilesError] = useState(null);

  // Hydrate from uiStates once they’re available
  useEffect(() => {
    if (!uiStatesLoading && uiStates) {
      // 1) Selected project id (cursor)
      const currentProjectId = uiStates.projects.project_id ?? "";
      setSelectedProjectId(currentProjectId);
      const perProject = uiStates.projects.per_project ?? {};
      const globalPrefs = uiStates.projects.default_project_settings ?? {};

      // 2) Focus / blend ratio
      const projectPrefs = currentProjectId? perProject[currentProjectId] ?? {} : {};
      const blend =
        typeof projectPrefs.blend_ratio === "number"
          ? projectPrefs.blend_ratio
          : typeof globalPrefs.blend_ratio === "number"
          ? globalPrefs.blend_ratio
          : 0.5;
      setFocus(blend);

      // 3) Auto-assign
      const auto =
        typeof projectPrefs.auto_assign === "boolean"
          ? projectPrefs.auto_assign
          : typeof globalPrefs.auto_assign === "boolean"
          ? globalPrefs.auto_assign
          : true;
      setAutoAssign(auto);
    }
  }, [uiStatesLoading, uiStates]);

  // On project select: fetch project doc (read-only)
  useEffect(() => {
    if (!selectedProjectId) {
      setProject(null);

      setInjectedFiles([]);
      return;
    }
    // 1. Load project metadata
    fetch(`/api/projects/${selectedProjectId}`)
      .then(res => res.json())
      .then(data => {
        setProject(data.project || data);

        setInjectedFiles([]);
      });

    // 2. Load effective UI state for this project
    fetch(`/api/states/${selectedProjectId}`)
      .then(res => res.json())
      .then(state => {
        if (typeof state.auto_assign === "boolean") {
          setAutoAssign(state.auto_assign);
        }
        if (typeof state.blend_ratio === "number") {
          setFocus(state.blend_ratio);
        }
      });

  }, [selectedProjectId]);

  // Fetch files for this project (special endpoint)
  const fetchFiles = useCallback(() => {
    if (!selectedProjectId) {
      setFiles([]);
      setFilesLoading(false);
      setFilesError(null);
      return;
    }
    setFilesLoading(true);
    setFilesError(null);
    fetch(`/api/projects/${selectedProjectId}/files`)
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
        setFilesLoading(false);
      })
      .catch(() => {
        setFilesError("Failed to load files.");
        setFiles([]);
        setFilesLoading(false);
      });
  }, [selectedProjectId]);

  // Refetch files whenever project changes
  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handlePinToggle = fid => {
    setInjectedFiles(prev =>
      prev.map(f =>
        f.id === fid ? { ...f, pinned: !f.pinned } : f
      )
    );
  };

  const handleEphemeralUpload = (file) => {
    if (!file) return;
    // Optional: check for duplicates or size/type limits here
    setEphemeralFiles(prev => [
      ...prev,
      {
        file, // Store the File object itself
        name: file.name,
        type: file.type,
        size: file.size,
        id: crypto.randomUUID(), // For UI tracking/removal
        // You could add preview data URLs for images if you want
      }
    ]);
  };

  return (
    <div className="flex flex-col h-full w-full">
      {/* Sub-tab selector */}
      <div className="flex gap-2 border-b border-neutral-800 px-6">
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            title={tab.key === "history" ? "View, search, and filter conversation logs" : ""}
            className={`px-4 py-2 rounded-t-lg border-b-2 transition-all
              ${activeTab === tab.key
                ? 'border-purple-400 text-purple-200 font-bold bg-neutral-900'
                : 'border-transparent text-purple-400 hover:bg-neutral-900/50'
              }`
            }
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sub-tab content */}
      {activeTab === "chat" && (
        <div className="relative grid grid-cols-1 md:grid-cols-3 gap-6 h-full px-6">
          <div className=" relative md:col-span-2 overflow-y-auto" style={{ maxHeight: "calc(100vh - 92px - 48px)" }}>
            <ChatTab
              setSpeaking={setSpeaking}
              speaking={speaking}
              selectedProjectId={selectedProjectId}
              focus={focus}
              autoAssign={autoAssign}
              injectedFiles={injectedFiles}
              files={files}
              setInjectedFiles={setInjectedFiles}
              handlePinToggle={handlePinToggle}
              ephemeralFiles={ephemeralFiles}
              setEphemeralFiles={setEphemeralFiles}
              handleEphemeralUpload={handleEphemeralUpload}
            />
          </div>
          <div className="flex flex-col w-full md:max-w-sm sticky top-6 self-start h-[80vh] min-h-[400px]">
            {/* Expandable/collapsible presence panel */}
            <PresencePanel speaking={speaking} />
            <MotdBar />
            {/* Always-scrollable tool panel below */}
            <div className="flex-1 overflow-y-auto">
            <TabbedToolPanel
              projects={projects}
              project={project}
              fetchProjects={fetchProjects}
              projectMap={projectMap}
              selectedProjectId={selectedProjectId}
              setSelectedProjectId={setSelectedProjectId}
              focus={focus}
              setFocus={setFocus}
              autoAssign={autoAssign}
              setAutoAssign={setAutoAssign}
              injectedFiles={injectedFiles}
              setInjectedFiles={setInjectedFiles}
              fetchFiles={fetchFiles}
              files={files}
              setFiles={setFiles}
              filesLoading={filesLoading}
              setFilesLoading={setFilesLoading}
              filesError={filesError}
              handlePinToggle={handlePinToggle}
            />
            </div>
          </div>
        </div>
      )}

      {activeTab === "history" && (
        <div className="flex-1 px-6">
          <HistoryTab
            onReturnToThisMoment={handleReturnToThisMoment}
          />
        </div>
      )}
    </div>
  );
}