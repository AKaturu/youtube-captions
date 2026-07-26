import json
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import web.app as web_app
from youtube_captions.extractor import (
    Transcript,
    TranscriptInfo,
    TranscriptSnippet,
)


def _make_transcript(video_id="test123"):
    return Transcript(
        video_id=video_id,
        language="English",
        language_code="en",
        is_generated=False,
        snippets=[
            TranscriptSnippet(text="Hello world", start=0.0, duration=1.5),
            TranscriptSnippet(text="How are you", start=1.5, duration=2.0),
        ],
    )


def _make_fetch_result(video_id="test123"):
    snippet = MagicMock()
    snippet.text = "Hello world"
    snippet.start = 0.0
    snippet.duration = 1.5
    snippet2 = MagicMock()
    snippet2.text = "How are you"
    snippet2.start = 1.5
    snippet2.duration = 2.0
    result = MagicMock()
    result.__iter__ = MagicMock(return_value=iter([snippet, snippet2]))
    result.video_id = video_id
    result.language = "English"
    result.language_code = "en"
    result.is_generated = False
    return result


def _make_language_infos():
    return [
        TranscriptInfo(language="English", language_code="en", is_generated=False),
        TranscriptInfo(language="Spanish", language_code="es", is_generated=True),
    ]


def _get_ext():
    return web_app.extractor


class TestIndexEndpoint:
    def test_index_returns_html(self):
        client = TestClient(web_app.app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]


class TestExtractEndpoint:
    def test_extract_text(self):
        ext = _get_ext()
        ext._api = MagicMock()
        ext._api.fetch.return_value = _make_fetch_result()
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.post(
            "/api/extract",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["video_id"] == "test123"
        assert data["language"] == "English"
        assert data["format"] == "text"
        assert "Hello world" in data["content"]
        assert data["stats"]["word_count"] == 5
        assert data["stats"]["snippet_count"] == 2

    def test_extract_srt_format(self):
        ext = _get_ext()
        ext._api = MagicMock()
        ext._api.fetch.return_value = _make_fetch_result()
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.post(
            "/api/extract",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "format": "srt",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "srt"
        assert "00:00:00,000 --> 00:00:01,500" in data["content"]

    def test_extract_vtt_format(self):
        ext = _get_ext()
        ext._api = MagicMock()
        ext._api.fetch.return_value = _make_fetch_result()
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.post(
            "/api/extract",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "format": "vtt",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["content"].startswith("WEBVTT")

    def test_extract_json_format(self):
        ext = _get_ext()
        ext._api = MagicMock()
        ext._api.fetch.return_value = _make_fetch_result()
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.post(
            "/api/extract",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "format": "json",
            },
        )
        assert resp.status_code == 200
        data = json.loads(resp.json()["content"])
        assert data["video_id"] == "test123"
        assert len(data["snippets"]) == 2

    def test_extract_unknown_format(self):
        ext = _get_ext()
        ext._api = MagicMock()
        ext._api.fetch.return_value = _make_fetch_result()
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.post(
            "/api/extract",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "format": "csv",
            },
        )
        assert resp.status_code == 400
        assert "Unknown format" in resp.json()["detail"]

    def test_extract_invalid_url(self):
        ext = _get_ext()
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.post(
            "/api/extract",
            json={"url": "https://example.com"},
        )
        assert resp.status_code == 400

    def test_extract_missing_url(self):
        client = TestClient(web_app.app)
        resp = client.post("/api/extract", json={})
        assert resp.status_code == 422


class TestBatchEndpoint:
    def test_batch_success(self):
        ext = _get_ext()
        ext.extract = MagicMock(return_value=_make_transcript())
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.post(
            "/api/batch",
            json={
                "urls": [
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "https://www.youtube.com/watch?v=abc12345678",
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_batch_empty_urls(self):
        ext = _get_ext()
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.post("/api/batch", json={"urls": []})
        assert resp.status_code == 200
        assert resp.json() == {}


class TestStatsEndpoint:
    def test_stats_success(self):
        ext = _get_ext()
        ext._api = MagicMock()
        ext._api.fetch.return_value = _make_fetch_result()
        ext._api.list.return_value = _make_language_infos()
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.get(
            "/api/stats",
            params={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["word_count"] == 5
        assert data["snippet_count"] == 2
        assert data["languages_available"] == 2

    def test_stats_invalid_url(self):
        ext = _get_ext()
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.get("/api/stats", params={"url": "https://example.com"})
        assert resp.status_code == 400

    def test_stats_missing_url(self):
        client = TestClient(web_app.app)
        resp = client.get("/api/stats")
        assert resp.status_code == 422


class TestListLanguagesEndpoint:
    def test_list_languages_success(self):
        ext = _get_ext()
        ext._api = MagicMock()
        ext._api.list.return_value = _make_language_infos()
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.get(
            "/api/list-languages",
            params={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["language_code"] == "en"
        assert data[1]["language_code"] == "es"

    def test_list_languages_invalid_url(self):
        ext = _get_ext()
        ext._cache.clear()

        client = TestClient(web_app.app)
        resp = client.get(
            "/api/list-languages",
            params={"url": "https://example.com"},
        )
        assert resp.status_code == 400

    def test_list_languages_missing_url(self):
        client = TestClient(web_app.app)
        resp = client.get("/api/list-languages")
        assert resp.status_code == 422


class TestConfigEndpoint:
    def test_get_config_defaults(self):
        client = TestClient(web_app.app)
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["proxy_url"] is None
        assert data["cookie_path"] is None

    def test_set_config(self):
        client = TestClient(web_app.app)
        resp = client.post(
            "/api/config",
            json={"proxy_url": "https://proxy:8080", "cookie_path": None},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        resp = client.get("/api/config")
        data = resp.json()
        assert data["proxy_url"] == "https://proxy:8080"
        assert data["cookie_path"] is None

    def test_clear_config(self):
        client = TestClient(web_app.app)
        client.post("/api/config", json={"proxy_url": "https://proxy:8080"})
        resp = client.post("/api/config", json={"proxy_url": None, "cookie_path": None})
        assert resp.status_code == 200
        data = client.get("/api/config").json()
        assert data["proxy_url"] is None
