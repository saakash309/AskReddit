"""Text-to-speech voiceover generation using edge-tts (free, no API key)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts
from moviepy import AudioFileClip


async def _synthesize_async(text: str, voice: str, rate: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await communicate.save(str(out_path))


def synthesize(text: str, voice: str, rate: str, out_path: Path) -> Path:
    """Render `text` to speech at `out_path` (mp3) and return the path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synthesize_async(text, voice, rate, out_path))
    return out_path


def audio_duration(path: Path) -> float:
    with AudioFileClip(str(path)) as clip:
        return clip.duration
