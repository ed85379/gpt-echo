// Muse info panel to sit beside ChatTab (import and render in page.tsx)
"use client";

import { useEffect, useState } from "react";
import { useConfig } from '../hooks/ConfigContext';

const MusePanel = ({ speaking }) => {
  const { museProfile, museProfileLoading } = useConfig();
  const museName = museProfile?.name?.[0]?.content ?? "Muse";
  const panelIntro = museProfile?.panel_intro?.[0]?.content;

  const avatarName = museName?.toLowerCase() || "muse";
  const intro = panelIntro || "This presence was designed to remember — not command.";

  return (
    <div className="bg-neutral-900 p-4 rounded-xl space-y-4 w-full md:max-w-sm sticky top-6 self-start">
      <img
        src={`/${avatarName}-new.jpg`}
        alt={museName}
            className={`rounded-xl w-full border-2 border-purple-700 ${
              speaking ? "animate-pulse-border" : ""
            }`}
      />
      <div className="text-2xl font-semibold text-purple-300 text-center">
        {museName || "Muse"}
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
