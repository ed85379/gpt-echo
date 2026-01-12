"use client";
import React, { useEffect, useState } from "react";
import MemoryLayerEditor from "@/components/app/MemoryLayerEditor";

function ProjectFacts({ project }) {
  const [layer, setLayer] = useState(null);
  const [loading, setLoading] = useState(true);
  const projectId = project._id; // passed in from parent page

  useEffect(() => {
    fetchLayer();
  }, [projectId]);

  const fetchLayer = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/memory/project_facts_${projectId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setLayer(data || null);
    } catch (err) {
      console.error("Failed to fetch layer:", err);
    } finally {
      setLoading(false);
    }
  };

  const updateEntryLocal = (entryId, patch) => {
    setLayer(prev =>
      prev
        ? {
          ...prev,
          entries: prev.entries.map(e =>
            e.id === entryId ? { ...e, ...patch } : e
          )
        }
      : prev
    );
  };

  const removeEntryLocal = (entryId) => {
    setLayer(prev =>
      prev
        ? {
          ...prev,
          entries: prev.entries.filter(e => e.id !== entryId)
        }
      : prev
    );
  };

  if (loading) {
    return <div style={{ color: "#aaa" }}>Loading…</div>;
  }
  if (!layer) {
    return <div style={{ color: "#aaa" }}>No project facts layer found.</div>;
  }

  return (
    <div
      style={{
        minHeight: "70vh",
        background: "#181823",
        borderRadius: 12,
        overflow: "hidden",
        boxShadow: "0 4px 32px #0004",
        padding: "32px"
      }}
    >
      <h2 style={{ fontSize: 22, marginBottom: 12 }}>{layer.name}</h2>
      <p style={{ marginBottom: 20 }}>
        Purpose: {layer.purpose || "—"}
      </p>
      <MemoryLayerEditor
        entries={layer.entries}
        onUpdate={(entryId, text) => {
          updateEntryLocal(entryId, {
            text,
            updated_on: new Date().toISOString()
          });
          return fetch(`/api/memory/${layer.id}/${entryId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
          }).catch(err => {
            console.error("Update failed", err);
            fetchLayer();
          });
        }}
        onTogglePin={(entryId, isPinned) => {
          updateEntryLocal(entryId, { is_pinned: isPinned });
          return fetch(`/api/memory/${layer.id}/${entryId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_pinned: isPinned })
          }).catch(err => {
            console.error("Pin failed", err);
            fetchLayer();
          });
        }}
        onRecycle={(entryId, deleted = true) => {
          updateEntryLocal(entryId, { is_deleted: deleted });
          return fetch(`/api/memory/${layer.id}/${entryId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_deleted: deleted })
          }).catch(err => {
            console.error("Recycle failed", err);
            fetchLayer();
          });
        }}
        onDelete={entryId => {
          removeEntryLocal(entryId);
          return fetch(`/api/memory/${layer.id}/${entryId}`, {
            method: "DELETE"
          }).catch(err => {
            console.error("Delete failed", err);
            fetchLayer();
          });
        }}
        onAdd={() => {
          const tempId = "temp-" + Date.now();
          const newEntry = { id: tempId, text: " ", is_deleted: false, is_pinned: false };
          setLayer(prev =>
            prev
              ? { ...prev, entries: [...prev.entries, newEntry] }
              : prev
          );

          return fetch(`/api/memory/${layer.id}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: " " })
          })
          .then(res => res.json())
          .then(data => {
            const realEntry = data.entry;
            setLayer(prev =>
              prev
                ? {
                    ...prev,
                    entries: prev.entries.map(e =>
                      e.id === tempId ? { ...realEntry, text: realEntry.text ?? " " } : e
                    )
                  }
                : prev
            );
          });
        }}
      />
    </div>
  );
}

export default ProjectFacts;