"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useConfig } from '@/hooks/ConfigContext';

export default function MainTabBar() {
  const pathname = usePathname();

const { config, loading } = useConfig();
// Flatten config to: { GAMES_ENABLED: true/false, ... }
const flagValues = {};
for (const key in config) {
  if (config[key] && typeof config[key].value === "boolean") {
    flagValues[key] = config[key].value;
  }
}


if (loading) return null; // or a spinner, or a skeleton bar

const allTabs = [
  { name: "Chat", path: "/chat" },
  { name: "Projects", path: "/projects", feature: "PROJECTS_ENABLED" },
  { name: "Reminders", path: "/reminders" },
  { name: "Journal", path: "/journal" },
  { name: "Memory", path: "/memory" },
  { name: "Muse", path: "/muse" },
  { name: "Games", path: "/games", feature: "GAMES_ENABLED" },
  { name: "Sync", path: "/sync", feature: "SYNC_ENABLED"  },
  { name: "Config", path: "/config" },
];

// Now filter tabs using the flat object:
const visibleTabs = allTabs.filter(
  tab => !tab.feature || flagValues[tab.feature]
);

  return (
    <div className="border-b border-neutral-800 p-4 flex justify-between items-center sticky top-0 z-10 bg-neutral-950">
      <div className="flex items-center">
        <img src="/memorymuse-logo.png" alt="MemoryMuse Logo" className="h-15 w-20 mr-3" />
        <span className="text-2xl font-black tracking-wide text-purple-200 drop-shadow">
          Memory<span className="text-purple-400">Muse</span>
        </span>
      </div>
        <div className="space-x-3 text-sm">
          {visibleTabs.map((tab) => (
            <Link href={tab.path} key={tab.name}>
              <button
                className={`px-3 py-1 rounded ${
                  pathname.startsWith(tab.path) ? "bg-purple-700" : "hover:bg-neutral-800"
                }`}
              >
                {tab.name}
              </button>
            </Link>
          ))}
        </div>
    </div>
  );
}
