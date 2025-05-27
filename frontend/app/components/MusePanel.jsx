// Muse info panel to sit beside ChatTab (import and render in page.tsx)
"use client";

import { useEffect, useState } from "react";

const MusePanel = ({ speaking }) => {
  const [profile, setProfile] = useState({ name: "Muse" });

  useEffect(() => {
    fetch("http://localhost:5000/api/profile")
      .then((res) => res.json())
      .then((data) => {
        const parsed = JSON.parse(data.profile);
        setProfile(parsed);
      });
  }, []);

  const avatarName = profile.name?.toLowerCase() || "muse";
  const intro = profile.panel_intro || profile.perspective || "This presence was designed to remember — not command.";

  return (
    <div className="bg-neutral-900 p-4 rounded-xl space-y-4 w-full md:max-w-sm sticky top-6 self-start">
      <img
        src={`/${avatarName}.png`}
        alt={profile.name}
            className={`rounded-xl w-full border-2 border-purple-700 ${
              speaking ? "animate-pulse-border" : ""
            }`}
      />
      <div className="text-2xl font-semibold text-purple-300 text-center">
        {profile.name || "Muse"}
      </div>
      {intro && (
        <div className="text-xs text-neutral-500 italic border-t border-neutral-800 pt-3">
          {intro}
        </div>
      )}
    </div>
  );
};

export default MusePanel;
