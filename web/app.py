from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from youtube_captions.extractor import CaptionExtractor
from youtube_captions.formatters import to_json, to_srt, to_text, to_vtt


class ExtractRequest(BaseModel):
    url: str
    language: str | None = None
    languages: list[str] | None = None
    format: str = "text"
    translate_to: str | None = None


class BatchRequest(BaseModel):
    urls: list[str]
    language: str | None = None
    languages: list[str] | None = None
    format: str = "text"
    translate_to: str | None = None


app = FastAPI(title="YouTube Captions", version="0.2.0")
extractor = CaptionExtractor()

app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("web/static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/list-languages")
async def api_list_languages(url: str = Query(...)):
    try:
        infos = extractor.list_available(url)
        return JSONResponse(
            content=[
                {
                    "language": info.language,
                    "language_code": info.language_code,
                    "is_generated": info.is_generated,
                }
                for info in infos
            ]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")


@app.post("/api/extract")
async def api_extract(req: ExtractRequest):
    try:
        transcript = extractor.extract(
            req.url,
            language=req.language,
            languages=req.languages,
            translate_to=req.translate_to,
        )

        fmt = req.format.lower()
        if fmt == "text":
            content = to_text(transcript)
        elif fmt == "srt":
            content = to_srt(transcript)
        elif fmt == "vtt":
            content = to_vtt(transcript)
        elif fmt == "json":
            content = to_json(transcript)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}")

        stats = transcript.stats

        return JSONResponse(
            content={
                "video_id": transcript.video_id,
                "language": transcript.language,
                "language_code": transcript.language_code,
                "is_generated": transcript.is_generated,
                "format": fmt,
                "content": content,
                "stats": {
                    "word_count": stats.word_count,
                    "snippet_count": stats.snippet_count,
                    "duration_seconds": stats.duration_seconds,
                },
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")


@app.post("/api/batch")
async def api_batch(req: BatchRequest):
    try:
        results = extractor.extract_batch(
            req.urls,
            language=req.language,
            languages=req.languages,
            translate_to=req.translate_to,
        )

        fmt = req.format.lower()
        output = {}
        for url, result in results.items():
            if isinstance(result, str):
                output[url] = {"error": result}
            else:
                if fmt == "text":
                    content = to_text(result)
                elif fmt == "srt":
                    content = to_srt(result)
                elif fmt == "vtt":
                    content = to_vtt(result)
                elif fmt == "json":
                    content = to_json(result)
                else:
                    content = to_text(result)

                output[url] = {
                    "video_id": result.video_id,
                    "language": result.language,
                    "language_code": result.language_code,
                    "is_generated": result.is_generated,
                    "format": fmt,
                    "content": content,
                    "stats": {
                        "word_count": result.stats.word_count,
                        "snippet_count": result.stats.snippet_count,
                        "duration_seconds": result.stats.duration_seconds,
                    },
                }

        return JSONResponse(content=output)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def api_stats(url: str = Query(...)):
    try:
        stats = extractor.get_stats(url)
        return JSONResponse(
            content={
                "word_count": stats.word_count,
                "snippet_count": stats.snippet_count,
                "duration_seconds": stats.duration_seconds,
                "languages_available": stats.languages_available,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
