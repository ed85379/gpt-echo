"use client";

import { useState } from "react";
import ChatTab from "./components/ChatTab";
import MusePanel from "./components/MusePanel";
import MemoryTab from "./components/MemoryTab";
import SyncTab from "./components/SyncTab";

import Image from 'next/image';
<Image
  src="/memorymuse-logo.png"
  alt="MemoryMuse Logo"
  width={79}
  height={52}
  className="inline-block mr-3 align-middle"
/>

const MuseApp = () => {
  const [tab, setTab] = useState("chat");
  const [speaking, setSpeaking] = useState(false);

  return (
    <div className="h-screen flex flex-col bg-neutral-950 text-white">
      {/* Fixed Header */}
      <div className="border-b border-neutral-800 p-4 flex justify-between items-center sticky top-0 z-10 bg-neutral-950">
        <div className="flex items-center">
          <img src="/memorymuse-logo.png" alt="MemoryMuse Logo" className="h-15 w-20 mr-3" />
          <span className="text-2xl font-black tracking-wide text-purple-200 drop-shadow">
            Memory<span className="text-purple-400">Muse</span>
          </span>
        </div>
        <div className="space-x-3 text-sm">
          {["chat", "journal", "memory", "sync", "profile", "you", "settings", "status"].map((t) => (
            <button
              key={t}
              className={`px-3 py-1 rounded ${
                tab === t ? "bg-purple-700" : "hover:bg-neutral-800"
              }`}
              onClick={() => setTab(t)}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Main content below header */}
      <div className="flex-1 overflow-hidden">
        {tab === "chat" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-full px-6">
            <div className="md:col-span-2 overflow-y-auto max-h-[calc(100vh-80px)] bg-neutral-950 text-purple-100 rounded-xl p-4 border border-neutral-800">
              <ChatTab setSpeaking={setSpeaking} />
            </div>
            <div className="hidden md:block sticky top-0 self-start h-fit">
              <MusePanel speaking={speaking} />
            </div>
          </div>
        )}
        {tab === "journal" && <div className="p-6">[ Journal goes here ]</div>}
        {tab === "memory" && <MemoryTab />}
        {tab === "sync" && (
          <div className="p-6 h-full overflow-y-auto">
            <SyncTab />
          </div>
        )}
        {tab === "profile" && <div className="p-6">[ Muse profile ]</div>}
        {tab === "you" && <div className="p-6">[ User profile ]</div>}
        {tab === "settings" && <div className="p-6">[ Settings go here ]</div>}
        {tab === "status" && <div className="p-6">[ System status ]</div>}
      </div>
    </div>
  );
};

export default MuseApp;
