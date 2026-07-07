"use client";
import { useCallback, useEffect, useRef, useState } from "react";

// Browser speech-to-text via the free Web Speech API (Chrome/Edge/Safari).
// Transcribes locally in the browser — nothing hits the backend until you send.
export function useSpeech(lang: string, onText: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(false);
  const recRef = useRef<any>(null);
  const baseRef = useRef("");

  useEffect(() => {
    const SR =
      typeof window !== "undefined" &&
      ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
    setSupported(!!SR);
  }, []);

  const stop = useCallback(() => {
    try {
      recRef.current?.stop();
    } catch {
      /* ignore */
    }
    setListening(false);
  }, []);

  const start = useCallback(
    (base: string) => {
      const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SR) return;
      const rec = new SR();
      rec.lang = lang;
      rec.continuous = true;
      rec.interimResults = true;
      baseRef.current = base.trim() ? base.trim() + " " : "";
      rec.onresult = (e: any) => {
        let txt = "";
        for (let i = 0; i < e.results.length; i++) txt += e.results[i][0].transcript;
        onText(baseRef.current + txt);
      };
      rec.onend = () => setListening(false);
      rec.onerror = () => setListening(false);
      recRef.current = rec;
      try {
        rec.start();
        setListening(true);
      } catch {
        setListening(false);
      }
    },
    [lang, onText],
  );

  // cleanup on unmount
  useEffect(() => () => stop(), [stop]);

  return { listening, supported, start, stop };
}
