"""Central configuration, loaded from environment variables / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent


def _env_list(name: str, default: str) -> List[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Config:
    # Reddit
    reddit_client_id: str = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_ID", ""))
    reddit_client_secret: str = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_SECRET", ""))
    reddit_user_agent: str = field(default_factory=lambda: os.getenv("REDDIT_USER_AGENT", "askreddit-shorts-bot"))

    subreddits: List[str] = field(default_factory=lambda: _env_list("SUBREDDITS", "AskReddit"))
    post_time_filter: str = field(default_factory=lambda: os.getenv("POST_TIME_FILTER", "day"))
    post_scan_limit: int = field(default_factory=lambda: _env_int("POST_SCAN_LIMIT", 25))
    num_comments: int = field(default_factory=lambda: _env_int("NUM_COMMENTS", 4))
    max_title_chars: int = field(default_factory=lambda: _env_int("MAX_TITLE_CHARS", 200))
    max_comment_chars: int = field(default_factory=lambda: _env_int("MAX_COMMENT_CHARS", 280))
    min_comment_score: int = field(default_factory=lambda: _env_int("MIN_COMMENT_SCORE", 15))

    # TTS
    title_voice: str = field(default_factory=lambda: os.getenv("TITLE_VOICE", "en-US-GuyNeural"))
    comment_voice: str = field(default_factory=lambda: os.getenv("COMMENT_VOICE", "en-US-AriaNeural"))
    tts_rate: str = field(default_factory=lambda: os.getenv("TTS_RATE", "+0%"))

    # Background video
    background_dir: Path = field(default_factory=lambda: ROOT_DIR / os.getenv("BACKGROUND_DIR", "assets/backgrounds"))
    pexels_api_key: str = field(default_factory=lambda: os.getenv("PEXELS_API_KEY", ""))
    pexels_query: str = field(default_factory=lambda: os.getenv("PEXELS_QUERY", "minecraft parkour"))

    # Music
    music_dir: Path = field(default_factory=lambda: ROOT_DIR / os.getenv("MUSIC_DIR", "assets/music"))
    music_volume: float = field(default_factory=lambda: _env_float("MUSIC_VOLUME", 0.08))

    # Output
    output_dir: Path = field(default_factory=lambda: ROOT_DIR / os.getenv("OUTPUT_DIR", "output"))

    # YouTube
    youtube_client_secrets_file: Path = field(
        default_factory=lambda: ROOT_DIR / os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secret.json")
    )
    youtube_token_file: Path = field(
        default_factory=lambda: ROOT_DIR / os.getenv("YOUTUBE_TOKEN_FILE", "token.json")
    )
    youtube_privacy_status: str = field(default_factory=lambda: os.getenv("YOUTUBE_PRIVACY_STATUS", "private"))
    youtube_category_id: str = field(default_factory=lambda: os.getenv("YOUTUBE_CATEGORY_ID", "24"))

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.background_dir.mkdir(parents=True, exist_ok=True)
        self.music_dir.mkdir(parents=True, exist_ok=True)

    def require_reddit_credentials(self) -> None:
        missing = [
            name
            for name, value in (
                ("REDDIT_CLIENT_ID", self.reddit_client_id),
                ("REDDIT_CLIENT_SECRET", self.reddit_client_secret),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing Reddit API credentials: "
                + ", ".join(missing)
                + ". Copy .env.example to .env and fill them in "
                + "(create an app at https://www.reddit.com/prefs/apps)."
            )


def load_config() -> Config:
    return Config()
