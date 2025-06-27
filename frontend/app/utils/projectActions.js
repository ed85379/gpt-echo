import { useState, useEffect } from "react";

export function ListEditor({
  items,
  setItems,
  placeholder = "",
  maxItems = 10,
  maxLength = 32,
  allowEdit = false
}) {
  const [input, setInput] = React.useState("");

  const handleAdd = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    if (items.includes(trimmed)) return;
    if (items.length >= maxItems) return;
    setItems([...items, trimmed]);
    setInput("");
  };

  const handleRemove = idx => {
    setItems(items.filter((_, i) => i !== idx));
  };

  const handleEdit = (idx, val) => {
    setItems(items.map((item, i) => i === idx ? val : item));
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {items.map((item, idx) =>
        <div key={idx} style={{
          display: "flex", alignItems: "center", width: "100%"
        }}>
          {allowEdit ? (
            <input
              value={item}
              onChange={e => handleEdit(idx, e.target.value)}
              maxLength={maxLength}
              style={{
                background: "#222",
                color: "#c084fc",
                border: "none",
                borderRadius: 3,
                width: "100%",
                minWidth: 90,
                marginRight: 6,
                padding: "6px 12px",
                fontSize: 15,
              }}
            />
          ) : (
            <span style={{
              background: "#7c3aed33",
              color: "#c084fc",
              borderRadius: 5,
              padding: "6px 12px",
              fontSize: 15,
              minWidth: 90,
              marginRight: 6,
              display: "inline-block",
            }}>{item}</span>
          )}
          <button
            onClick={() => handleRemove(idx)}
            style={{
              background: "none",
              border: "none",
              color: "#c084fc",
              cursor: "pointer",
              fontWeight: "bold",
              fontSize: 20,
              lineHeight: "1"
            }}
            tabIndex={0}
            aria-label="Remove"
          >×</button>
        </div>
      )}
      {items.length < maxItems && (
        <div style={{ display: "flex", alignItems: "center", width: "100%" }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") handleAdd(); }}
            placeholder={placeholder}
            maxLength={maxLength}
            style={{
              background: "#16162a",
              color: "#c084fc",
              borderRadius: 5,
              padding: "6px 12px",
              fontSize: 15,
              border: "1px solid #666",
              width: "100%",
              minWidth: 90,
              marginRight: 6,
            }}
          />
          <button
            onClick={handleAdd}
            disabled={!input.trim()}
            style={{
              background: "#7c3aed",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              padding: "4px 12px",
              fontWeight: 500,
              fontSize: 17,
              cursor: input.trim() ? "pointer" : "not-allowed",
              marginLeft: 4,
              opacity: input.trim() ? 1 : 0.5,
              display: "flex",
              alignItems: "center",
            }}
            aria-label="Add"
          >
            <SquarePlus size={18} strokeWidth={1.5} style={{ fontSize: 18, marginRight: 4 }} />
            Add
          </button>
        </div>
      )}
    </div>
  );
}

export function TagEditor({
  items,            // array of strings
  setItems,         // (nextArray) => void
  placeholder = "",
  maxItems = 10,
  maxLength = 32,
  allowEdit = false // true = allow edit-in-place
}) {
  const [input, setInput] = React.useState("");

  // Add item on Enter or button click
  const handleAdd = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    if (items.includes(trimmed)) return;
    if (items.length >= maxItems) return;
    setItems([...items, trimmed]);
    setInput("");
  };

  const handleRemove = idx => {
    setItems(items.filter((_, i) => i !== idx));
  };

  // Optional edit-in-place for notes
  const handleEdit = (idx, val) => {
    setItems(items.map((item, i) => i === idx ? val : item));
  };

  return (
    <div>
      <div style={{display: "flex", gap: 4, flexWrap: "wrap", alignItems: "center"}}>
        {items.map((item, idx) =>
          <span key={idx} style={{
            background: "#7c3aed33", color: "#c084fc",
            borderRadius: 5, padding: "2px 8px", marginRight: 6, fontSize: 13,
            display: "inline-flex", alignItems: "center"
          }}>
            {allowEdit ? (
              <input
                value={item}
                onChange={e => handleEdit(idx, e.target.value)}
                maxLength={maxLength}
                style={{background: "#222", color: "#c084fc", border: "none", borderRadius: 3, width: 90, marginRight: 2}}
              />
            ) : item}
            <button
              onClick={() => handleRemove(idx)}
              style={{
                marginLeft: 4, background: "none", border: "none",
                color: "#c084fc", cursor: "pointer", fontWeight: "bold"
              }}
              tabIndex={0}
              aria-label="Remove"
            >×</button>
          </span>
        )}
        {items.length < maxItems && (
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") handleAdd(); }}
            placeholder={placeholder}
            maxLength={maxLength}
            style={{
              background: "#16162a", color: "#c084fc", borderRadius: 5,
              padding: "4px 10px", fontSize: 13, border: "1px solid #666", minWidth: 80
            }}
          />
        )}
        {input.trim() && items.length < maxItems && (
          <button
            onClick={handleAdd}
            style={{marginLeft: 6, background: "#7c3aed", color: "#fff", border: "none",
              borderRadius: 4, padding: "2px 8px", fontWeight: 500}}
          >Add</button>
        )}
      </div>
    </div>
  );
}