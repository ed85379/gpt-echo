"use client";

import { useState, useEffect } from "react";
import timezones from 'timezones-list';
import { useConfig } from "@/hooks/ConfigContext";
import { SETTINGS_META } from "@/config/configMeta";



function ConfigIntro() {
  return (
    <div className="mb-6 p-4 bg-gradient-to-r from-purple-950 via-neutral-950 to-neutral-950 rounded shadow text-neutral-200 border border-purple-900">
      <div className="text-lg font-bold text-purple-200 mb-1">
        Muse Configuration
      </div>
      <div className="text-sm text-neutral-300">
        Here you shape your Muse, one setting at a time—tuning the voice,
        memory, and mood of your digital companion.
        <span className="ml-2 text-purple-400 italic">
          Every toggle is an invitation to become.
        </span>
      </div>
    </div>
  );
}

function SectionStatus({ sectionKey, saving, saved, error }) {
  if (saving[sectionKey]) {
    return <span className="text-xs text-purple-400">⏳ Saving…</span>;
  }
  if (error[sectionKey]) {
    return (
      <span className="text-xs text-red-400">
        ⚠ {error[sectionKey]}
      </span>
    );
  }
  if (saved[sectionKey]) {
    return (
      <span className="text-xs text-green-400">
        ✔ Saved!
      </span>
    );
  }
  return null;
}

function UserProfileSection({
  profile,
  editMode,
  saving,
  saved,
  error,
  onSaveSection,
}) {
  const [localProfile, setLocalProfile] = useState(profile || {});
  const profileMeta = SETTINGS_META.user_config || {};
  const [timezones, setTimezones] = useState([]);

  useEffect(() => {
    if (typeof Intl !== 'undefined' && typeof Intl.supportedValuesOf !== 'undefined') {
      // Get an array of all IANA time zone names (e.g., "America/New_York", "Europe/London")
      const timeZoneNames = Intl.supportedValuesOf('timeZone');
      setTimezones(timeZoneNames);
    } else {
      console.error('Intl.supportedValuesOf not supported in this browser.');
      // Fallback or use a library
    }
  }, []);

  useEffect(() => {
    setLocalProfile(profile || {});
  }, [profile]);

  const handleChange = (key, value) => {
    setLocalProfile(prev => ({ ...prev, [key]: value }));
  };

  const handleBlur = () => {
    if (!editMode) return;
    // avoid useless PATCH if nothing changed
    if (JSON.stringify(localProfile) === JSON.stringify(profile || {})) return;
    onSaveSection("user_config", localProfile);
  };

  return (
    <div className="bg-neutral-900 rounded-xl shadow border border-purple-900/40 p-5">
      <div className="font-semibold text-purple-300 text-base mb-3">
        User Profile
      </div>
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-neutral-400 mb-1">
            {profileMeta.USER_NAME?.label || "Display Name"}
          </label>
          <p className="text-[11px] text-neutral-500 mb-1">
            {profileMeta.USER_NAME?.description}
          </p>
          <input
            type="text"
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localProfile.USER_NAME || ""}
            disabled={!editMode}
            onChange={e => handleChange("USER_NAME", e.target.value)}
            onBlur={handleBlur}
          />
        </div>
        <div>

          <label className="block text-xs text-neutral-400 mb-1">
            {profileMeta.USER_TIMEZONE?.label || "Timezone"}
          </label>
          <p className="text-[11px] text-neutral-500 mb-1">
            {profileMeta.USER_TIMEZONE?.description}
          </p>
          <select className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700">
            {timezones.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </select>
          <input
            type="text"
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localProfile.USER_TIMEZONE || ""}
            disabled={!editMode}
            onChange={e => handleChange("USER_TIMEZONE", e.target.value)}
            onBlur={handleBlur}
          />
        </div>
        {/* Add ZIP / COUNTRY later if you want */}
      </div>

      <div className="mt-3">
        <SectionStatus
          sectionKey="user_config"
          saving={saving}
          saved={saved}
          error={error}
        />
      </div>
    </div>
  );
}

// Simple read-only stubs you can flesh out later

