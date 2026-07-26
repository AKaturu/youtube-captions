from __future__ import annotations

import http.cookiejar
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import IpBlocked, RequestBlocked
from youtube_transcript_api.proxies import GenericProxyConfig

VIDEO_ID_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})"
)
VIDEO_ID_DIRECT = re.compile(r"^[a-zA-Z0-9_-]{11}$")


@dataclass
class TranscriptSnippet:
    text: str
    start: float
    duration: float


@dataclass
class TranscriptInfo:
    language: str
    language_code: str
    is_generated: bool


@dataclass
class TranscriptStats:
    word_count: int
    snippet_count: int
    duration_seconds: float
    languages_available: int


@dataclass
class Transcript:
    video_id: str
    language: str
    language_code: str
    is_generated: bool
    snippets: List[TranscriptSnippet]

    @property
    def stats(self) -> TranscriptStats:
        words = sum(len(s.text.split()) for s in self.snippets)
        duration = (
            (self.snippets[-1].start + self.snippets[-1].duration)
            if self.snippets
            else 0.0
        )
        return TranscriptStats(
            word_count=words,
            snippet_count=len(self.snippets),
            duration_seconds=round(duration, 2),
            languages_available=0,
        )


@dataclass
class _CacheEntry:
    transcript: Transcript
    timestamp: float


class CaptionExtractor:
    def __init__(
        self,
        cache_ttl: int = 300,
        max_retries: int = 3,
        cookie_path: Optional[str] = None,
        proxy_url: Optional[str] = None,
    ) -> None:
        self._cache: Dict[str, _CacheEntry] = {}
        self._cache_ttl = cache_ttl
        self._max_retries = max_retries

        http_client: Optional[requests.Session] = None
        proxy_config: Optional[GenericProxyConfig] = None

        if cookie_path:
            http_client = requests.Session()
            cj = http.cookiejar.MozillaCookieJar(cookie_path)
            cj.load(ignore_discard=True, ignore_expires=True)
            http_client.cookies = cj  # type: ignore[assignment]

        if proxy_url:
            proxy_config = GenericProxyConfig(https_url=proxy_url)

        self._api = YouTubeTranscriptApi(
            proxy_config=proxy_config,
            http_client=http_client,
        )

    def _retry(self, fn, *args, **kwargs):  # noqa: ANN002, ANN003
        last_exc = None
        for attempt in range(self._max_retries):
            try:
                return fn(*args, **kwargs)
            except (RequestBlocked, IpBlocked) as e:
                last_exc = e
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)
        raise last_exc  # type: ignore[misc]

    @staticmethod
    def extract_video_id(url_or_id: str) -> str:
        url_or_id = url_or_id.strip()

        match = VIDEO_ID_PATTERN.search(url_or_id)
        if match:
            return match.group(1)

        if VIDEO_ID_DIRECT.match(url_or_id):
            return url_or_id

        raise ValueError(f"Invalid YouTube URL or video ID: {url_or_id}")

    def _get_cache_key(
        self, video_id: str, languages: List[str], translate_to: Optional[str]
    ) -> str:
        lang_key = ",".join(languages)
        return f"{video_id}:{lang_key}:{translate_to or ''}"

    def _get_cached(self, key: str) -> Optional[Transcript]:
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry.timestamp < self._cache_ttl:
                return entry.transcript
            del self._cache[key]
        return None

    def _set_cache(self, key: str, transcript: Transcript) -> None:
        self._cache[key] = _CacheEntry(transcript=transcript, timestamp=time.time())

    def list_available(self, url_or_id: str) -> List[TranscriptInfo]:
        video_id = self.extract_video_id(url_or_id)
        transcript_list = self._retry(self._api.list, video_id)
        return [
            TranscriptInfo(
                language=t.language,
                language_code=t.language_code,
                is_generated=t.is_generated,
            )
            for t in transcript_list
        ]

    def extract(
        self,
        url_or_id: str,
        language: Optional[str] = None,
        languages: Optional[List[str]] = None,
        translate_to: Optional[str] = None,
        use_cache: bool = True,
    ) -> Transcript:
        video_id = self.extract_video_id(url_or_id)

        if language and not languages:
            languages = [language]
        elif not languages:
            languages = ["en"]

        cache_key = self._get_cache_key(video_id, languages, translate_to)

        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                return cached

        fetched = self._retry(self._api.fetch, video_id, languages=languages)

        if translate_to:
            transcript_list = self._retry(self._api.list, video_id)
            found = None
            for t in transcript_list:
                if t.language_code == fetched.language_code:
                    found = t
                    break
            if found and found.is_translatable:
                translated = found.translate(translate_to)
                fetched = translated.fetch()

        snippets = [
            TranscriptSnippet(
                text=s.text,
                start=s.start,
                duration=s.duration,
            )
            for s in fetched
        ]

        transcript = Transcript(
            video_id=fetched.video_id,
            language=fetched.language,
            language_code=fetched.language_code,
            is_generated=fetched.is_generated,
            snippets=snippets,
        )

        if use_cache:
            self._set_cache(cache_key, transcript)

        return transcript

    def extract_batch(
        self,
        urls_or_ids: List[str],
        language: Optional[str] = None,
        languages: Optional[List[str]] = None,
        translate_to: Optional[str] = None,
    ) -> Dict[str, Transcript | str]:
        results: Dict[str, Transcript | str] = {}
        for url in urls_or_ids:
            try:
                results[url] = self.extract(
                    url,
                    language=language,
                    languages=languages,
                    translate_to=translate_to,
                )
            except Exception as e:
                results[url] = str(e)
        return results

    def get_stats(self, url_or_id: str) -> TranscriptStats:
        transcript = self.extract(url_or_id)
        info = self.list_available(url_or_id)
        stats = transcript.stats
        stats.languages_available = len(info)
        return stats

    def clear_cache(self) -> None:
        self._cache.clear()
