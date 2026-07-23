import json
from unittest.mock import MagicMock

import pytest

from youtube_captions.extractor import (
    CaptionExtractor,
    Transcript,
    TranscriptSnippet,
)
from youtube_captions.formatters import to_json, to_srt, to_text, to_vtt


class TestExtractVideoId:
    def test_watch_url(self):
        assert (
            CaptionExtractor.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_short_url(self):
        assert (
            CaptionExtractor.extract_video_id("https://youtu.be/dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_embed_url(self):
        assert (
            CaptionExtractor.extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_direct_id(self):
        assert CaptionExtractor.extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            CaptionExtractor.extract_video_id("https://example.com")

    def test_strips_whitespace(self):
        assert CaptionExtractor.extract_video_id("  dQw4w9WgXcQ  ") == "dQw4w9WgXcQ"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            CaptionExtractor.extract_video_id("")

    def test_url_with_extra_params(self):
        assert (
            CaptionExtractor.extract_video_id(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
            )
            == "dQw4w9WgXcQ"
        )


class TestFormatters:
    @pytest.fixture
    def transcript(self):
        return Transcript(
            video_id="test123",
            language="English",
            language_code="en",
            is_generated=False,
            snippets=[
                TranscriptSnippet(text="Hello world", start=0.0, duration=1.5),
                TranscriptSnippet(text="How are you", start=1.5, duration=2.0),
            ],
        )

    def test_to_text(self, transcript):
        result = to_text(transcript)
        assert result == "Hello world How are you"

    def test_to_srt(self, transcript):
        result = to_srt(transcript)
        assert "1\n" in result
        assert "00:00:00,000 --> 00:00:01,500" in result
        assert "Hello world" in result

    def test_to_vtt(self, transcript):
        result = to_vtt(transcript)
        assert result.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:01.500" in result

    def test_to_json(self, transcript):
        result = to_json(transcript)
        data = json.loads(result)
        assert data["video_id"] == "test123"
        assert len(data["snippets"]) == 2

    def test_to_json_structure(self, transcript):
        data = json.loads(to_json(transcript))
        assert "video_id" in data
        assert "language" in data
        assert "language_code" in data
        assert "is_generated" in data
        assert "snippets" in data
        for s in data["snippets"]:
            assert "text" in s
            assert "start" in s
            assert "duration" in s

    def test_empty_transcript(self):
        t = Transcript(
            video_id="empty",
            language="English",
            language_code="en",
            is_generated=False,
            snippets=[],
        )
        assert to_text(t) == ""
        assert to_srt(t) == ""
        assert json.loads(to_json(t))["snippets"] == []


class TestTranscriptStats:
    def test_stats_computation(self):
        t = Transcript(
            video_id="test",
            language="English",
            language_code="en",
            is_generated=False,
            snippets=[
                TranscriptSnippet(text="Hello beautiful world", start=0.0, duration=2.0),
                TranscriptSnippet(text="How are you today", start=2.0, duration=3.0),
            ],
        )
        stats = t.stats
        assert stats.word_count == 7
        assert stats.snippet_count == 2
        assert stats.duration_seconds == 5.0

    def test_empty_stats(self):
        t = Transcript(
            video_id="test",
            language="English",
            language_code="en",
            is_generated=False,
            snippets=[],
        )
        stats = t.stats
        assert stats.word_count == 0
        assert stats.snippet_count == 0
        assert stats.duration_seconds == 0.0


class TestCache:
    def _make_fake_transcript(self):
        return Transcript(
            video_id="test",
            language="English",
            language_code="en",
            is_generated=False,
            snippets=[TranscriptSnippet(text="Hello", start=0.0, duration=1.0)],
        )

    def _make_fake_fetch_result(self):
        snippet = MagicMock()
        snippet.text = "Hello"
        snippet.start = 0.0
        snippet.duration = 1.0

        result = MagicMock()
        result.__iter__ = MagicMock(return_value=iter([snippet]))
        result.video_id = "test"
        result.language = "English"
        result.language_code = "en"
        result.is_generated = False
        return result

    def test_cache_hit(self):
        ext = CaptionExtractor(cache_ttl=60)
        ext._api = MagicMock()
        ext._api.fetch.return_value = self._make_fake_fetch_result()
        t1 = ext.extract("dQw4w9WgXcQ", use_cache=True)
        t2 = ext.extract("dQw4w9WgXcQ", use_cache=True)
        assert t1.video_id == t2.video_id
        ext._api.fetch.assert_called_once()

    def test_cache_disabled(self):
        ext = CaptionExtractor(cache_ttl=60)
        ext._api = MagicMock()
        ext._api.fetch.return_value = self._make_fake_fetch_result()
        ext.extract("dQw4w9WgXcQ", use_cache=False)
        ext.extract("dQw4w9WgXcQ", use_cache=False)
        assert ext._api.fetch.call_count == 2

    def test_clear_cache(self):
        ext = CaptionExtractor(cache_ttl=60)
        ext._api = MagicMock()
        ext._api.fetch.return_value = self._make_fake_fetch_result()
        ext.extract("dQw4w9WgXcQ", use_cache=True)
        assert len(ext._cache) > 0
        ext.clear_cache()
        assert len(ext._cache) == 0


class TestBatchExtraction:
    def _make_fake_transcript(self):
        return Transcript(
            video_id="test",
            language="English",
            language_code="en",
            is_generated=False,
            snippets=[TranscriptSnippet(text="Hello", start=0.0, duration=1.0)],
        )

    def test_batch_multiple(self):
        ext = CaptionExtractor()
        fake = self._make_fake_transcript()
        ext.extract = MagicMock(return_value=fake)
        results = ext.extract_batch(["dQw4w9WgXcQ"])
        assert len(results) == 1
        assert "dQw4w9WgXcQ" in results

    def test_batch_with_invalid(self):
        ext = CaptionExtractor()

        def fake_extract(url_or_id, **kwargs):
            vid = CaptionExtractor.extract_video_id(url_or_id)
            return Transcript(
                video_id=vid,
                language="English",
                language_code="en",
                is_generated=False,
                snippets=[TranscriptSnippet(text="Hi", start=0.0, duration=1.0)],
            )

        ext.extract = MagicMock(side_effect=fake_extract)
        results = ext.extract_batch(["dQw4w9WgXcQ", "https://example.com"])
        assert len(results) == 2
        assert isinstance(results["dQw4w9WgXcQ"], Transcript)
        assert isinstance(results["https://example.com"], str)
