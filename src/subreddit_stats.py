"""Feedback loop: weight subreddits by how well past uploads actually performed.

Every successful upload is appended to output/uploads_log.jsonl. compute_weights()
pulls current view counts for those videos (via the public Data API, read-only)
and turns average views-per-subreddit into a ranking multiplier, so subreddits
that historically get watched are favored over ones that don't. Uniform weights
(empty dict) if there's no API key configured or not enough data yet.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List

import requests

from .config import Config

YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
MIN_VIDEOS_PER_SUBREDDIT = 3
WEIGHT_MIN = 0.5
WEIGHT_MAX = 2.0
CACHE_TTL_SECONDS = 12 * 3600


def record_upload(log_file: Path, video_id: str, post_id: str, subreddit: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "video_id": video_id,
        "post_id": post_id,
        "subreddit": subreddit,
        "uploaded_at": int(time.time()),
    }
    with log_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _load_uploads(log_file: Path) -> List[dict]:
    if not log_file.exists():
        return []
    entries = []
    for line in log_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _fetch_view_counts(video_ids: List[str], api_key: str) -> Dict[str, int]:
    views: Dict[str, int] = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        resp = requests.get(
            YOUTUBE_VIDEOS_URL,
            params={"part": "statistics", "id": ",".join(batch), "key": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        for item in resp.json().get("items", []):
            views[item["id"]] = int(item.get("statistics", {}).get("viewCount", 0))
    return views


def compute_weights(config: Config) -> Dict[str, float]:
    """Returns {subreddit: multiplier}. Empty when disabled or data is insufficient."""
    cache_file = config.output_dir / "subreddit_weights.json"
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text())
            if time.time() - cached.get("computed_at", 0) < CACHE_TTL_SECONDS:
                return cached.get("weights", {})
        except (json.JSONDecodeError, OSError):
            pass

    if not config.youtube_api_key:
        return {}

    uploads = _load_uploads(config.output_dir / "uploads_log.jsonl")
    if not uploads:
        return {}

    try:
        views = _fetch_view_counts([u["video_id"] for u in uploads], config.youtube_api_key)
    except Exception:
        return {}

    per_sub: Dict[str, List[int]] = {}
    for u in uploads:
        v = views.get(u["video_id"])
        if v is not None:
            per_sub.setdefault(u["subreddit"], []).append(v)

    eligible = {sub: vs for sub, vs in per_sub.items() if len(vs) >= MIN_VIDEOS_PER_SUBREDDIT}
    if len(eligible) < 2:
        return {}

    averages = {sub: sum(vs) / len(vs) for sub, vs in eligible.items()}
    overall_avg = sum(averages.values()) / len(averages)
    if overall_avg <= 0:
        return {}

    weights = {sub: max(WEIGHT_MIN, min(WEIGHT_MAX, avg / overall_avg)) for sub, avg in averages.items()}

    try:
        cache_file.write_text(json.dumps({"computed_at": int(time.time()), "weights": weights}))
    except OSError:
        pass
    return weights