function ModelsSection({ models }) {
  const modelMeta = SETTINGS_META.model_config || {};
  const openaiModelMeta = modelMeta.OPENAI_MODEL || {};
  const options = openaiModelMeta.options || [];
  if (!models || Object.keys(models).length === 0) return null;

  return (
    <div className="bg-neutral-900 rounded-xl shadow border border-purple-900/40 p-5">
      <div className="font-semibold text-purple-300 text-base mb-3">
        Models
      </div>
      <div className="space-y-2 text-sm text-neutral-300">
        {Object.entries(models).map(([key, value]) => (
          <div key={key} className="flex justify-between gap-4">
            <span className="font-mono text-purple-200">{key}</span>
            <span className="truncate">{String(value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MuseConfigSection({ museConfig }) {
  if (!museConfig || Object.keys(museConfig).length === 0) return null;

  return (
    <div className="bg-neutral-900 rounded-xl shadow border border-purple-900/40 p-5">
      <div className="font-semibold text-purple-300 text-base mb-3">
        Muse Config
      </div>
      <div className="space-y-2 text-sm text-neutral-300">
        {Object.entries(museConfig).map(([key, value]) => (
          <div key={key} className="flex justify-between gap-4">
            <span className="font-mono text-purple-200">{key}</span>
            <span className="truncate">{String(value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MuseFeaturesSection({ features }) {
  if (!features || Object.keys(features).length === 0) return null;

  return (
    <div className="bg-neutral-900 rounded-xl shadow border border-purple-900/40 p-5">
      <div className="font-semibold text-purple-300 text-base mb-3">
        Muse Features
      </div>
      <div className="space-y-2 text-sm text-neutral-300">
        {Object.entries(features).map(([key, value]) => (
          <div key={key} className="flex justify-between items-center gap-4">
            <span className="font-mono text-purple-200">{key}</span>
            <span className="text-xs text-neutral-400">
              {typeof value === "boolean" ? (value ? "Enabled" : "Disabled") : String(value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ApiKeysSection({ apiKeys }) {
  if (!apiKeys || Object.keys(apiKeys).length === 0) return null;

  return (
    <div className="bg-neutral-900 rounded-xl shadow border border-purple-900/40 p-5">
      <div className="font-semibold text-purple-300 text-base mb-3">
        API Keys
      </div>
      <div className="space-y-2 text-sm text-neutral-300">
        {Object.entries(apiKeys).map(([key, value]) => (
          <div key={key} className="flex justify-between items-center gap-4">
            <span className="font-mono text-purple-200">{key}</span>
            <span className="truncate text-neutral-500">
              {value ? "••••••••" : "(not set)"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

const ConfigTab = () => {
  const { userConfig, userLoading, updateUserConfig } = useConfig();
  const [editMode, setEditMode] = useState(false);
  const [saving, setSaving] = useState({});
  const [error, setError] = useState({});
  const [saved, setSaved] = useState({});

  const handleSectionUpdate = async (section, updatedSection) => {
    setSaving(s => ({ ...s, [section]: true }));
    setError(e => ({ ...e, [section]: undefined }));

    try {
      await updateUserConfig({
        section,
        data: updatedSection,
      });
      setSaved(s => ({ ...s, [section]: true }));
      setTimeout(() => {
        setSaved(s => ({ ...s, [section]: false }));
      }, 1200);
    } catch (err) {
      setError(e => ({
        ...e,
        [section]: err?.message || "Save failed",
      }));
    } finally {
      setSaving(s => ({ ...s, [section]: false }));
    }
  };

  if (userLoading || !userConfig) {
    return (
      <div className="p-6 text-neutral-400 bg-neutral-950 h-full">
        Loading settings…
      </div>
    );
  }

  const profile = userConfig.user_config || {};
  const models = userConfig.model_config || {};
  const museConfig = userConfig.muse_config || {};
  const features = userConfig.muse_features || {};
  const apiKeys = userConfig.api_keys || {};

  return (
    <div className="p-6 text-white bg-neutral-950 h-full flex flex-col min-h-0">
      <ConfigIntro />

      <div className="flex justify-between items-center mb-4">
        <div className="text-xs text-neutral-500">
          Beta layout — sections will get more polish later.
        </div>
        <div className="flex items-center gap-2">
          <span
            className={
              editMode
                ? "text-neutral-400"
                : "font-bold text-purple-400"
            }
          >
            Read Only
          </span>
          <button
            className={`relative inline-block w-12 h-6 rounded-full transition-colors duration-300
              ${editMode ? "bg-purple-600" : "bg-neutral-700"}`}
            onClick={() => setEditMode(e => !e)}
            aria-label="Toggle Edit Mode"
          >
            <span
              className={`absolute left-1 top-1 w-4 h-4 rounded-full bg-white transition-transform duration-300
                ${editMode ? "translate-x-6" : ""}`}
            />
          </button>
          <span
            className={
              editMode
                ? "font-bold text-purple-400"
                : "text-neutral-400"
            }
          >
            Edit
          </span>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="grid gap-6">
          <UserProfileSection
            profile={profile}
            editMode={editMode}
            saving={saving}
            saved={saved}
            error={error}
            onSaveSection={handleSectionUpdate}
          />
          <ModelsSection models={models} />
          <MuseConfigSection museConfig={museConfig} />
          <MuseFeaturesSection features={features} />
          <ApiKeysSection apiKeys={apiKeys} />
        </div>
      </div>
    </div>
  );
};

export default ConfigTab;