"""Orchestrates: fetch Reddit post -> narrate -> render cards -> assemble video."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from . import cards, narration
from .background import get_background_video
from .config import Config
from .reddit_source import RedditPost, fetch_post, get_reddit_client, mark_used
from .video import Segment, build_video

TITLE_PAD = 0.6
COMMENT_PAD = 0.4
MUSIC_EXTENSIONS = {".mp3", ".wav", ".m4a"}


@dataclass
class BuildResult:
    post: RedditPost
    video_path: Path
    title: str
    description: str
    tags: List[str]


def _slug(text: str, max_len: int = 60) -> str:
    keep = "".join(c if c.isalnum() or c in " -_" else "" for c in text)
    keep = "_".join(keep.split())
    return keep[:max_len] or "video"


def _make_youtube_title(post: RedditPost) -> str:
    suffix = " #shorts"
    max_len = 100 - len(suffix)
    title = post.title.strip()
    if len(title) > max_len:
        title = title[: max_len - 1].rsplit(" ", 1)[0] + "…"
    return title + suffix


def _make_description(post: RedditPost) -> str:
    lines = [
        post.title,
        "",
        f"Original post: r/{post.subreddit} — {post.url}",
        "",
        "Top comments featured are from Reddit users; full credit to the original "
        "commenters linked above.",
        "",
        "#shorts #askreddit #reddit",
    ]
    return "\n".join(lines)


def _make_tags(post: RedditPost) -> List[str]:
    tags = ["reddit", "askreddit", post.subreddit.lower(), "shorts", "reddit stories"]
    seen = set()
    deduped = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            deduped.append(tag)
    return deduped


def fetch_reddit_post(config: Config, subreddit: Optional[str] = None) -> RedditPost:
    reddit = get_reddit_client(config)
    used_ids_file = config.output_dir / "used_posts.json"
    post = fetch_post(reddit, config, subreddit_name=subreddit, used_ids_file=used_ids_file)
    if post is None:
        raise RuntimeError(
            "No suitable post found (needs to be a text question post with enough "
            "highly-upvoted comments). Try a different subreddit, lower MIN_COMMENT_SCORE, "
            "or a wider POST_TIME_FILTER."
        )
    mark_used(used_ids_file, post.id)
    return post


def _pick_music(config: Config) -> Optional[Path]:
    candidates = [p for p in config.music_dir.glob("*") if p.suffix.lower() in MUSIC_EXTENSIONS]
    return random.choice(candidates) if candidates else None


def build_video_for_post(config: Config, post: RedditPost) -> BuildResult:
    work_dir = config.output_dir / post.id
    work_dir.mkdir(parents=True, exist_ok=True)

    segments: List[Segment] = []

    title_audio = narration.synthesize(
        post.title, config.title_voice, config.tts_rate, work_dir / "audio_title.mp3"
    )
    title_card_path = cards.save_card(
        cards.render_title_card(post.subreddit, post.title, post.author, post.score),
        work_dir / "card_title.png",
    )
    segments.append(
        Segment(
            image_path=title_card_path,
            audio_path=title_audio,
            duration=narration.audio_duration(title_audio) + TITLE_PAD,
        )
    )

    for i, comment in enumerate(post.comments):
        audio_path = narration.synthesize(
            comment.body, config.comment_voice, config.tts_rate, work_dir / f"audio_comment_{i}.mp3"
        )
        card_path = cards.save_card(
            cards.render_comment_card(comment.author, comment.body, comment.score),
            work_dir / f"card_comment_{i}.png",
        )
        segments.append(
            Segment(
                image_path=card_path,
                audio_path=audio_path,
                duration=narration.audio_duration(audio_path) + COMMENT_PAD,
            )
        )

    background_path = get_background_video(config)
    music_path = _pick_music(config)

    output_path = config.output_dir / f"{post.id}_{_slug(post.title)}.mp4"
    build_video(
        background_path,
        segments,
        output_path,
        music_path=music_path,
        music_volume=config.music_volume,
    )

    result = BuildResult(
        post=post,
        video_path=output_path,
        title=_make_youtube_title(post),
        description=_make_description(post),
        tags=_make_tags(post),
    )

    output_path.with_suffix(".json").write_text(
        json.dumps(
            {
                "post_id": post.id,
                "subreddit": post.subreddit,
                "url": post.url,
                "youtube_title": result.title,
                "youtube_description": result.description,
                "youtube_tags": result.tags,
            },
            indent=2,
        )
    )
    return result
