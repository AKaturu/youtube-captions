# Youtube Captions

A Python library, CLI tool, and web app for extracting captions and subtitles from YouTube videos. No API key required.

Supports manual and auto-generated captions in any available language, with optional translation, batch extraction, caching, and multiple output formats.

## Features

- **Multiple output formats** -- plain text, SRT, VTT, and JSON
- **Language detection** -- list available caption tracks for any video
- **Translation** -- translate captions to a target language
- **Batch extraction** -- process multiple videos in one call
- **Caching** -- in-memory TTL cache to avoid redundant requests
- **Statistics** -- word count, segment count, and duration
- **Web interface** -- browser UI with transcript search, dark mode, and keyboard shortcuts
- **CLI tool** -- `yt-captions` for terminal workflows
- **Library** -- import `CaptionExtractor` directly in Python code

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## Run the web app

```powershell
python -m web.app
```

Opens at `http://127.0.0.1:8000`. The interface includes:

- Transcript extraction with format selection (text, SRT, VTT, JSON)
- Available language detection with clickable language chips
- Transcript search with match highlighting
- Word count, segment count, and duration statistics
- Recent extraction history (stored locally in the browser)
- Dark mode toggle
- Keyboard shortcuts (`Ctrl+Enter` to extract, `Ctrl+C` to copy)
- Shareable URL deep links (`?v=VIDEO_ID&format=srt`)

## Run the CLI

```powershell
yt-captions https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Examples

```powershell
# Plain text output (default)
yt-captions https://www.youtube.com/watch?v=dQw4w9WgXcQ

# SRT format
yt-captions -f srt https://www.youtube.com/watch?v=dQw4w9WgXcQ

# JSON format
yt-captions -f json https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Prefer a specific language
yt-captions -l es https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Translate to French
yt-captions -t fr https://www.youtube.com/watch?v=dQw4w9WgXcQ

# List available languages
yt-captions --list-languages https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Show transcript statistics
yt-captions --stats https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Process multiple videos
yt-captions URL1 URL2 URL3

# Disable caching
yt-captions --no-cache https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

## Library usage

```python
from youtube_captions import CaptionExtractor, to_srt, to_json

extractor = CaptionExtractor()

# Extract a transcript
transcript = extractor.extract("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Format output
print(to_srt(transcript))
print(to_json(transcript))

# Translate to Spanish
transcript_es = extractor.extract(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    translate_to="es",
)

# Batch extract
results = extractor.extract_batch(["VIDEO_ID_1", "VIDEO_ID_2"])

# Get statistics
stats = extractor.get_stats("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(f"{stats.word_count} words, {stats.duration_seconds:.1f}s")
```

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web interface |
| `GET` | `/api/list-languages?url=VIDEO_URL` | List available caption tracks |
| `GET` | `/api/stats?url=VIDEO_URL` | Get transcript statistics |
| `POST` | `/api/extract` | Extract a single transcript |
| `POST` | `/api/batch` | Extract transcripts from multiple videos |

### POST `/api/extract`

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "format": "srt",
  "language": "en",
  "translate_to": "fr"
}
```

### POST `/api/batch`

```json
{
  "urls": ["VIDEO_ID_1", "VIDEO_ID_2"],
  "format": "json",
  "translate_to": "es"
}
```

## Project structure

```
Youtube Captions/
  youtube_captions/         Python package
    __init__.py             Public API exports
    extractor.py            CaptionExtractor, Transcript, TranscriptInfo, TranscriptStats
    formatters.py           to_text, to_srt, to_vtt, to_json
    cli.py                  yt-captions CLI entry point
  web/
    app.py                  FastAPI application and API routes
    static/
      index.html            Browser interface
      app.css               Styles with light and dark themes
  tests/
    test_core.py            Unit tests with mocked API calls
  pyproject.toml            Package metadata, dependencies, and entry points
```

## Privacy

There are no cloud APIs, analytics, remote fonts, or CDN assets. Captions are fetched directly from YouTube's public subtitle data using the [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api).

## License

MIT
