"use client";
import { createContext, useContext, useState, useEffect } from 'react';

// 1. Create the context
const ConfigContext = createContext();

export function ConfigProvider({ children }) {
  const [config, setConfig] = useState({});
  const [profile, setProfile] = useState(null);
  const [states, setStates] = useState(null);

  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(true);
  const [statesLoading, setStatesLoading] = useState(true);

  const POLL_MS = 60_000; // 1 minute; change to 300_000 for 5 minutes

  // --- helpers ---

  async function loadConfig(signal) {
    try {
      const res = await fetch('/api/config', { signal });
      if (!res.ok) throw new Error("Failed to fetch config");
      const data = await res.json();

      const clean = {};
      for (let key in data) {
        let val = data[key];
        if (val === "True" || val === "true") val = true;
        else if (val === "False" || val === "false") val = false;
        else clean[key] = val;
      }

      setConfig(clean);
      setLoading(false);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Error loading config:", err);
    }
  }

  async function loadProfile(signal) {
    try {
      const res = await fetch('/api/muse_profile', { signal });
      if (!res.ok) throw new Error("Failed to fetch muse profile");
      const data = await res.json();
      setProfile(data);
      setProfileLoading(false);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Error loading muse profile:", err);
    }
  }

  async function loadStates(signal) {
    try {
      const res = await fetch('/api/states', { signal });
      if (!res.ok) throw new Error("Failed to fetch states");
      const data = await res.json();
      setStates(data);
      setStatesLoading(false);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Error loading states:", err);
    }
  }

  useEffect(() => {
    const configController = new AbortController();
    const profileController = new AbortController();
    const statesController = new AbortController();

    // initial loads
    loadConfig(configController.signal);
    loadProfile(profileController.signal);
    loadStates(statesController.signal);

    // 🔁 polling
    const configInterval = setInterval(() => {
      const c = new AbortController();
      loadConfig(c.signal);
    }, POLL_MS);

    const profileInterval = setInterval(() => {
      const p = new AbortController();
      loadProfile(p.signal);
    }, POLL_MS);

    const statesInterval = setInterval(() => {
      const s = new AbortController();
      loadStates(s.signal);
    }, POLL_MS);

    return () => {
      configController.abort();
      profileController.abort();
      statesController.abort();
      clearInterval(configInterval);
      clearInterval(profileInterval);
      clearInterval(statesInterval);
    };
  }, []);

  return (
    <ConfigContext.Provider
      value={{
        config,
        loading,
        museProfile: profile,
        museProfileLoading: profileLoading,
        uiStates: states,
        uiStatesLoading: statesLoading,
      }}
    >
      {children}
    </ConfigContext.Provider>
  );
}

// 3. Hook for easy access
export function useConfig() {
  return useContext(ConfigContext);
}