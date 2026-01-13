"use client";
import { useRef, useState, useEffect } from "react";
import { useConfig } from '@/hooks/ConfigContext';

export default function MotdBar({}) {
  const { museProfile, uiStates } = useConfig();
  const museName = museProfile?.name?.[0]?.content ?? "Muse";
  const motd = uiStates?.motd?.text ?? "";
  if (!motd) return null;

  return (
    <div className="mt-1 w-full px-3 py-2 bg-black/80 rounded-b-xl">
      <p className="text-sm italic text-purple-200 text-center wrap">
        {motd} - {museName}
      </p>
    </div>
  );
}