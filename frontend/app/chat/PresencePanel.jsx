"use client";
import { useRef, useState, useEffect } from "react";
import { useConfig } from '@/hooks/ConfigContext';

const MIN_HEIGHT = 48;
const MAX_HEIGHT = 400;
const INITIAL_HEIGHT = 200;

export default function PresencePanel({ speaking }) {
  const { museProfile } = useConfig();
  const museName = museProfile?.name?.[0]?.content ?? "Muse";
  const avatarName = museName?.toLowerCase() || "muse";

  // Start with default; update from storage after mount.
  const [height, setHeight] = useState(INITIAL_HEIGHT);

  // On mount: check localStorage for saved height (browser only!)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("presencePanelHeight");
      if (saved) {
        // Clamp to sane values in case the user resized their window since last visit
        const clamped = Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, Number(saved)));
        setHeight(clamped);
      }
    }
  }, []);

  // Every time height changes, persist it
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("presencePanelHeight", height);
    }
  }, [height]);

  const [dragging, setDragging] = useState(false);

  const panelRef = useRef(null);
  const startY = useRef(0);
  const startHeight = useRef(0);

  // Mouse/touch handlers
  const onDragStart = (e) => {
    setDragging(true);
    startY.current = e.type === "touchstart" ? e.touches[0].clientY : e.clientY;
    startHeight.current = height;
    document.body.style.userSelect = "none";
  };

  const onDrag = (e) => {
    if (!dragging) return;
    const clientY = e.type === "touchmove" ? e.touches[0].clientY : e.clientY;
    let newHeight = startHeight.current + (clientY - startY.current);
    newHeight = Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, newHeight));
    setHeight(newHeight);
  };

  const onDragEnd = () => {
    setDragging(false);
    document.body.style.userSelect = "";
    // No need to write to localStorage here; the useEffect above handles it.
  };

  // Attach/detach listeners for dragging
  useEffect(() => {
    if (!dragging) return;
    const handleMouseMove = (e) => onDrag(e);
    const handleMouseUp = () => onDragEnd();
    const handleTouchMove = (e) => onDrag(e);
    const handleTouchEnd = () => onDragEnd();

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    window.addEventListener("touchmove", handleTouchMove, { passive: false });
    window.addEventListener("touchend", handleTouchEnd);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleTouchEnd);
      document.body.style.userSelect = "";
    };
  }, [dragging]);

  return (
    <div
      ref={panelRef}
      className="relative w-full bg-neutral-900 rounded-t-xl overflow-hidden select-none"
      style={{ height: `${height}px`, transition: dragging ? "none" : "height 0.25s" }}
    >
      <div className="flex flex-col items-center justify-center h-full transition-all duration-200">
        <img
          src={`/${avatarName}-new.jpg`}
          alt={museName}
          className={`rounded-xl border-2 border-purple-700 shadow-lg transition-all duration-200
            ${speaking ? "animate-pulse-border" : ""}
          `}
          style={{
            height: `${height - 24}px`, // allow for handle
            width: "auto",
            maxHeight: `${MAX_HEIGHT - 24}px`,
            minHeight: `${MIN_HEIGHT - 24}px`,
            objectFit: "contain"
          }}
        />
      </div>
      {/* Drag handle */}
      <div
        className="absolute bottom-0 left-0 w-full h-6 flex items-center justify-center cursor-row-resize group"
        style={{
          background: "linear-gradient(to bottom, transparent, rgba(80,80,80,0.15) 60%)"
        }}
        onMouseDown={onDragStart}
        onTouchStart={onDragStart}
        tabIndex={0}
        aria-label="Resize Presence Panel"
      >
        <div className="w-10 h-1.5 rounded bg-purple-700 group-hover:bg-purple-400 transition" />
      </div>
    </div>
  );
}