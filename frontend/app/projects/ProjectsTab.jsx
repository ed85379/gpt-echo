"use client";
import React, { useEffect, useState, useMemo } from "react";

import ProjectCard from "./ProjectCard"


// --- ICONS ---
const ArchiveIcon = () => <span title="Archived" style={{marginLeft: 4}}>⏸️</span>;
const PinIcon = () => <span title="Pinned" style={{marginLeft: 4}}>📌</span>;

const StatusDot = ({ is_hidden, is_private }) => {
  let color;

  if (is_hidden) {
    // Hidden always wins
    color = "#ef4444"; // red
  } else if (is_private) {
    color = "#a855f7"; // purple (Iris-color)
  } else {
    color = "#22c55e"; // green
  }

  return (
    <span
      style={{
        display: "inline-block",
        background: color,
        width: 10,
        height: 10,
        borderRadius: 5,
        marginRight: 6,
        marginTop: 2,
      }}
    />
  );
};


// --- Main Tab ---
function ProjectsTab() {
  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState("recent");
  const [showArchived, setShowArchived] = useState(false);
  const [toggleLoading, setToggleLoading] = useState(false);

  const handleAddProject = async () => {
    try {
      // Optionally: disable button here if you want
      const res = await fetch("/api/projects", { method: "POST" });
      if (!res.ok) throw new Error("Failed to create project");
      const project = await res.json();
      // If your backend returns only the project ID: { "_id": ... }
      // If it returns the full project object, adapt accordingly below.
      await fetchProjects();
      // After re-fetching, select the new project
      setSelectedProjectId(project._id || project.project_id);
    } catch (e) {
      alert("Could not add project:\n" + e);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    setProjectsLoading(true);
    const res = await fetch("/api/projects");
    const data = await res.json();
    setProjects(data.projects || []);
    setProjectsLoading(false);
  };

  const projectMap = useMemo(() => {
    const map = {};
    for (const proj of projects) map[proj._id] = proj;
    return map;
  }, [projects]);

  const tagOptions = useMemo(() => {
    const tags = new Set();
    for (const p of projects) (p.tags || []).forEach(t => tags.add(t));
    return Array.from(tags);
  }, [projects]);

  let filtered = projects.filter(p =>
    (showArchived ? true : !p.archived)
    && (filter ? (p.tags || []).includes(filter) : true)
  );
  filtered = [...filtered].sort((a, b) => {
    if (sort === "recent") return 0; // Add updatedOn sort if desired
    if (sort === "alpha") return a.name.localeCompare(b.name);
    return 0;
  });

  const selectedProject = projects.find(p => p._id === selectedProjectId);

  const handleToggleVisibility = async () => {
    if (!selectedProject) return;
    setToggleLoading(true);
    try {
      const res = await fetch(`/api/projects/${selectedProject._id}/visibility`, {
        method: "PUT"
      });
      if (!res.ok) throw new Error(`Failed to toggle visibility (${res.status})`);
      await fetchProjects();
    } catch (e) {
      alert("Failed to toggle visibility:\n" + e);
    } finally {
      setToggleLoading(false);
    }
  };

  const handleTogglePrivacy = async () => {
    if (!selectedProject) return;
    setToggleLoading(true);
    try {
      const res = await fetch(`/api/projects/${selectedProject._id}/privacy`, {
        method: "PUT"
      });
      if (!res.ok) throw new Error(`Failed to toggle privacy (${res.status})`);
      await fetchProjects();
    } catch (e) {
      alert("Failed to toggle privacy:\n" + e);
    } finally {
      setToggleLoading(false);
    }
  };


  const handleToggleArchived = async () => {
    if (!selectedProject) return;
    setToggleLoading(true);
    try {
      const res = await fetch(`/api/projects/${selectedProject._id}/archive`, {
        method: "PUT"
      });
      if (!res.ok) throw new Error(`Failed to toggle archived (${res.status})`);
      await fetchProjects();
    } catch (e) {
      alert("Failed to toggle archived:\n" + e);
    } finally {
      setToggleLoading(false);
    }
  };

  const getStatusTitle = (project) => {
    if (project.is_hidden) return "Hidden project";
    if (project.is_private) return "Private project";
    return "Public project";
  };

  return (
    <div style={{
      display: "flex",
      minHeight: "70vh",
      background: "#181823",
      borderRadius: 12,
      overflow: "hidden",
      boxShadow: "0 4px 32px #0004"
    }}>
      {/* LEFT: Sidebar */}
      <aside style={{
        width: 330,
        background: "#23233a",
        padding: "24px 16px 24px 16px",
        borderRight: "1px solid #292950",
        display: "flex", flexDirection: "column"
      }}>
        <button
          className="add-project-btn"
          style={{
            background: "linear-gradient(90deg,#7c3aed,#c084fc)",
            color: "#fff",
            border: "none", borderRadius: 8,
            padding: "8px 0", fontWeight: "bold",
            marginBottom: 16,
            fontSize: 16,
            cursor: "pointer"
          }}
          onClick={handleAddProject}
        >+ Add Project</button>
        <div className="filters" style={{
          display: "flex", gap: 8, marginBottom: 20
        }}>
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            style={{
              borderRadius: 6, border: "1px solid #444", background: "#16162a", color: "#fff"
            }}>
            <option value="">All Tags</option>
            {tagOptions.map(tag => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
          <select
            value={sort}
            onChange={e => setSort(e.target.value)}
            style={{
              borderRadius: 6, border: "1px solid #444", background: "#16162a", color: "#fff"
            }}>
            <option value="recent">Recently Updated</option>
            <option value="alpha">A–Z</option>
          </select>
        </div>
        <ul style={{
          flex: 1, listStyle: "none", padding: 0, margin: 0,
          overflowY: "auto"
        }}>
          {projectsLoading && <li style={{color: "#aaa"}}>Loading…</li>}
          {!projectsLoading && filtered.length === 0 && <li style={{color: "#aaa"}}>No projects found.</li>}
          {filtered.map(project => (
            <li
              key={project._id}
              className="project-item"
              style={{
                background: selectedProjectId === project._id ? "#312e81" : "none",
                borderRadius: 7,
                marginBottom: 6,
                padding: "10px 10px",
                cursor: "pointer",
                color: project.archived ? "#aaa" : "#f7f7ff",
                display: "flex", alignItems: "center", gap: 8,
                boxShadow: selectedProjectId === project._id ? "0 2px 8px #0002" : "none"
              }}
              onClick={() => setSelectedProjectId(project._id)}
              title={getStatusTitle(project)}
            >
              <StatusDot is_hidden={project.is_hidden} is_private={project.is_private} />
              <span style={{
                fontWeight: "bold", flex: 1
              }}>{project.name}</span>
              {project.archived && <ArchiveIcon />}
              {project.pinned && <PinIcon />}
              <span style={{
                background: "#7c3aed",
                color: "#fff",
                borderRadius: 7,
                fontSize: 12,
                padding: "1px 6px",
                marginLeft: 4
              }}>{project.messageCount || ""}</span>
            </li>
          ))}
        </ul>
        <button
          className="show-archived-btn"
          style={{
            background: "none", border: "none", color: "#aaa",
            marginTop: 8, fontSize: 14, cursor: "pointer"
          }}
          onClick={() => setShowArchived(v => !v)}
        >
          {showArchived ? "Hide Archived" : "Show Archived"}
        </button>
      </aside>
      {/* RIGHT: Details */}
      <main style={{
        flex: 1,
        padding: "32px 32px 24px 32px",
        background: "#1e1e2e",
        display: "flex", flexDirection: "column"
      }}>
        {!selectedProject ? (
          <div className="placeholder"
            style={{
              color: "#aaa", fontSize: 20, marginTop: "20vh", textAlign: "center"
            }}>
            Select a project to view details
          </div>
        ) : (
          <ProjectCard
            projects={projects}
            project={selectedProject}
            projectMap={projectMap}
            projects={projects}
            projectsLoading={projectsLoading}
            onToggleVisibility={handleToggleVisibility}
            onTogglePrivacy={handleTogglePrivacy}
            onToggleArchived={handleToggleArchived}
            toggleLoading={toggleLoading}
            onProjectChange={p => {
              fetch(`/api/projects/${selectedProject._id}`, {
                method: "PATCH",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(p)
              })
                .then(res => {
                  if (!res.ok) throw new Error("Failed to update project");
                  fetchProjects();
                })
                .catch(e => alert("Failed to update project: " + e));
            }}
          />
        )}
      </main>
    </div>
  );
}


export default ProjectsTab;