// SettingsPanel.jsx
import { useState, useEffect, useCallback } from "react";
import { useTimezoneSelect, allTimezones } from "react-timezone-select";
import { countryCodes } from "country-codes-list";
import { CircleQuestionMark, Info } from "lucide-react";
import { useConfig  } from "@/hooks/ConfigContext";
import { useFeatures } from "@/hooks/FeaturesContext";
import { SETTINGS_META } from "@/config/configMeta";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import {
  Popover,
  PopoverContent,
  PopoverDescription,
  PopoverHeader,
  PopoverTitle,
  PopoverTrigger,
} from "@/components/ui/popover";
// import inputs, switches, etc.


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
  FieldLabelWithInfo,
  profile,
  editMode,
  saving,
  saved,
  error,
  hasPendingChanges,
  onFieldChange,
  onSaveSection,
}) {
  const [localProfile, setLocalProfile] = useState(profile || {});
  const profileMeta = SETTINGS_META.user_config || {};
  const labelStyle = "original"
  const timezones = {
    ...allTimezones,
  }
  const { options, parseTimezone } = useTimezoneSelect({ labelStyle, timezones })

  const countryCodes = require("country-codes-list");
  const countryCodesObject = countryCodes.customList(
    "countryCode",
    "[{countryCode}] {countryNameEn}"
  );

  // Turn it into an array of { value, label }
  const countryOptions = Object.entries(countryCodesObject).map(
    ([code, label]) => ({
      value: code,
      label, // e.g. "[US] United States: +1"
    })
  );


  const hours = Array.from({ length: 24 }, (_, h) => ({
    value: h,
    label: `${(h % 12) === 0 ? 12 : h % 12}:00 ${h < 12 ? "AM" : "PM"}`
  }));

  useEffect(() => {
    setLocalProfile(profile || {});
  }, [profile]);
{/*
  const handleChange = (key, value) => {
    setLocalProfile(prev => ({ ...prev, [key]: value }));
  };

  const handleUserSave = (section) => {
    if (!editMode) return;
    if (JSON.stringify(localProfile) === JSON.stringify(profile || {})) return;
    onSaveSection(section, localProfile);
  };


  const handleBlur = () => {
    if (!editMode) return;
    // avoid useless PATCH if nothing changed
    if (JSON.stringify(localProfile) === JSON.stringify(profile || {})) return;
    onSaveSection("user_config", localProfile);
  };
*/}


  return (
    <div className="bg-neutral-900 rounded-xl shadow border border-purple-900/40 p-5">
      <div className="space-y-3">
        <div>
          <FieldLabelWithInfo
            meta={profileMeta.USER_NAME}
            fallbackLabel="Display Name"
          />
          <input
            type="text"
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localProfile.USER_NAME || ""}
            disabled={!editMode}
            onChange={e => onFieldChange("USER_NAME", e.target.value)}
          />
        </div>
        <div>
          <FieldLabelWithInfo
            meta={profileMeta.USER_TIMEZONE}
            fallbackLabel="Timezone"
          />
          <select
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            onChange={(e) => handleChange("USER_TIMEZONE", e.currentTarget.value)}
            disabled={!editMode}
            value={localProfile.USER_TIMEZONE || ""}
          >
            {options.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <FieldLabelWithInfo
            meta={profileMeta.USER_COUNTRYCODE}
            fallbackLabel="Country code"
          />
          <select
            className="bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localProfile.USER_COUNTRYCODE || "US"}
            onChange={e => onFieldChange("USER_COUNTRYCODE", e.currentTarget.value)}
            disabled={!editMode}

          >
            {countryOptions.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <FieldLabelWithInfo
            meta={profileMeta.USER_ZIPCODE}
            fallbackLabel="Zip / Postal Code"
          />
          <input
            type="text"
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localProfile.USER_ZIPCODE || ""}
            onChange={e => onFieldChange("USER_ZIPCODE", e.target.value)}

            disabled={!editMode}
            placeholder="ZIP / Postal code"
          />
        </div>
        <div className="flex flex-col gap-1">
          <FieldLabelWithInfo
            meta={profileMeta.QUIET_HOURS}
            fallbackLabel="Quiet hours"
          />
          <div className="flex items-center gap-2">
            <select
              className="bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
              value={localProfile.QUIET_HOURS_START ?? 23}
              onChange={e => onFieldChange("QUIET_HOURS_START", parseInt(e.target.value, 10))}

              disabled={!editMode}
            >
              {hours.map(h => (
                <option key={h.value} value={h.value}>
                  {h.label}
                </option>
              ))}
            </select>
            <span className="text-neutral-400 text-sm">to</span>
            <select
              className="bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
              value={localProfile.QUIET_HOURS_END ?? 7}
              onChange={e => onFieldChange("QUIET_HOURS_END", parseInt(e.target.value, 10))}

              disabled={!editMode}
            >
              {hours.map(h => (
                <option key={h.value} value={h.value}>
                  {h.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <FieldLabelWithInfo
            meta={profileMeta.MEASUREMENT_UNITS}
            fallbackLabel="Measurement units"
          />
          <select
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            onChange={(e) => onFieldChange("MEASUREMENT_UNITS", e.currentTarget.value)}
            disabled={!editMode}
            value={localProfile.MEASUREMENT_UNITS || ""}
          >
            <option key="metric" value="metric">Metric</option>
            <option key="imperial" value="imperial">Imperial</option>
          </select>
        </div>
        <div>
          <button
            onClick={onSaveSection}
            disabled={!hasPendingChanges || !editMode || saving}
            className="bg-purple-700"
            style={{
              padding: "0.35rem 0.9rem",
              borderRadius: "4px",
              border: "none",
              fontSize: "0.9rem",
              cursor: "pointer",
              opacity: 1 ,
              color: "white",
              transition: "background-color 120ms ease, opacity 120ms ease",
            }}
          >
            {saving ? "Saving..." : "Save changes"}
          </button>
          {hasPendingChanges && !saving && (
            <span className="text-xs text-purple-400"> Unsaved changes</span>
          )}
          {saved && <span className="text-xs text-purple-400"> Saved</span>}
          {error && <span className="text-xs text-red-500"> {error}</span>}
        </div>
      </div>

    </div>
  );
}

function LLMSection({
  FieldLabelWithInfo,
  profile,
  editMode,
  saving,
  saved,
  error,
  hasPendingChanges,
  onFieldChange,
  onSaveSection,
  llm,
}) {
  const modelMeta = SETTINGS_META.llm_config || {};
  const openaiModelOptions = modelMeta.OPENAI_MODEL.options || {};
  const openaiFullModelOptions = modelMeta.OPENAI_FULL_MODEL.options || {};
  const openaiWhisperModelOptions = modelMeta.OPENAI_WHISPER_MODEL.options || {};
  if (!llm || Object.keys(llm).length === 0) return null;
  const [localModels, setLocalModels] = useState(llm || {});
  const [show, setShow] = useState(false);

  useEffect(() => {
    setLocalModels(llm || {});
  }, [llm]);

  return (
    <div className="bg-neutral-900 rounded-xl shadow border border-purple-900/40 p-5">
      <div className="space-y-3">
        <div>
          <FieldLabelWithInfo
            meta={modelMeta.OPENAI_API_KEY}
            fallbackLabel="OpenAI API Key"
          />
          <input
            type={show ? "text" : "password"}
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localModels.OPENAI_API_KEY || ""}
            disabled={!editMode}
            onChange={e => onFieldChange("OPENAI_API_KEY", e.target.value)}
          />
          <button
            type="button"
            className="px-2 py-1 text-xs rounded border border-neutral-600 text-neutral-300"
            onClick={() => setShow(s => !s)}
            disabled={!editMode}
          >
            {show ? "Hide" : "Show"}
          </button>
        </div>
        <div>
          <FieldLabelWithInfo
            meta={modelMeta.OPENAI_MODEL}
            fallbackLabel="OpenAI Main Model"
          />
          <select
            className="bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localModels.OPENAI_MODEL || "gpt-5.1"}
            onChange={e => onFieldChange("OPENAI_MODEL", e.currentTarget.value)}
            disabled={!editMode}
          >
            {openaiModelOptions.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <FieldLabelWithInfo
            meta={modelMeta.OPENAI_FULL_MODEL}
            fallbackLabel="OpenAI Journal Model"
          />
          <select
            className="bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localModels.OPENAI_FULL_MODEL || "gpt-5.1"}
            onChange={e => onFieldChange("OPENAI_FULL_MODEL", e.currentTarget.value)}
            disabled={!editMode}
          >
            {openaiFullModelOptions.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <FieldLabelWithInfo
            meta={modelMeta.OPENAI_WHISPER_MODEL}
            fallbackLabel="OpenAI Decision Model"
          />
          <select
            className="bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localModels.OPENAI_WHISPER_MODEL || "gpt-5-nano"}
            onChange={e => onFieldChange("OPENAI_WHISPER_MODEL", e.currentTarget.value)}
            disabled={!editMode}
          >
            {openaiWhisperModelOptions.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <button
            onClick={onSaveSection}
            disabled={!hasPendingChanges || !editMode || saving}
            className="bg-purple-700"
            style={{
              padding: "0.35rem 0.9rem",
              borderRadius: "4px",
              border: "none",
              fontSize: "0.9rem",
              cursor: "pointer",
              opacity: 1 ,
              color: "white",
              transition: "background-color 120ms ease, opacity 120ms ease",
            }}
          >
            {saving ? "Saving..." : "Save changes"}
          </button>
          {hasPendingChanges && !saving && (
            <span className="text-xs text-purple-400"> Unsaved changes</span>
          )}
          {saved && <span className="text-xs text-purple-400"> Saved</span>}
          {error && <span className="text-xs text-red-500"> {error}</span>}
        </div>
      </div>
    </div>
  );
}

function TTSSection({
  FieldLabelWithInfo,
  tts,
  editMode,
  saving,
  saved,
  error,
  hasPendingChanges,
  onFieldChange,
  onSaveSection,
  museName,
  userName,
  speak,
  setIsTTSPlaying,
  isThisPlaying,
  Equalizer,
  speakingMessageId,
}) {
  const ttsMeta = SETTINGS_META.tts_config || {};
  if (!tts || Object.keys(tts).length === 0) return null;
  const [localTTS, setLocalTTS] = useState(tts || {});
  const [show, setShow] = useState(false);



  const handleTestVoice = useCallback(() => {
    if (!speak) return;

    const sampleLine =
      `Hello ${userName}! This is ${museName} speaking. ` +
      "Try changing the sliders and listen for how my tone and pacing shift.";

    const fakeMsg = {
      text: sampleLine,
      message_id: "tts-test-" + Date.now(),
      from: "muse",
    };

    const overrides = {
      speed: Number(localTTS.ELEVENLABS_VOICE_SPEED ?? 1.0),
      similarity: Number(localTTS.ELEVENLABS_VOICE_SIMILARITY ?? 0.75),
      stability: Number(localTTS.ELEVENLABS_VOICE_STABILITY ?? 0.6),
    };

    speak(fakeMsg, () => setIsTTSPlaying(false), overrides);
  }, [speak, userName, museName, localTTS, setIsTTSPlaying]);

  useEffect(() => {
    setLocalTTS(tts || {});
  }, [tts]);

  return (
    <div className="bg-neutral-900 rounded-xl shadow border border-purple-900/40 p-5">
      <div className="space-y-3">
        <div>
          <FieldLabelWithInfo
            meta={ttsMeta.ELEVENLABS_API_KEY}
            fallbackLabel="Elevenlabs API Key"
          />
          <input
            type={show ? "text" : "password"}
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localTTS.ELEVENLABS_API_KEY || ""}
            disabled={!editMode}
            onChange={e => onFieldChange("ELEVENLABS_API_KEY", e.target.value)}
          />
          <button
            type="button"
            className="px-2 py-1 text-xs rounded border border-neutral-600 text-neutral-300"
            onClick={() => setShow(s => !s)}
            disabled={!editMode}
          >
            {show ? "Hide" : "Show"}
          </button>
        </div>
        <div>
          <FieldLabelWithInfo
            meta={ttsMeta.ELEVENLABS_VOICE_ID}
            fallbackLabel="Voice ID"
          />
          <input
            type="text"
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localTTS.ELEVENLABS_VOICE_ID || ""}
            onChange={e => onFieldChange("ELEVENLABS_VOICE_ID", e.target.value)}
            disabled={!editMode}
            placeholder="Voice ID"
          />
        </div>
        <div>
          <FieldLabelWithInfo
            meta={ttsMeta.ELEVENLABS_VOICE_SPEED}
            fallbackLabel="Voice Speed"
          />
          <div className="flex items-center gap-2 w-full">
            <input
              type="range"
              min={0.7}
              max={1.2}
              step={0.01}
              value={parseFloat(localTTS.ELEVENLABS_VOICE_SPEED ?? 1.0)}
              onChange={e => onFieldChange("ELEVENLABS_VOICE_SPEED", parseFloat(e.target.value))}
              className="accent-purple-500 flex-1"
            /> ({Number(localTTS.ELEVENLABS_VOICE_SPEED ?? 1.0).toFixed(2)})
          </div>
        </div>
        <div>
          <FieldLabelWithInfo
            meta={ttsMeta.ELEVENLABS_VOICE_SIMILARITY}
            fallbackLabel="Voice similarity"
          />
          <div className="flex items-center gap-2 w-full">
            <input
              type="range"
              min={0.0}
              max={1.0}
              step={0.01}
              value={parseFloat(localTTS.ELEVENLABS_VOICE_SIMILARITY ?? 1.0)}
              onChange={e => onFieldChange("ELEVENLABS_VOICE_SIMILARITY", parseFloat(e.target.value))}
              className="accent-purple-500 flex-1"
            /> ({Number(localTTS.ELEVENLABS_VOICE_SIMILARITY ?? 1.0).toFixed(2)})
          </div>
        </div>
        <div>
          <div>
          <FieldLabelWithInfo
            meta={ttsMeta.ELEVENLABS_VOICE_STABILITY}
            fallbackLabel="Voice stability"
          />
          </div>
          <div className="flex items-center gap-2 w-full">
            <input
              type="range"
              min={0.0}
              max={1.0}
              step={0.01}
              value={parseFloat(localTTS.ELEVENLABS_VOICE_STABILITY ?? 1.0)}
              onChange={e => onFieldChange("ELEVENLABS_VOICE_STABILITY", parseFloat(e.target.value))}
              className="accent-purple-500 flex-1"
            /> ({Number(localTTS.ELEVENLABS_VOICE_STABILITY ?? 1.0).toFixed(2)})
          </div>
          <button
            type="button"
            onClick={handleTestVoice}
            className="mt-3 inline-flex items-center rounded bg-purple-600 px-3 py-1 text-xs font-medium text-white hover:bg-purple-500"
          >
            Test voice
          </button> <Equalizer isActive={isThisPlaying} />
        </div>
        <div>
          <button
            onClick={onSaveSection}
            disabled={!hasPendingChanges || !editMode || saving}
            className="bg-purple-700"
            style={{
              padding: "0.35rem 0.9rem",
              borderRadius: "4px",
              border: "none",
              fontSize: "0.9rem",
              cursor: "pointer",
              opacity: 1 ,
              color: "white",
              transition: "background-color 120ms ease, opacity 120ms ease",
            }}
          >
            {saving ? "Saving..." : "Save changes"}
          </button>
          {hasPendingChanges && !saving && (
            <span className="text-xs text-purple-400"> Unsaved changes</span>
          )}
          {saved && <span className="text-xs text-purple-400"> Saved</span>}
          {error && <span className="text-xs text-red-500"> {error}</span>}
        </div>
      </div>
    </div>
  );
}

function SocialSection({
  FieldLabelWithInfo,
  social,
  editMode,
  saving,
  saved,
  error,
  hasPendingChanges,
  onFieldChange,
  onSaveSection,
}) {
  const socialMeta = SETTINGS_META.social_config || {};
  if (!social || Object.keys(social).length === 0) return null;
  const [localSocial, setLocalSocial] = useState(social || {});
  const [show, setShow] = useState(false);

  useEffect(() => {
    setLocalSocial(social || {});
  }, [social]);

  return (
    <div className="bg-neutral-900 rounded-xl shadow border border-purple-900/40 p-5">
      <div className="space-y-3">
        <div>
          <FieldLabelWithInfo
            meta={socialMeta.DISCORD_TOKEN}
            fallbackLabel="Discord Token"
          />
          <input
            type={show ? "text" : "password"}
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localSocial.DISCORD_TOKEN || ""}
            disabled={!editMode}
            onChange={e => onFieldChange("DISCORD_TOKEN", e.target.value)}
          />
          <button
            type="button"
            className="px-2 py-1 text-xs rounded border border-neutral-600 text-neutral-300"
            onClick={() => setShow(s => !s)}
            disabled={!editMode}
          >
            {show ? "Hide" : "Show"}
          </button>
        </div>
        <div>
          <FieldLabelWithInfo
            meta={socialMeta.DISCORD_GUILD_NAME}
            fallbackLabel="Discord Server Name"
          />
          <input
            type="text"
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localSocial.DISCORD_GUILD_NAME || ""}
            onChange={e => onFieldChange("DISCORD_GUILD_NAME", e.target.value)}
            disabled={!editMode}
            placeholder="Server Name"
          />
        </div>
        <div>
          <FieldLabelWithInfo
            meta={socialMeta.DISCORD_CHANNEL_NAME}
            fallbackLabel="Discord Channel Name"
          />
          <input
            type="text"
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localSocial.DISCORD_CHANNEL_NAME || ""}
            onChange={e => onFieldChange("DISCORD_CHANNEL_NAME", e.target.value)}
            disabled={!editMode}
            placeholder="Channel Name"
          />
        </div>
        <div>
          <FieldLabelWithInfo
            meta={socialMeta.PRIMARY_USER_DISCORD_ID}
            fallbackLabel="Your personal Discord ID"
          />
          <input
            type="text"
            className="w-full bg-neutral-800 text-white rounded p-2 text-sm border border-neutral-700"
            value={localSocial.PRIMARY_USER_DISCORD_ID || ""}
            onChange={e => onFieldChange("PRIMARY_USER_DISCORD_ID", e.target.value)}
            disabled={!editMode}
            placeholder="Discord User ID"
          />
        </div>
        <div>
          <button
            onClick={onSaveSection}
            disabled={!hasPendingChanges || !editMode || saving}
            className="bg-purple-700"
            style={{
              padding: "0.35rem 0.9rem",
              borderRadius: "4px",
              border: "none",
              fontSize: "0.9rem",
              cursor: "pointer",
              opacity: 1 ,
              color: "white",
              transition: "background-color 120ms ease, opacity 120ms ease",
            }}
          >
            {saving ? "Saving..." : "Save changes"}
          </button>
          {hasPendingChanges && !saving && (
            <span className="text-xs text-purple-400"> Unsaved changes</span>
          )}
          {saved && <span className="text-xs text-purple-400"> Saved</span>}
          {error && <span className="text-xs text-red-500"> {error}</span>}
        </div>
      </div>
    </div>
  );
}

function MuseFeatures({
  FieldLabelWithInfo,
  profile,
  editMode,
  saving,
  saved,
  error,
  hasPendingChanges,
  onFieldChange,
  onSaveSection,
  features,
}) {
  const featuresMeta = SETTINGS_META.muse_features || {};
  if (!features || Object.keys(features).length === 0) return null;
  const [localFeatures, setLocalFeatures] = useState(features || {});

  useEffect(() => {
    setLocalFeatures(features || {});
  }, [features]);

  return (
    <div className="bg-neutral-900 rounded-xl shadow border border-purple-900/40 p-5">
      <div className="space-y-3">
        {Object.entries(features).map(([key, value]) => (
          <div key={key} className="flex items-center justify-between gap-2">
            <FieldLabelWithInfo
              meta={featuresMeta[key]}
              fallbackLabel="Feature"
            />
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-neutral-700 bg-neutral-800 text-violet-400"
              checked={!!localFeatures[key]}
              disabled={!editMode}
              onChange={e => onFieldChange(key, e.target.checked)}
            />
          </div>
        ))}
        <div>
          <button
            onClick={onSaveSection}
            disabled={!hasPendingChanges || !editMode || saving}
            className="bg-purple-700"
            style={{
              padding: "0.35rem 0.9rem",
              borderRadius: "4px",
              border: "none",
              fontSize: "0.9rem",
              cursor: "pointer",
              opacity: 1 ,
              color: "white",
              transition: "background-color 120ms ease, opacity 120ms ease",
            }}
          >
            {saving ? "Saving..." : "Save changes"}
          </button>
          {hasPendingChanges && !saving && (
            <span className="text-xs text-purple-400"> Unsaved changes</span>
          )}
          {saved && <span className="text-xs text-purple-400"> Saved</span>}
          {error && <span className="text-xs text-red-500"> {error}</span>}
        </div>
      </div>
    </div>
  );
}

export default function SettingsPanel({
  audioControls,
  }) {
  const { userConfig, userLoading, updateUserConfig, museProfile } = useConfig();
  const { adminConfig, adminLoading } = useFeatures();
  const [editMode, setEditMode] = useState(true);
  const [saving, setSaving] = useState({});
  const [error, setError] = useState({});
  const [saved, setSaved] = useState({});
  const [localConfig, setLocalConfig] = useState(userConfig || {});
  const [hasPendingChanges, setHasPendingChanges] = useState({});
  const museName = museProfile?.name?.[0]?.content ?? "Muse";
  const userName = userConfig?.user_config?.USER_NAME ?? "User";

  const {
    speak,
    setIsTTSPlaying,
    isTTSPlaying,
    Equalizer,
    speakingMessageId,
  } = audioControls;

  const isThisPlaying =
    isTTSPlaying && speakingMessageId?.startsWith("tts-test-");

  useEffect(() => {
    if (userConfig) {
      setLocalConfig(userConfig);
      setHasPendingChanges({}); // reset all dirty flags when server truth changes
    }
  }, [userConfig]);

  const configsDiffer = (a, b) =>
    JSON.stringify(a || {}) !== JSON.stringify(b || {});

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

  const handleFieldChange = (section, key, value) => {
    setLocalConfig(prev => {
      const prevSection = prev[section] || {};
      const nextSection = { ...prevSection, [key]: value };
      const next = { ...prev, [section]: nextSection };

      setHasPendingChanges(h => ({
        ...h,
        [section]: configsDiffer(
          nextSection,
          (userConfig?.[section] || {})
        ),
      }));

      return next;
    });
  };

  const handleSaveSection = async section => {
    const updatedSection = localConfig[section] || {};

    // optional extra guard
    if (
      !configsDiffer(
        updatedSection,
        userConfig?.[section] || {}
      )
    ) {
      return;
    }

    // HERE: reuse your existing logic
    await handleSectionUpdate(section, updatedSection);
  };

  if (userLoading || !userConfig) {
    return (
      <div className="p-6 text-neutral-400 bg-neutral-950 h-full">
        Loading settings…
      </div>
    );
  }

  function FieldLabelWithInfo({ meta, fallbackLabel }) {
    const label = meta?.label || fallbackLabel;
    const description = meta?.description;

    return (
      <label className="block text-xs text-neutral-400 mb-1">
        <span className="inline-flex items-center gap-1">
          {label}

          {description && (
            <Popover>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  className="inline-flex h-3.5 w-3.5 items-center justify-center
                             text-neutral-500 hover:text-neutral-300"
                  aria-label={`${label} info`}
                >
                  <Info className="h-3 w-3" />
                </button>
              </PopoverTrigger>
              <PopoverContent
                side="top"
                align="start"
                className="max-w-xs text-xs bg-neutral-900 text-neutral-100 border border-neutral-700 shadow-lg"
              >
                {description}
              </PopoverContent>
            </Popover>
          )}
        </span>
      </label>
    );
  }

  const profile = userConfig.user_config || {};
  const llm = userConfig.llm_config || {};
  const tts = userConfig.tts_config || {};
  const museConfig = userConfig.muse_config || {};
  const features = userConfig.muse_features || {};
  const social = userConfig.social_config || {};
  const admin = adminConfig.mm_features || {};

  return (

    <Accordion type="multiple" className="space-y-2">
      <AccordionItem value="you-loc">
        <AccordionTrigger className="text-xs font-medium">
          You Identity and Location
        </AccordionTrigger>
        <AccordionContent className="space-y-2 pt-1">
          {/* display name, location, timezone, etc. */}
          <UserProfileSection
            FieldLabelWithInfo={FieldLabelWithInfo}
            profile={localConfig.user_config || {}}
            editMode={editMode}
            saving={saving.user_config}
            saved={saved.user_config}
            error={error.user_config}
            hasPendingChanges={!!hasPendingChanges.user_config}
            onFieldChange={(key, value) =>
              handleFieldChange("user_config", key, value)
            }
            onSaveSection={() => handleSaveSection("user_config")}
          />
        </AccordionContent>
      </AccordionItem>
      <AccordionItem value="llm-config">
        <AccordionTrigger className="text-xs font-medium">
          LLM Configuration
        </AccordionTrigger>
        <AccordionContent className="space-y-2 pt-1">
          <LLMSection
            FieldLabelWithInfo={FieldLabelWithInfo}
            llm={localConfig.llm_config || {}}
            editMode={editMode}
            saving={saving.llm_config}
            saved={saved.llm_config}
            error={error.llm_config}
            hasPendingChanges={!!hasPendingChanges.llm_config}
            onFieldChange={(key, value) =>
              handleFieldChange("llm_config", key, value)
            }
            onSaveSection={() => handleSaveSection("llm_config")}
          />
        </AccordionContent>
      </AccordionItem>
      {admin.ENABLE_TTS && (
      <AccordionItem value="voice-config">
        <AccordionTrigger className="text-xs font-medium">
          Voice configuration
        </AccordionTrigger>
        <AccordionContent className="space-y-2 pt-1">
          <TTSSection
            FieldLabelWithInfo={FieldLabelWithInfo}
            tts={localConfig.tts_config || {}}
            editMode={editMode}
            saving={saving.tts_config}
            saved={saved.tts_config}
            error={error.tts_config}
            hasPendingChanges={!!hasPendingChanges.tts_config}
            onFieldChange={(key, value) =>
              handleFieldChange("tts_config", key, value)
            }
            onSaveSection={() => handleSaveSection("tts_config")}
            museName={museName}
            userName={userName}
            speak={speak}
            setIsTTSPlaying={setIsTTSPlaying}
            isThisPlaying={isThisPlaying}
            Equalizer={Equalizer}
            speakingMessageId={speakingMessageId}
          />
        </AccordionContent>
      </AccordionItem>
      )}
      {admin.ENABLE_PUBLIC_INTERFACES && (
      <AccordionItem value="social-config">
        <AccordionTrigger className="text-xs font-medium">
          Social Setup
        </AccordionTrigger>
        <AccordionContent className="space-y-2 pt-1">
          <SocialSection
            FieldLabelWithInfo={FieldLabelWithInfo}
            social={localConfig.social_config || {}}
            editMode={editMode}
            saving={saving.social_config}
            saved={saved.social_config}
            error={error.social_config}
            hasPendingChanges={!!hasPendingChanges.social_config}
            onFieldChange={(key, value) =>
              handleFieldChange("social_config", key, value)
            }
            onSaveSection={() => handleSaveSection("social_config")}
          />
        </AccordionContent>
      </AccordionItem>
      )}
      <AccordionItem value="feature-config">
        <AccordionTrigger className="text-xs font-medium">
          Muse Awareness and Abilities
        </AccordionTrigger>
        <AccordionContent className="space-y-2 pt-1">
          <MuseFeatures
            FieldLabelWithInfo={FieldLabelWithInfo}
            features={localConfig.muse_features || {}}
            editMode={editMode}
            saving={saving.muse_features}
            saved={saved.muse_features}
            error={error.muse_features}
            hasPendingChanges={!!hasPendingChanges.muse_features}
            onFieldChange={(key, value) =>
              handleFieldChange("muse_features", key, value)
            }
            onSaveSection={() => handleSaveSection("muse_features")}
          />
        </AccordionContent>
      </AccordionItem>

      {/* Voice & Audio, Connections, Site Features, AI & API... */}
    </Accordion>
  );
}