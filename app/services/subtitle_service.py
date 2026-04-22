"""Subtitle service — wraps youtube-transcript-api for transcript fetching."""
from dataclasses import dataclass
from typing import List, Optional

from fastapi import status
from loguru import logger

from app.api_wrappers.youtube import _extract_video_id
from app.core.exceptions import AppError, BadRequestError


class SubtitlesUpstreamError(AppError):
    # Prateek: YouTube's unofficial transcript endpoint breaks often — surface 502.
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "SUBTITLES_UPSTREAM_ERROR"


@dataclass
class SubtitleEntry:
    start: float
    duration: float
    text: str


@dataclass
class SubtitleResult:
    video_id: str
    language: str
    entries: List[SubtitleEntry]
    srt: str
    vtt: str


def _format_timestamp(seconds: float, sep: str = ",") -> str:
    """Format seconds as HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT)."""
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def _build_srt(entries: List[SubtitleEntry]) -> str:
    lines: List[str] = []
    for i, e in enumerate(entries, 1):
        start = _format_timestamp(e.start, ",")
        end = _format_timestamp(e.start + e.duration, ",")
        lines.append(f"{i}\n{start} --> {end}\n{e.text}\n")
    return "\n".join(lines).strip() + "\n"


def _build_vtt(entries: List[SubtitleEntry]) -> str:
    lines: List[str] = ["WEBVTT\n"]
    for e in entries:
        start = _format_timestamp(e.start, ".")
        end = _format_timestamp(e.start + e.duration, ".")
        lines.append(f"{start} --> {end}\n{e.text}\n")
    return "\n".join(lines)


def fetch_subtitles(url: str, language: Optional[str] = None) -> SubtitleResult:
    """
    Fetch a YouTube video transcript and return both SRT and VTT.

    Raises SubtitlesUpstreamError (502) if the scraper fails — the library
    depends on an unofficial YouTube endpoint and breaks when YT ships
    anti-bot changes.
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        CouldNotRetrieveTranscript,
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )

    video_id = _extract_video_id(url)
    languages = (language,) if language else ("en",)

    try:
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=languages)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logger.info(
            "No transcript for video", video_id=video_id, err=type(e).__name__
        )
        raise AppError(
            "No subtitles are available for this video (transcripts disabled or missing)."
        )
    except VideoUnavailable:
        raise BadRequestError("Video is unavailable or private.")
    except CouldNotRetrieveTranscript as e:
        logger.warning(
            "YouTube transcript fetch failed",
            video_id=video_id,
            err=type(e).__name__,
        )
        raise SubtitlesUpstreamError(
            "YouTube subtitles endpoint rejected the request — try again later."
        )
    except Exception as e:
        logger.exception("Unexpected transcript error", video_id=video_id)
        raise SubtitlesUpstreamError(f"Unexpected transcript fetch error: {e}")

    entries = [
        SubtitleEntry(start=float(s.start), duration=float(s.duration), text=s.text)
        for s in fetched
    ]
    lang_code = getattr(fetched, "language_code", None) or (language or "en")

    return SubtitleResult(
        video_id=video_id,
        language=lang_code,
        entries=entries,
        srt=_build_srt(entries),
        vtt=_build_vtt(entries),
    )
