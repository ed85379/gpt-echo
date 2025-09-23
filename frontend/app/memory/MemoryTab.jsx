"use client";
import React, { useEffect, useState } from "react";
import MemoryLayerEditor from "@/components/app/MemoryLayerEditor";

function MemoryTab() {
  const [layers, setLayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedLayerId, setSelectedLayerId] = useState(null);

  useEffect(() => {
    fetchLayers();
  }, []);

  const fetchLayers = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/memory");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setLayers(data || []);
      console.log("Layers from API:", data);
    } catch (err) {
      console.error("Failed to fetch layers:", err);
    } finally {
      setLoading(false);
    }
  };

  const selectedLayer = layers.find(l => l.id === selectedLayerId);

  return (
    <div
      style={{
        display: "flex",
        minHeight: "70vh",
        background: "#181823",
        borderRadius: 12,
        overflow: "hidden",
        boxShadow: "0 4px 32px #0004"
      }}
    >
      {/* LEFT: Sidebar */}
      <aside
        style={{
          width: 350,
          background: "#23233a",
          padding: "24px 16px",
          borderRight: "1px solid #292950",
          display: "flex",
          flexDirection: "column"
        }}
      >
        {loading && <div style={{ color: "#aaa" }}>Loading…</div>}
        {!loading && layers.length === 0 && (
          <div style={{ color: "#aaa" }}>No layers found.</div>
        )}

        <ul
          style={{
            flex: 1,
            listStyle: "none",
            padding: 0,
            margin: 0,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: 12
          }}
        >
{layers.map(layer => {
  const total = layer.entries?.length ?? 0;
  const pinned = layer.entries?.filter(e => e.is_pinned).length ?? 0;
  const recycled = layer.entries?.filter(e => e.recycled).length ?? 0;

  return (
    <li
      key={layer.id}
      onClick={() => setSelectedLayerId(layer.id)}
      style={{
        cursor: "pointer",
        background: selectedLayerId === layer.id ? "#312e81" : "#2a2a40",
        borderRadius: 8,
        padding: "12px 14px",
        boxShadow:
          selectedLayerId === layer.id
            ? "0 2px 8px rgba(0,0,0,0.35)"
            : "0 1px 3px rgba(0,0,0,0.2)",
        color: "#f7f7ff",
        transition: "background 0.2s"
      }}
    >
      <div style={{ fontWeight: "bold", marginBottom: 4 }}>
        {layer.name || "Untitled Layer"}
      </div>
      <div style={{ fontSize: 13, color: "#bbb", marginBottom: 6 }}>
        Purpose: {layer.purpose || "—"}
      </div>
      <div style={{ fontSize: 13, display: "flex", gap: 12, color: "#ccc" }}>
        <span>📌 pinned: {pinned}</span>
        <span>🗂 total: {total}</span>
        <span>♻ recycled: {recycled}</span>
      </div>
    </li>
  );
})}
        </ul>
      </aside>

      {/* RIGHT: Details */}
      <main
        style={{
          flex: 1,
          padding: "32px 32px 24px 32px",
          background: "#1e1e2e",
          display: "flex",
          flexDirection: "column"
        }}
      >
        {!selectedLayer ? (
          <div
            style={{
              color: "#aaa",
              fontSize: 20,
              marginTop: "20vh",
              textAlign: "center"
            }}
          >
            Select a memory layer to view entries
          </div>
        ) : (
          <div style={{ color: "#eee" }}>
            <h2 style={{ fontSize: 22, marginBottom: 12 }}>
              {selectedLayer.name}
            </h2>
            <p style={{ marginBottom: 20 }}>
              Purpose: {selectedLayer.purpose || "—"}
            </p>
                <MemoryLayerEditor
                  entries={selectedLayer.entries}
                  onUpdate={(entryId, text) =>
                    fetch(`/api/memory/${selectedLayer.id}/${entryId}`, {
                      method: "PATCH",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ text })
                    }).then(res => res.json())
                  }
                  onTogglePin={(entryId, isPinned) =>
                    fetch(`/api/memory/${selectedLayer.id}/${entryId}`, {
                      method: "PATCH",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ is_pinned: isPinned })
                    }).then(res => res.json())
                  }
                  onRecycle={entryId =>
                    fetch(`/api/memory/${selectedLayer.id}/${entryId}`, {
                      method: "PATCH",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ is_deleted: true })
                    }).then(res => res.json())
                  }
                  onDelete={entryId =>
                    fetch(`/api/memory/${selectedLayer.id}/${entryId}`, {
                      method: "DELETE"
                    }).then(res => res.json())
                  }
                  onAdd={() =>
                    fetch(`/api/memory/${selectedLayer.id}`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ text: "" })
                    }).then(res => res.json())
                  }
                />
          </div>
        )}
      </main>
    </div>
  );
}

export default MemoryTab;