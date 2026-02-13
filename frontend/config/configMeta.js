// /config/configMeta.js
export const SETTINGS_META = {
  user_config: {
    USER_NAME: {
      label: "Display Name",
      description: "What your muse can call you in the UI and in conversation.",
    },
    USER_TIMEZONE: {
      label: "Timezone",
      description: "Used for reminders and all time displays in the UI and in your muse's context.",
    },
  },
  model_config: {
    OPENAI_MODEL: {
      label: "Lightweight model",
      description: "Fast, cheap model for most conversations.",
      options: [
        { value: "gpt-4.1-mini", label: "gpt-4.1-mini (default)" },
        { value: "gpt-4.1", label: "gpt-4.1" },
        { value: "gpt-5-chat-latest", label: "gpt-5-chat-latest" },
      ],
    },
    OPENAI_FULL_MODEL: {
      label: "Heavy model",
      description: "Used for complex reasoning or long-form work.",
      options: [
        { value: "gpt-4.1", label: "gpt-4.1" },
        { value: "gpt-4.1-preview", label: "gpt-4.1-preview" },
      ],
    },
  },
  muse_features: {
    ENABLE_GCP: {
      label: "Global Consciousness Project",
      description: "Include GCP status in the [World / Now] block.",
    },
    // ...
  },
};