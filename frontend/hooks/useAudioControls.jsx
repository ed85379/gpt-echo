// hooks/useAudioControls.js
import { useState, useRef, useEffect, useCallback } from "react";

export function useAudioControls() {
  const [speaking, setSpeaking] = useState(false);
  const audioCtxRef = useRef(null);
  const audioSourceRef = useRef(null);
  const [isTTSPlaying, setIsTTSPlaying] = useState(false);
  const [speakingMessageId, setSpeakingMessageId] = useState(null);
  const [autoTTS, setAutoTTS] = useState(false);
  const autoTTSRef = useRef(autoTTS);
  const audioResponseRef = useRef(null);

  useEffect(() => {
    autoTTSRef.current = autoTTS;
  }, [autoTTS]);

  const playPing = useCallback(() => {
    const audio = new window.Audio("/ping.mp3");
    audio.play();
  }, []);

  const speak = useCallback(
    async (msg, onDone) => {
      const text = msg.text;

      setSpeaking(true);
      setSpeakingMessageId(msg.message_id);
      setIsTTSPlaying(true);

      if (audioSourceRef.current) {
        try {
          audioSourceRef.current.stop();
        } catch (e) {}
        audioSourceRef.current = null;
      }
      if (audioCtxRef.current) {
        try {
          audioCtxRef.current.close();
        } catch (e) {}
        audioCtxRef.current = null;
      }

      let cancelled = false;

      try {
        const response = await fetch("/api/tts/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });

        if (!response.ok) throw new Error("TTS request failed");

        const reader = response.body.getReader();
        const audioCtx = new window.AudioContext();
        audioCtxRef.current = audioCtx;

        const source = audioCtx.createBufferSource();
        audioSourceRef.current = source;

        const chunks = [];
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          chunks.push(...value);
        }

        if (cancelled) return;

        const buffer = new Uint8Array(chunks).buffer;
        const thisCtx = audioCtx;
        const thisSource = source;

        audioCtx.decodeAudioData(buffer, (decoded) => {
          if (audioCtxRef.current !== thisCtx) return;
          if (!decoded) return;

          thisSource.buffer = decoded;
          thisSource.connect(thisCtx.destination);
          thisSource.start(0);

          thisSource.onended = () => {
            if (audioSourceRef.current === thisSource) {
              audioSourceRef.current = null;
            }
            if (audioCtxRef.current === thisCtx) {
              audioCtxRef.current = null;
            }
            setSpeaking(false);
            setIsTTSPlaying(false);
            if (onDone) onDone();
          };
        });
      } catch (err) {
        if (!cancelled) {
          setSpeaking(false);
          setIsTTSPlaying(false);
          if (onDone) onDone();
        }
      }

      return () => {
        cancelled = true;
      };
    },
    []
  );

  useEffect(() => {
    audioResponseRef.current = (incoming) => {
      if (autoTTSRef.current) {
        speak(incoming, () => setIsTTSPlaying(false));
      } else {
        playPing();
      }
    };
  }, [speak, playPing]);

  function Equalizer({ isActive }) {
    if (!isActive) return null;
    return (
      <span className="ml-1 equalizer">
        <span className="equalizer-bar" />
        <span className="equalizer-bar" />
        <span className="equalizer-bar" />
      </span>
    );
  }

  return {
    speaking,
    setSpeaking,
    speak,
    isTTSPlaying,
    setIsTTSPlaying,
    audioSourceRef,
    audioCtxRef,
    Equalizer,
    speakingMessageId,
    setSpeakingMessageId,
    autoTTS,
    setAutoTTS,
    audioResponseRef,
  };
}