"""Renders Reddit-style title/comment card images with PIL."""
from __future__ import annotations

import random
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

CARD_WIDTH = 950
PADDING = 48
CARD_RADIUS = 28

BG_COLOR = (26, 26, 27, 235)
TEXT_COLOR = (215, 218, 220)
SUBTEXT_COLOR = (129, 130, 132)
ACCENT_COLOR = (255, 69, 0)
WHITE = (255, 255, 255)

AVATAR_PALETTE = [
    (255, 69, 0), (0, 121, 211), (70, 209, 128), (255, 176, 0),
    (255, 102, 172), (124, 92, 255), (0, 191, 179),
]

_FONT_SEARCH_DIRS = [
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation"),
]


def _find_font(names: List[str]) -> Path:
    for directory in _FONT_SEARCH_DIRS:
        for name in names:
            candidate = directory / name
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"None of the fonts {names} found under {_FONT_SEARCH_DIRS}")


BOLD_FONT_PATH = _find_font(["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"])
REGULAR_FONT_PATH = _find_font(["DejaVuSans.ttf", "LiberationSans-Regular.ttf"])

_font_cache: dict = {}


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    key = (str(path), size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(path), size)
    return _font_cache[key]


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _format_score(score: int) -> str:
    if score >= 10_000:
        return f"{score / 1000:.0f}k"
    if score >= 1_000:
        return f"{score / 1000:.1f}k".replace(".0k", "k")
    return str(score)


def _draw_avatar(draw: ImageDraw.ImageDraw, top_left: Tuple[int, int], size: int, letter: str, color) -> None:
    x, y = top_left
    draw.ellipse([x, y, x + size, y + size], fill=color)
    font = _font(BOLD_FONT_PATH, int(size * 0.5))
    bbox = draw.textbbox((0, 0), letter, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (x + size / 2 - tw / 2 - bbox[0], y + size / 2 - th / 2 - bbox[1]),
        letter,
        font=font,
        fill=WHITE,
    )


def _new_card(height: int) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (CARD_WIDTH, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, CARD_WIDTH - 1, height - 1], radius=CARD_RADIUS, fill=BG_COLOR)
    return img, draw


def _draw_upvote_footer(draw: ImageDraw.ImageDraw, y: int, score: int) -> None:
    x = PADDING
    arrow = 20
    draw.polygon([(x, y + arrow), (x + arrow, y + arrow), (x + arrow / 2, y)], fill=ACCENT_COLOR)
    font = _font(BOLD_FONT_PATH, 30)
    draw.text((x + arrow + 14, y - 5), _format_score(score), font=font, fill=TEXT_COLOR)


def render_title_card(subreddit: str, title: str, author: str, score: int) -> Image.Image:
    header_font = _font(BOLD_FONT_PATH, 30)
    sub_font = _font(REGULAR_FONT_PATH, 24)
    title_font = _font(BOLD_FONT_PATH, 46)

    measurer = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    text_width = CARD_WIDTH - PADDING * 2
    lines = _wrap_text(measurer, title, title_font, text_width)

    avatar_size = 64
    header_h = avatar_size
    line_h = 58
    title_block_h = len(lines) * line_h
    footer_h = 50
    height = PADDING + header_h + 26 + title_block_h + 20 + footer_h + PADDING

    img, draw = _new_card(height)

    avatar_color = random.choice(AVATAR_PALETTE)
    _draw_avatar(draw, (PADDING, PADDING), avatar_size, subreddit[0].upper(), avatar_color)
    draw.text((PADDING + avatar_size + 18, PADDING), f"r/{subreddit}", font=header_font, fill=TEXT_COLOR)
    draw.text(
        (PADDING + avatar_size + 18, PADDING + 34),
        f"Posted by u/{author}",
        font=sub_font,
        fill=SUBTEXT_COLOR,
    )

    y = PADDING + header_h + 26
    for line in lines:
        draw.text((PADDING, y), line, font=title_font, fill=TEXT_COLOR)
        y += line_h

    _draw_upvote_footer(draw, y + 20, score)
    return img


def render_comment_card(author: str, body: str, score: int) -> Image.Image:
    header_font = _font(BOLD_FONT_PATH, 28)
    body_font = _font(REGULAR_FONT_PATH, 38)

    measurer = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    text_width = CARD_WIDTH - PADDING * 2
    lines = _wrap_text(measurer, body, body_font, text_width)

    avatar_size = 56
    header_h = avatar_size
    line_h = 50
    body_block_h = len(lines) * line_h
    footer_h = 46
    height = PADDING + header_h + 22 + body_block_h + 18 + footer_h + PADDING

    img, draw = _new_card(height)

    avatar_color = random.choice(AVATAR_PALETTE)
    _draw_avatar(draw, (PADDING, PADDING), avatar_size, author[0].upper(), avatar_color)
    draw.text(
        (PADDING + avatar_size + 16, PADDING + avatar_size / 2 - 17),
        f"u/{author}",
        font=header_font,
        fill=TEXT_COLOR,
    )

    y = PADDING + header_h + 22
    for line in lines:
        draw.text((PADDING, y), line, font=body_font, fill=TEXT_COLOR)
        y += line_h

    _draw_upvote_footer(draw, y + 18, score)
    return img


def save_card(img: Image.Image, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path
