"use client";
import { useRef, useState, useEffect } from "react";
import { useConfig } from '@/hooks/ConfigContext';

export default function MotdBar({}) {
  const { museProfile, uiStates, uiPollstates } = useConfig();
  const { states, muse_profile, muse_config } = uiPollstates || {};
  const motd = states?.motd?.text ?? "";
  const museName = museProfile?.name?.[0]?.content ?? "Muse";

  if (!motd) return null;

  return (
    <div className="mt-1 w-full px-3 py-2 bg-black/80 rounded-b-xl">
      <p className="text-sm italic text-purple-200 text-center wrap">
        {motd}
      </p>
    </div>
  );
}