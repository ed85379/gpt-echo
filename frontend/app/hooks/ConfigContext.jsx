import { createContext, useContext, useState, useEffect } from 'react';

// 1. Create the context
const ConfigContext = createContext();

// 2. Provider component
export function ConfigProvider({ children }) {
  const [config, setConfig] = useState({});
  const [profile, setProfile] = useState(null);  // <-- NEW
  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(true); // Optional: For profile-specific loading

  useEffect(() => {
    // Config fetch (as before)
    fetch('/api/config')
      .then(res => res.json())
      .then(data => {
        const clean = {};
        for (let key in data) {
          let val = data[key];
          if (val === "True" || val === "true") val = true;
          else if (val === "False" || val === "false") val = false;
          else clean[key] = val;
        }
        setConfig(clean);
        setLoading(false);
      });

    // Muse profile fetch
    fetch('/api/muse_profile')
      .then(res => res.json())
      .then(data => {
        setProfile(data);
        setProfileLoading(false);
      });
  }, []);

  return (
    <ConfigContext.Provider
      value={{
        config,
        loading,
        // Add the new fields:
        museProfile: profile,
        museProfileLoading: profileLoading,
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