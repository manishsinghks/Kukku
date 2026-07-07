"""Voice note transcription with faster-whisper (lazy-loaded, optional)."""
from __future__ import annotations

import threading
from pathlib import Path

from app.utils.logging import get_logger

log = get_logger(__name__)


class Transcriber:
    def __init__(self, model_name: str = "base"):
        self._model_name = model_name
        self._model = None
        self._lock = threading.Lock()
        self._unavailable: str | None = None

    def _ensure(self) -> bool:
        if self._model is not None:
            return True
        if self._unavailable:
            return False
        with self._lock:
            if self._model is not None:
                return True
            try:
                from faster_whisper import WhisperModel

                log.info("Loading whisper model '%s' ...", self._model_name)
                self._model = WhisperModel(self._model_name, device="cpu", compute_type="int8")
                return True
            except Exception as e:  # noqa: BLE001
                self._unavailable = f"{type(e).__name__}: {e}"
                log.warning("Transcription unavailable: %s", self._unavailable)
                return False

    def transcribe(self, audio_path: Path) -> str:
        """Blocking — call from a thread executor. Raises RuntimeError if unavailable.

        Language is auto-detected (English, Hindi, Hinglish all work); vad_filter
        trims silence for cleaner results on short voice notes.
        """
        if not self._ensure():
            raise RuntimeError(f"voice transcription unavailable ({self._unavailable})")
        segments, _info = self._model.transcribe(
            str(audio_path), beam_size=5, vad_filter=True
        )
        return " ".join(s.text.strip() for s in segments).strip()
