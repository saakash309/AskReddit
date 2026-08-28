"""Assembles the final vertical short: background video + timed card overlays + narration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    afx,
    vfx,
)

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
FPS = 30
LEAD_IN = 0.35  # seconds of background before the first card appears


@dataclass
class Segment:
    image_path: Path
    audio_path: Path
    duration: float  # on-screen time in seconds (narration length + padding)


def _fit_background(clip: VideoFileClip, duration: float) -> VideoFileClip:
    """Scale-to-cover + center-crop the background to 1080x1920, looped/trimmed to `duration`."""
    scale = max(TARGET_WIDTH / clip.w, TARGET_HEIGHT / clip.h)
    resized = clip.resized(scale)
    cropped = resized.with_effects(
        [
            vfx.Crop(
                x_center=resized.w / 2,
                y_center=resized.h / 2,
                width=TARGET_WIDTH,
                height=TARGET_HEIGHT,
            )
        ]
    )
    if cropped.duration < duration:
        cropped = cropped.with_effects([vfx.Loop(duration=duration)])
    else:
        cropped = cropped.subclipped(0, duration)
    return cropped.without_audio()


def build_video(
    background_path: Path,
    segments: List[Segment],
    output_path: Path,
    music_path: Optional[Path] = None,
    music_volume: float = 0.08,
) -> Path:
    if not segments:
        raise ValueError("No segments to render")

    starts: List[float] = []
    t = LEAD_IN
    for seg in segments:
        starts.append(t)
        t += seg.duration
    total_duration = t + LEAD_IN

    open_clips = []
    try:
        background_raw = VideoFileClip(str(background_path))
        open_clips.append(background_raw)
        background = _fit_background(background_raw, total_duration)

        image_clips = []
        audio_clips = []
        for seg, start in zip(segments, starts):
            img_clip = (
                ImageClip(str(seg.image_path))
                .with_duration(seg.duration)
                .with_start(start)
                .with_position(("center", "center"))
            )
            image_clips.append(img_clip)

            audio_clip = AudioFileClip(str(seg.audio_path)).with_start(start)
            open_clips.append(audio_clip)
            audio_clips.append(audio_clip)

        if music_path is not None:
            music_raw = AudioFileClip(str(music_path))
            open_clips.append(music_raw)
            music = music_raw.with_effects(
                [afx.AudioLoop(duration=total_duration), afx.MultiplyVolume(music_volume)]
            )
            audio_clips.insert(0, music)

        composite_audio = CompositeAudioClip(audio_clips).with_duration(total_duration)

        final = (
            CompositeVideoClip([background, *image_clips], size=(TARGET_WIDTH, TARGET_HEIGHT))
            .with_duration(total_duration)
            .with_audio(composite_audio)
            .with_fps(FPS)
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="medium",
            logger=None,
        )
        final.close()
    finally:
        for clip in open_clips:
            try:
                clip.close()
            except Exception:
                pass

    return output_path
