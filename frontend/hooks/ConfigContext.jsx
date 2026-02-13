"use client";
import { createContext, useContext, useState, useEffect } from 'react';

// 1. Create the context
const ConfigContext = createContext();

export function ConfigProvider({ children }) {
  const [config, setConfig] = useState({});
  const [userConfig, setUserConfig] = useState({});
  const [adminConfig, setAdminConfig] = useState({});
  const [profile, setProfile] = useState(null);
  const [states, setStates] = useState(null);
  //const [pollstates, setPollstates] = useState(null);

  const [loading, setLoading] = useState(true);
  const [userLoading, setUserLoading] = useState(true);
  const [adminLoading, setAdminLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(true);
  const [statesLoading, setStatesLoading] = useState(true);
  //const [pollstatesLoading, setPollstatesLoading] = useState(true);

  //const POLL_MS = 600_000; // 1 minute; change to 300_000 for 5 minutes

  // --- helpers ---

  async function loadConfig(signal) {
    try {
      const res = await fetch('/api/config/', { signal });
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

  async function loadUserConfig(signal) {
    try {
      const res = await fetch('/api/config/user', { signal });
      if (!res.ok) throw new Error("Failed to fetch user config");
      const data = await res.json();

      // Strip out _id, keep the rest as-is
      const { _id, ...rest } = data;
      setUserConfig(rest);
      setUserLoading(false);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Error loading user config:", err);
    }
  }

  async function loadAdminConfig(signal) {
    try {
      const res = await fetch('/api/config/admin', { signal });
      if (!res.ok) throw new Error("Failed to fetch admin config");
      const data = await res.json();

      // Strip out _id, keep the rest as-is
      const { _id, ...rest } = data;
      setAdminConfig(rest);
      setAdminLoading(false);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Error loading admin config:", err);
    }
  }

  async function loadProfile(signal) {
    try {
      const res = await fetch('/api/muse_profile/', { signal });
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
      const res = await fetch('/api/states/', { signal });
      if (!res.ok) throw new Error("Failed to fetch states");
      const data = await res.json();
      setStates(data);
      setStatesLoading(false);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Error loading states:", err);
    }
  }
{/*
  async function loadPollstates(signal) {
    try {
      const res = await fetch('/api/uipolling/', { signal });
      if (!res.ok) throw new Error("Failed to fetch polling states");
      const data = await res.json();
      setPollstates(data);
      setPollstatesLoading(false);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Error loading polling states:", err);
    }
  }
*/}

  async function updateUserConfig(patch) {
    // patch: { section: "user_config", data: { ... } }
    const res = await fetch("/api/config/user", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Failed to update user config");
    }
    const data = await res.json();
    const { _id, ...rest } = data;
    setUserConfig(rest);
  }

  useEffect(() => {
    const configController = new AbortController();
    const userConfigController = new AbortController();
    const adminConfigController = new AbortController();
    const profileController = new AbortController();
    const statesController = new AbortController();
    //const pollstatesController = new AbortController();

    // initial loads
    loadConfig(configController.signal);
    loadUserConfig(userConfigController.signal);
    loadAdminConfig(adminConfigController.signal);
    loadProfile(profileController.signal);
    loadStates(statesController.signal);
    //loadPollstates(pollstatesController.signal);

    // 🔁 polling
    //const configInterval = setInterval(() => {
    //  const c = new AbortController();
    //  loadConfig(c.signal);
    //}, POLL_MS);

    //const profileInterval = setInterval(() => {
    //  const p = new AbortController();
    //  loadProfile(p.signal);
    //}, POLL_MS);

    //const pollstatesInterval = setInterval(() => {
    //  const s = new AbortController();
    //  loadPollstates(s.signal);
    //}, POLL_MS);

    //return () => {
    //  configController.abort();
    //  profileController.abort();
    //  pollstatesController.abort();
    //  clearInterval(configInterval);
    //  clearInterval(profileInterval);
    //  clearInterval(pollstatesInterval);
    //};
  }, []);

  return (
    <ConfigContext.Provider
      value={{
        config,
        loading,
        userConfig,
        userLoading,
        adminConfig,
        adminLoading,
        museProfile: profile,
        museProfileLoading: profileLoading,
        uiStates: states,
        uiStatesLoading: statesLoading,
//        uiPollstates: pollstates,
//        uiPollstatesLoading: pollstatesLoading,
        updateUserConfig,
        setUserConfig,
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