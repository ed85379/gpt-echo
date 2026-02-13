"use client";
import { createContext, useContext, useState, useEffect } from 'react';

// 1. Create the context
const FeaturesContext = createContext();

export function FeaturesProvider({ children }) {
  const [adminConfig, setAdminConfig] = useState({});

  const [adminLoading, setAdminLoading] = useState(true);

  const POLL_MS = 30_000; // 1 minute; change to 300_000 for 5 minutes

  // --- helpers ---

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

  useEffect(() => {
    const adminConfigController = new AbortController();

    // initial loads
    loadAdminConfig(adminConfigController.signal);

    // 🔁 polling
    const configInterval = setInterval(() => {
      const c = new AbortController();
      loadAdminConfig(c.signal);
    }, POLL_MS);


    return () => {
      adminConfigController.abort();
      clearInterval(configInterval);
    };
  }, []);

  return (
    <FeaturesContext.Provider
      value={{
        adminConfig,
        adminLoading,
      }}
    >
      {children}
    </FeaturesContext.Provider>
  );
}

// 3. Hook for easy access
export function useFeatures() {
  return useContext(FeaturesContext);
}