"use client";
import React, { useEffect, useState, useMemo } from "react";
import { SquarePlus, SquarePen } from 'lucide-react';

const MAX_LENGTH_DESC = 512;
const MAX_LENGTH_NOTE = 256;
const MAX_LENGTH_TAG = 24;

function ListEditor({
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

function TagEditor({
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

// --- Details Card with Editable Fields ---
function ProjectDetailsCard({ project, projectMap, projects, projectsLoading, onToggleVisibility, toggleLoading, onProjectChange }) {
  const [editing, setEditing] = useState({name: false, description: false, tags: false, notes: false});
  const [draft, setDraft] = useState({
    name: project.name,
    description: project.description ?? ""
  });
  const [tagList, setTagList] = useState(project.tags || []);
  const [noteList, setNoteList] = useState(project.notes || []);


  // Only reset local state when switching projects (not on every save/edit)
  useEffect(() => {
    setEditing({name: false, description: false, tags: false, notes: false});
    setDraft({
      name: project.name,
      description: project.description ?? ""
    });
    setTagList(project.tags || []);
    setNoteList(project.notes || []);
  }, [project._id]);

  // Save handlers
  const handleSave = (field) => {
    if (field === "tags") {
            console.log("Saving tags, tagList is:", tagList);
      onProjectChange({ tags: tagList });
      setEditing(e => ({...e, tags: false}));
    } else if (field === "notes") {
      const cleaned = noteList.map(n => n.trim()).filter(Boolean);
      onProjectChange({ notes: cleaned });
      setEditing(e => ({...e, notes: false}));
    } else {
      onProjectChange({ [field]: draft[field] });
      setEditing(e => ({...e, [field]: false}));
    }
  };

  const handleEdit = (field) => setEditing(e => ({...e, [field]: true}));



useEffect(() => {
  setTagList(project.tags || []);
}, [project]);

const handleAddTag = (newTag) => {
    console.log("handleAdd called!", input);
  setTagList(prev => (!prev.includes(newTag) ? [...prev, newTag] : prev));
};

const handleRemoveTag = idx => {
  setTagList(prev => prev.filter((_, i) => i !== idx));
};

const handleSaveTags = () => {
  console.log("PATCHING tags:", tagList); // Debug here
  onProjectChange({ tags: tagList });
  setEditing(e => ({...e, tags: false}));
};

  return (
    <div>

    <div style={{ marginBottom: 18 }}>
      <span style={{ fontWeight: "bold", color: "#bbb" }}>Description: </span>
      {editing.description ? (
        <form
          onSubmit={e => { e.preventDefault(); handleSave("description"); }}
          style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", marginTop: 6 }}
        >
          <textarea
            value={draft.description}
            onChange={e => setDraft(d => ({ ...d, description: e.target.value }))}
            maxLength={MAX_LENGTH_DESC}
            autoFocus
            rows={2}
            style={{
              fontWeight: "bold",
              fontSize: 16,
              background: "none",
              color: "#fff",
              border: draft.description.length > MAX_LENGTH_DESC ? "2px solid #f55" : "1px solid #666",
              borderRadius: 6,
              outline: "none",
              width: "100%",
              padding: "6px 12px",
              marginBottom: 4,
              minWidth: 280
            }}
            onBlur={() => handleSave("description")}
          />
          <div
            style={{
              textAlign: "right",
              fontSize: 12,
              color: draft.description.length > MAX_LENGTH_DESC ? "#f55" : "#bbb",
              alignSelf: "flex-end",
              marginBottom: 4,
            }}
          >
            {draft.description.length}/{MAX_LENGTH_DESC}
          </div>
          {/* Optional: Save/Cancel buttons */}
          {/* <div>
            <button style={miniBtnStyle} type="submit">Save</button>
            <button style={miniBtnStyle} type="button" onClick={() => setEditing(e => ({ ...e, description: false }))}>Cancel</button>
          </div> */}
        </form>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", marginTop: 6 }}>
          <span style={{
            background: "#16162a",
            color: "#cbd5fa",
            borderRadius: 6,
            padding: "6px 12px",
            display: "inline-block",
            fontSize: 15,
            minWidth: 280,
            marginBottom: 4,
          }}>
            {project.description || <span style={{ color: "#777" }}>none</span>}
          </span>
          <SquarePen size={18} strokeWidth={1.5} onClick={() => handleEdit("description")} style={{ cursor: "pointer" }} />
        </div>
      )}
    </div>
      <div style={{marginBottom: 8}}>
        <span style={{fontWeight: "bold", color: "#bbb"}}>Tags: </span>
        {editing.tags ? (
          <div>
            <TagEditor
              items={tagList}
              setItems={setTagList}
              placeholder="Add tag…"
              maxItems={10}
              maxLength={24}
              allowEdit={false}
            />
            <div style={{marginTop: 6}}>
              <button style={miniBtnStyle} onClick={handleSaveTags}>Save</button>
              <button style={miniBtnStyle} onClick={() => {
                setTagList(project.tags || []);
                setEditing(e => ({...e, tags: false}));
              }}>Cancel</button>
            </div>
          </div>
        ) : (
          <>
            {(project.tags || []).length === 0 ?
              <span style={{color: "#777"}}>none</span> :
              project.tags.map(tag => (
                <span key={tag} style={{
                  background: "#7c3aed33", color: "#c084fc",
                  borderRadius: 5, padding: "2px 8px", marginRight: 6, fontSize: 13
                }}>{tag}</span>
              ))
            }
            <SquarePlus size={18} strokeWidth={1.5} onClick={() => handleEdit("tags")} />
          </>
        )}
      </div>
      <div style={{marginBottom: 18}}>
        <span style={{fontWeight: "bold", color: "#bbb"}}>Notes: </span>
        {editing.notes ? (
          <div>
            <ListEditor
              items={noteList}
              setItems={setNoteList}
              placeholder="Add note…"
              maxItems={50}
              maxLength={256}
              allowEdit={true}
            />
            <div style={{marginTop: 6}}>
              <button style={miniBtnStyle} onClick={() => handleSave("notes")}>Save</button>
              <button style={miniBtnStyle} onClick={() => {
                setNoteList(project.notes || []);
                setEditing(e => ({...e, notes: false}));
              }}>Cancel</button>
            </div>
          </div>
        ) : (
          <>
            {(project.notes || []).length === 0 ?
              <span style={{ color: "#777" }}>none</span>
              : project.notes.map((note, i) => (
                <span key={i} style={{
                  display: "block",
                  background: "#16162a", color: "#cbd5fa", borderRadius: 6,
                  padding: "6px 12px", fontSize: 15, minWidth: 280, marginBottom: 3, whiteSpace: "pre-wrap"
                }}>{note}</span>
              ))
            }
            <SquarePlus size={18} strokeWidth={1.5} onClick={() => handleEdit("notes")} />
          </>
        )}
      </div>
      <hr style={{border: "none", borderTop: "1px solid #282860", margin: "18px 0"}} />
     <div style={{
        display: "flex", gap: 32, marginBottom: 12, fontSize: 16, color: "#b1b1df"
      }}>
        <span>Messages: <b>{project.messageCount ?? "—"}</b></span>
        <span>Key Facts: <b>{project.cortexCount ?? "—"}</b></span>
      </div>
{/*       <div style={{
        marginTop: 10, fontSize: 14,
        color: project.hidden ? "#ef4444" : "#22c55e"
      }}>
        {project.hidden
          ? "Project data is hidden from your muse and OpenAI’s systems."
          : "Project data is accessible to your muse (and may be processed by OpenAI)."}
      </div>
      */}
      <footer style={{display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 24}}>
        {/*}<button style={{
          ...cardBtnStyle, background: "#ef444422", color: "#ff4455", border: "1px solid #ef4444"
        }}>Delete Project</button>*/}
      </footer>
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

export default ProjectDetailsCard;