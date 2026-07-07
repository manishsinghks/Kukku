import json
from pathlib import Path

import pytest

from app.search import extractors
from app.search.extractors import (
    ExtractionError,
    _find_tesseract,
    _ocr_langs,
    chunk_text,
    classify,
    extract_text,
)


def test_ocr_langs_includes_hindi_when_available(monkeypatch):
    extractors._ocr_langs_cache = None
    import subprocess as sp

    def fake_run(*a, **k):
        return sp.CompletedProcess(a, 0, stdout="List of langs (3):\neng\nhin\nosd\n", stderr="")

    monkeypatch.setattr(sp, "run", fake_run)
    assert _ocr_langs("/usr/bin/tesseract") == "eng+hin"
    extractors._ocr_langs_cache = None


def test_ocr_langs_english_only_when_no_hindi(monkeypatch):
    extractors._ocr_langs_cache = None
    import subprocess as sp

    monkeypatch.setattr(
        sp, "run",
        lambda *a, **k: sp.CompletedProcess(a, 0, stdout="eng\nosd\n", stderr=""),
    )
    assert _ocr_langs("/usr/bin/tesseract") == "eng"
    extractors._ocr_langs_cache = None


def _system_font():
    """Return a readable TrueType font, or None if none is available."""
    from PIL import ImageFont

    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, 28)
    return None


@pytest.mark.skipif(_find_tesseract() is None, reason="tesseract not installed")
def test_ocr_extracts_screenshot_text(tmp_path):
    from PIL import Image, ImageDraw

    font = _system_font()
    if font is None:
        pytest.skip("no TrueType font available for a fair OCR test")
    img = Image.new("RGB", (1000, 160), "white")
    draw = ImageDraw.Draw(img)
    draw.text((40, 40), "Cannot connect to the Docker daemon", fill="black", font=font)
    shot = tmp_path / "screenshot.png"
    img.save(shot)

    text = extract_text(shot)
    assert "Docker" in text and "daemon" in text.lower()


def test_classify():
    assert classify(Path("a.py")) == "code"
    assert classify(Path("a.png")) == "image"
    assert classify(Path("a.pdf")) == "document"
    assert classify(Path("a.xlsx")) == "data"


def test_extract_plain_text(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("# Title\nhello world")
    assert "hello world" in extract_text(f)


def test_extract_json_as_code(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(json.dumps({"key": "special-value"}))
    assert "special-value" in extract_text(f)


def test_extract_unsupported_raises(tmp_path):
    f = tmp_path / "movie.mp4"
    f.write_bytes(b"\x00\x01")
    with pytest.raises(ExtractionError):
        extract_text(f)


def test_extract_image_without_ocr_raises(tmp_path):
    f = tmp_path / "shot.png"
    f.write_bytes(b"\x89PNG\r\n")
    with pytest.raises(ExtractionError):
        extract_text(f, ocr_enabled=False)


def test_extract_respects_max_chars(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("x" * 500)
    assert len(extract_text(f, max_chars=100)) == 100


def test_chunk_text_short_is_single_chunk():
    assert chunk_text("hello") == ["hello"]
    assert chunk_text("   ") == []


def test_chunk_text_overlap_and_coverage():
    text = "\n".join(f"paragraph {i} " + "words " * 30 for i in range(30))
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert all(len(c) <= 500 for c in chunks)
    assert len(chunks) > 3
    # last paragraph must be represented
    assert "paragraph 29" in chunks[-1]


def test_supported_exts_sane():
    assert ".pdf" in extractors.SUPPORTED_EXTS
    assert ".py" in extractors.SUPPORTED_EXTS
    assert ".exe" not in extractors.SUPPORTED_EXTS
