// utils/statesFunctions.js

export async function patchStates(path, payload) {
  try {
    const res = await fetch(`/api/states/${path}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      console.error(`Failed to patch states at ${path}`, await res.text());
    }
  } catch (err) {
    console.error(`Error patching states at ${path}`, err);
  }
}

// Per‑project UI state
export function updateUiStateForProject(projectId, updates) {
  if (!projectId) return;
  return patchStates(`projects/${projectId}`, updates);
}

// Main / side tabs
export function updateNavState(updates) {
  return patchStates("nav", updates);
}

// Threads
export function updateThreadsState(updates) {
  return patchStates("threads", updates);
}