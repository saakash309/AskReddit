"""Sources a non-copyright vertical background video clip.

Priority:
1. If PEXELS_API_KEY is set, fetch a free-license portrait stock video from
   Pexels (https://www.pexels.com/api/) matching PEXELS_QUERY, cached locally.
2. Otherwise pick a random clip already placed in assets/backgrounds/ by the
   user (e.g. gameplay footage, satisfying/relaxing loops, timelapses they
   have the rights to use).
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import List, Optional

import requests

from .config import Config

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
_PEXELS_CACHE_DIR_NAME = "_pexels_cache"


def _local_backgrounds(background_dir: Path) -> List[Path]:
    if not background_dir.exists():
        return []
    return [p for p in background_dir.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS]


def _pick_local_background(background_dir: Path) -> Path:
    candidates = [p for p in _local_backgrounds(background_dir) if _PEXELS_CACHE_DIR_NAME not in p.parts]
    if not candidates:
        raise RuntimeError(
            f"No background video found in {background_dir}. Either add a royalty-free "
            "vertical .mp4 clip there (gameplay/parkour/satisfying loops you have the rights "
            "to use), or set PEXELS_API_KEY in .env to auto-fetch one from Pexels' free "
            "stock library."
        )
    return random.choice(candidates)


def _fetch_from_pexels(config: Config) -> Optional[Path]:
    cache_dir = config.background_dir / _PEXELS_CACHE_DIR_NAME
    cache_dir.mkdir(parents=True, exist_ok=True)

    headers = {"Authorization": config.pexels_api_key}
    params = {
        "query": config.pexels_query,
        "orientation": "portrait",
        "size": "medium",
        "per_page": 15,
    }
    response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=20)
    response.raise_for_status()
    videos = response.json().get("videos", [])
    random.shuffle(videos)

    for video in videos:
        files = [f for f in video.get("video_files", []) if f.get("width") and f.get("height")]
        portrait_files = [f for f in files if f["height"] >= f["width"]]
        files_to_try = sorted(portrait_files or files, key=lambda f: f.get("height", 0), reverse=True)
        if not files_to_try:
            continue
        chosen = files_to_try[0]
        out_path = cache_dir / f"pexels_{video['id']}.mp4"
        if out_path.exists():
            return out_path
        with requests.get(chosen["link"], stream=True, timeout=60) as dl:
            dl.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in dl.iter_content(chunk_size=1 << 16):
                    f.write(chunk)
        return out_path
    return None


def get_background_video(config: Config) -> Path:
    if config.pexels_api_key:
        try:
            fetched = _fetch_from_pexels(config)
            if fetched is not None:
                return fetched
        except requests.RequestException:
            pass  # fall through to local backgrounds
    return _pick_local_background(config.background_dir)
