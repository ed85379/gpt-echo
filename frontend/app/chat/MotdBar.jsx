"use client";
import { useRef, useEffect } from "react";
import { useConfig } from "@/hooks/ConfigContext";

export default function MotdBar({ motd }) {
  const { museProfile } = useConfig();
  const museName = museProfile?.name?.[0]?.content ?? "Muse";

  const motdRef = useRef(null);

useEffect(() => {
  if (!motd || !motdRef.current) return;

  const container = motdRef.current;
  container.innerHTML = "";

  const words = motd.split(" ");
  let letterIndex = 0;
  const spans = [];

  words.forEach((word, wIdx) => {
    // wrapper for each word so the browser can wrap at word boundaries
    const wordSpan = document.createElement("span");
    wordSpan.style.display = "inline-block"; // keeps letters together as a word
    container.appendChild(wordSpan);

    // letters inside the word
    for (let i = 0; i < word.length; i++) {
      const span = document.createElement("span");
      span.textContent = word[i];
      span.classList.add("motd-letter");
      wordSpan.appendChild(span);

      setTimeout(() => {
        span.classList.add("visible");
      }, letterIndex * 25);

      spans.push(span);
      letterIndex++;
    }

    // add a space after each word except the last
    if (wIdx < words.length - 1) {
      const space = document.createElement("span");
      space.textContent = "\u00A0"; // non‑breaking space so words don't split
      container.appendChild(space);
      letterIndex++; // still count it for timing, keeps rhythm even
    }
  });

  return () => {
    spans.forEach((span) => span.classList.remove("visible"));
  };
}, [motd]);

  if (!motd) return null;

  return (
    <div className="mt-1 w-full px-3 py-2 bg-black/80 rounded-b-xl overflow-hidden">
      <p
        ref={motdRef}
        aria-label={motd}
        className="
          text-sm italic text-purple-200
          flex flex-wrap justify-start
          leading-snug
        "
      />
    </div>
  );
}