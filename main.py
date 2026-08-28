"""CLI: turn a top AskReddit-style post into a narrated YouTube Short.

Usage:
    python main.py                       # build a video, don't upload
    python main.py --subreddit AskMen    # pull from a specific subreddit
    python main.py --upload              # build and publish to YouTube
    python main.py --upload --privacy public
"""
from __future__ import annotations

import argparse
import sys

from src.config import load_config
from src.pipeline import build_video_for_post, fetch_reddit_post
from src.youtube_upload import upload_video


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--subreddit", help="Subreddit to pull from (default: rotate through SUBREDDITS in .env)")
    parser.add_argument("--upload", action="store_true", help="Upload the finished video to YouTube")
    parser.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        help="Override YOUTUBE_PRIVACY_STATUS for this run",
    )
    args = parser.parse_args()

    config = load_config()

    print("Fetching a Reddit post...")
    post = fetch_reddit_post(config, subreddit=args.subreddit)
    print(f"Selected: r/{post.subreddit} - \"{post.title}\" ({len(post.comments)} comments)")

    print("Building video (narration + cards + background)...")
    result = build_video_for_post(config, post)
    print(f"Video written to {result.video_path}")

    if args.upload:
        privacy = args.privacy or config.youtube_privacy_status
        print(f"Uploading to YouTube (privacy={privacy})...")
        video_id = upload_video(
            result.video_path,
            result.title,
            result.description,
            result.tags,
            config.youtube_category_id,
            privacy,
            config.youtube_client_secrets_file,
            config.youtube_token_file,
        )
        print(f"Uploaded: https://youtu.be/{video_id}")
    else:
        print("Skipping upload (pass --upload to publish to YouTube).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
