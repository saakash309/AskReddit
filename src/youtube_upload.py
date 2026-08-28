"""Uploads a finished short to YouTube via the YouTube Data API v3.

Requires an OAuth "Desktop app" client (console.cloud.google.com -> APIs &
Services -> Credentials) downloaded as client_secret.json. The first run
opens a browser for consent and caches a refresh token in token.json so
later runs are non-interactive.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_credentials(client_secrets_file: Path, token_file: Path) -> Credentials:
    creds: Optional[Credentials] = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secrets_file.exists():
                raise RuntimeError(
                    f"YouTube OAuth client file not found at {client_secrets_file}. "
                    "Create an OAuth 2.0 Desktop app client at "
                    "https://console.cloud.google.com/apis/credentials, enable the "
                    "YouTube Data API v3, and download it as client_secret.json."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_file), SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())
    return creds


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: List[str],
    category_id: str,
    privacy_status: str,
    client_secrets_file: Path,
    token_file: Path,
) -> str:
    """Uploads `video_path` to YouTube and returns the resulting video ID."""
    creds = _get_credentials(client_secrets_file, token_file)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
    return response["id"]
