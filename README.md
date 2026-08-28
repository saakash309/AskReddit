# AskReddit Shorts

Turns a top AskReddit-style post into a narrated YouTube Short:

1. **Fetch** a question post and its top comments from Reddit (PRAW).
2. **Render** Reddit-style title/comment card images (Pillow).
3. **Narrate** the question and each comment with text-to-speech (edge-tts,
   free, no API key).
4. **Composite** the cards over a royalty-free vertical background video,
   timed to match each narration clip, mixed with optional background music
   (MoviePy).
5. **Upload** the finished 1080x1920 MP4 to YouTube as a Short (YouTube Data
   API v3), optional.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`ffmpeg` is not a separate system requirement — MoviePy pulls in a bundled
binary via `imageio-ffmpeg`.

### 1. Reddit API credentials (required)

Create a "script" app at <https://www.reddit.com/prefs/apps>, then fill in
`.env`:

```
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=askreddit-shorts-bot by u/your_username
```

### 2. Background video (required)

Two options, in priority order:

- **Auto (recommended):** get a free API key at <https://www.pexels.com/api/>
  and set `PEXELS_API_KEY` in `.env`. Pexels' license allows free use,
  including commercial, with no attribution required — every run fetches a
  fresh royalty-free vertical clip matching `PEXELS_QUERY` (e.g. "minecraft
  parkour", "satisfying", "subway surfers").
- **Manual:** drop your own royalty-free/non-copyright vertical `.mp4` clips
  into `assets/backgrounds/`. One is picked at random each run.

### 3. Voiceover

Uses [`edge-tts`](https://github.com/rany2/edge-tts) — free, no signup.
List available voices with `edge-tts --list-voices`, then set `TITLE_VOICE`
/ `COMMENT_VOICE` in `.env` (defaults: `en-US-GuyNeural` for the question,
`en-US-AriaNeural` for comments, so they sound distinct).

### 4. Background music (optional)

Drop a royalty-free `.mp3`/`.wav` into `assets/music/`; it's mixed in quietly
(`MUSIC_VOLUME`, default 8%) under the narration. Skipped if the folder is
empty.

### 5. YouTube upload (optional)

Only needed if you pass `--upload`:

1. In [Google Cloud Console](https://console.cloud.google.com/), create a
   project, enable the **YouTube Data API v3**, and create an **OAuth
   client ID** of type "Desktop app".
2. Download it as `client_secret.json` in the project root.
3. First upload opens a browser for one-time consent; a refresh token is
   cached in `token.json` so later runs are non-interactive.

## Usage

```bash
# Build a video only (no upload) — picks a subreddit from SUBREDDITS in .env
python main.py

# Pull from a specific subreddit
python main.py --subreddit AskMen

# Build and publish to YouTube
python main.py --upload --privacy public
```

Each run writes `output/<post_id>_<slug>.mp4` plus a `.json` file with the
suggested YouTube title/description/tags. Already-used post IDs are tracked
in `output/used_posts.json` so reruns don't repeat a post.

## Project layout

```
main.py                 CLI entrypoint
src/
  config.py              env-driven settings
  reddit_source.py        PRAW: pick a post + top comments
  narration.py            edge-tts voiceover + duration lookup
  cards.py                PIL: title/comment card rendering
  background.py           local clip picker + optional Pexels fetch
  video.py                MoviePy: crop/loop background, overlay cards, mux audio
  youtube_upload.py       OAuth + resumable upload
  pipeline.py             ties it all together, writes metadata sidecar
assets/
  backgrounds/            your own background clips (gitignored cache excluded)
  music/                  optional background music
output/                   generated videos (gitignored)
```

## Notes

- Comments are filtered: no `AutoModerator`/deleted/removed, no stickied
  comments, minimum score threshold (`MIN_COMMENT_SCORE`), truncated to
  `MAX_COMMENT_CHARS` for pacing.
- Only self (text) posts whose title ends in `?` are considered, matching
  AskReddit's question format.
- Video output is 1080x1920 @ 30fps, H.264/AAC — YouTube Shorts spec.
- Give credit to original posters/commenters in the description (already
  included by default) and check the target subreddit's rules and Reddit's
  API terms before publishing content pulled from it.
