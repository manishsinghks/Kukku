"use client";
import { useCallback, useEffect, useRef, useState } from "react";

// Browser text-to-speech via the free Web Speech API (speechSynthesis).
// The mirror of useSpeech: Kukku reads replies aloud, all in the browser —
// nothing hits the backend. Chrome/Edge/Safari all support it.

// Strip markdown so the voice doesn't read "asterisk asterisk" etc.
function clean(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, " code block ") // fenced code
    .replace(/`([^`]+)`/g, "$1") // inline code
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "") // images
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1") // links → text
    .replace(/[*_~#>]+/g, "") // md punctuation
    .replace(/^\s*[-•]\s+/gm, "") // bullets
    .replace(/\s+/g, " ")
    .trim();
}

export function useTTS(lang: string) {
  const [supported, setSupported] = useState(false);
  const [speakingId, setSpeakingId] = useState<number | null>(null);
  const langRef = useRef(lang);
  langRef.current = lang;

  useEffect(() => {
    setSupported(typeof window !== "undefined" && "speechSynthesis" in window);
  }, []);

  const cancel = useCallback(() => {
    try {
      window.speechSynthesis.cancel();
    } catch {
      /* ignore */
    }
    setSpeakingId(null);
  }, []);

  // Pick a voice that matches the requested language, falling back gracefully.
  const pickVoice = useCallback((code: string): SpeechSynthesisVoice | null => {
    const voices = window.speechSynthesis.getVoices();
    if (!voices.length) return null;
    const base = code.split("-")[0];
    return (
      voices.find((v) => v.lang === code) ||
      voices.find((v) => v.lang.startsWith(base)) ||
      voices.find((v) => v.lang.startsWith("en")) ||
      voices[0]
    );
  }, []);

  const speak = useCallback(
    (id: number, text: string) => {
      if (!("speechSynthesis" in window)) return;
      const body = clean(text);
      if (!body) return;
      window.speechSynthesis.cancel(); // stop anything already playing
      const u = new SpeechSynthesisUtterance(body);
      u.lang = langRef.current;
      const v = pickVoice(langRef.current);
      if (v) u.voice = v;
      u.rate = 1.02;
      u.pitch = 1;
      u.onend = () => setSpeakingId((cur) => (cur === id ? null : cur));
      u.onerror = () => setSpeakingId((cur) => (cur === id ? null : cur));
      setSpeakingId(id);
      window.speechSynthesis.speak(u);
    },
    [pickVoice],
  );

  const toggle = useCallback(
    (id: number, text: string) => {
      if (speakingId === id) cancel();
      else speak(id, text);
    },
    [speakingId, cancel, speak],
  );

  // voices load async in some browsers — warm them up
  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const warm = () => window.speechSynthesis.getVoices();
    warm();
    window.speechSynthesis.onvoiceschanged = warm;
    return () => cancel();
  }, [cancel]);

  return { supported, speakingId, speak, cancel, toggle };
}
