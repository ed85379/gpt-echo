"use client";
import { useRef, useState, useEffect } from "react";
import { useConfig } from '@/hooks/ConfigContext';

export default function MotdBar({}) {
  const { museProfile, uiStates, uiPollstates } = useConfig();
  const { states, muse_profile, muse_config } = uiPollstates || {};
const motd = states?.pollstates?.motd?.text ?? "";
const museName =
  muse_profile?.find((s) => s.section === "name")?.content ?? "Muse";

  if (!motd) return null;

  return (
    <div className="mt-1 w-full px-3 py-2 bg-black/80 rounded-b-xl">
      <p className="text-sm italic text-purple-200 text-center wrap">
        {motd} - {museName}
      </p>
    </div>
  );
}