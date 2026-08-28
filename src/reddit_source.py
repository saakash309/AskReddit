"""Fetches a suitable AskReddit-style post + its top comments via PRAW."""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import praw

from .config import Config

BLOCKED_AUTHORS = {"AutoModerator", "[deleted]"}
DEAD_COMMENT_BODIES = {"[removed]", "[deleted]"}

_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_URL_RE = re.compile(r"https?://\S+")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class Comment:
    author: str
    body: str
    score: int


@dataclass
class RedditPost:
    id: str
    subreddit: str
    title: str
    author: str
    score: int
    url: str
    comments: List[Comment] = field(default_factory=list)


def get_reddit_client(config: Config) -> praw.Reddit:
    config.require_reddit_credentials()
    return praw.Reddit(
        client_id=config.reddit_client_id,
        client_secret=config.reddit_client_secret,
        user_agent=config.reddit_user_agent,
    )


def _clean_text(text: str) -> str:
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)
    text = _URL_RE.sub("", text)
    text = text.replace("&amp;", "&").replace("*", "").replace("_", "").replace("^", "")
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "..."


def _load_used_ids(used_ids_file: Path) -> set:
    if used_ids_file.exists():
        try:
            return set(json.loads(used_ids_file.read_text()))
        except (json.JSONDecodeError, OSError):
            return set()
    return set()


def mark_used(used_ids_file: Path, post_id: str) -> None:
    used = _load_used_ids(used_ids_file)
    used.add(post_id)
    used_ids_file.write_text(json.dumps(sorted(used)))


def _extract_comments(submission, num_comments: int, max_chars: int, min_score: int) -> List[Comment]:
    submission.comment_sort = "top"
    submission.comments.replace_more(limit=0)
    candidates: List[Comment] = []
    seen_bodies = set()
    for c in submission.comments:
        if len(candidates) >= num_comments:
            break
        body = getattr(c, "body", None)
        if not body or body in DEAD_COMMENT_BODIES:
            continue
        if getattr(c, "stickied", False):
            continue
        author = c.author
        if author is None or str(author) in BLOCKED_AUTHORS:
            continue
        if int(getattr(c, "score", 0)) < min_score:
            continue
        cleaned = _clean_text(body)
        if not cleaned or len(cleaned) < 10:
            continue
        cleaned = _truncate(cleaned, max_chars)
        if cleaned.lower() in seen_bodies:
            continue
        seen_bodies.add(cleaned.lower())
        candidates.append(Comment(author=str(author), body=cleaned, score=int(c.score)))
    return candidates


def fetch_post(
    reddit: praw.Reddit,
    config: Config,
    subreddit_name: Optional[str] = None,
    used_ids_file: Optional[Path] = None,
) -> Optional[RedditPost]:
    """Scan a subreddit's top posts for the first one with enough good comments."""
    subreddits = [subreddit_name] if subreddit_name else list(config.subreddits)
    random.shuffle(subreddits)
    used_ids = _load_used_ids(used_ids_file) if used_ids_file else set()

    for name in subreddits:
        subreddit = reddit.subreddit(name)
        try:
            submissions = subreddit.top(time_filter=config.post_time_filter, limit=config.post_scan_limit)
        except Exception:
            continue
        for submission in submissions:
            if submission.id in used_ids:
                continue
            if submission.over_18 or submission.stickied or submission.locked:
                continue
            if not submission.is_self:
                continue
            title = _clean_text(submission.title)
            if not title or len(title) > config.max_title_chars:
                continue
            if not title.rstrip().endswith("?"):
                # AskReddit-style posts are questions; skip anything that isn't.
                continue
            comments = _extract_comments(
                submission,
                num_comments=config.num_comments,
                max_chars=config.max_comment_chars,
                min_score=config.min_comment_score,
            )
            if len(comments) < min(2, config.num_comments):
                continue
            return RedditPost(
                id=submission.id,
                subreddit=name,
                title=title,
                author=str(submission.author) if submission.author else "unknown",
                score=int(submission.score),
                url=f"https://reddit.com{submission.permalink}",
                comments=comments,
            )
    return None
