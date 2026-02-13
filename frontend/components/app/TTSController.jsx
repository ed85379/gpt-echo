import React, { useState } from "react";
import { CirclePlay, CirclePause } from "lucide-react";
import { useFeatures } from '@/hooks/FeaturesContext';

export default function TTSController({
    audioControls,
    msg,
    effectiveRole,
    connecting,
  }) {

  const { adminConfig, adminLoading } = useFeatures();
  if (adminLoading) return null;
  const mm = adminConfig?.mm_features || {};
  const enableTTS = !!mm.ENABLE_TTS;

  const {
    audioSourceRef,
    audioCtxRef,
    isTTSPlaying,
    setIsTTSPlaying,
    speak,
    setSpeaking,
    Equalizer,
    speakingMessageId,
  } = audioControls;

  const isThisPlaying =
    isTTSPlaying && speakingMessageId === msg.message_id;

  return (
    <>
    {enableTTS && (
    <div
      className={`
        absolute bottom-2 left-3 flex items-center gap-2 z-30
        ${isThisPlaying ? "" : "hidden group-hover:flex"}
      `}
    >
      {effectiveRole === "muse" && (
        <button
          onClick={() => {
            if (isThisPlaying) {
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
              setIsTTSPlaying(false);
              setSpeaking(false);
              // setSpeakingMessageId(null); // if you’re not already doing this in speak()
            } else if (msg && !connecting) {
              speak(msg, () => {
                setIsTTSPlaying(false);
                // setSpeakingMessageId(null);
              });
            }
          }}
          title={
            isThisPlaying ? "Stop Playing Audio" : "Start Playing Audio"
          }
          className="text-sm text-purple-300 hover:underline disabled:opacity-50"
          disabled={connecting || !msg}
        >
          {isThisPlaying ? (
            <CirclePause
              size={18}
              className="transition-colors text-purple-400 hover:text-purple-300"
            />
          ) : (
            <CirclePlay
              size={18}
              className={`transition-colors ${
                isTTSPlaying ? "text-purple-400" : "text-neutral-400"
              } hover:text-purple-300`}
            />
          )}
        </button>
      )}

      <Equalizer isActive={isThisPlaying} />
    </div>
    )}
  </>
  );
}