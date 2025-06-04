"use client";
import { useState } from "react";
import ChatTab from './ChatTab';
import MusePanel from './MusePanel';
import HistoryTab from './HistoryTab';
import { useConfig } from '../hooks/ConfigContext';

const TABS = [
  { key: "chat", label: "Chat" },      // Or "Current"
  { key: "history", label: "History" } // Or "Search"
];

export default function ChatPage() {
  const [activeTab, setActiveTab] = useState("chat");
  const [speaking, setSpeaking] = useState(false);

  return (
    <div className="flex flex-col h-full w-full">
      {/* Sub-tab selector */}
      <div className="flex gap-2 border-b border-neutral-800 px-6">
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            title={tab.key === "history" ? "View, search, and filter conversation logs" : ""}
            className={`px-4 py-2 rounded-t-lg border-b-2 transition-all
              ${activeTab === tab.key
                ? 'border-purple-400 text-purple-200 font-bold bg-neutral-900'
                : 'border-transparent text-purple-400 hover:bg-neutral-900/50'
              }`
            }
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sub-tab content */}
      {activeTab === "chat" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-full px-6">
<div className="md:col-span-2 overflow-y-auto"
     style={{ maxHeight: "calc(100vh - 92px - 48px)" }}  // Adjust 92/48 as needed for your actual bar heights
>
            <ChatTab setSpeaking={setSpeaking} speaking={speaking} />
          </div>
          <div className="hidden md:block sticky top-0 self-start h-fit">
            <MusePanel setSpeaking={setSpeaking} speaking={speaking} />
          </div>
        </div>
      )}

      {activeTab === "history" && (
        <div className="flex-1 px-6">
          <HistoryTab />
        </div>
      )}
    </div>
  );
}