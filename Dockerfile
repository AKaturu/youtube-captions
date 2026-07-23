FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY youtube_captions/ youtube_captions/
COPY web/ web/

EXPOSE 8000

CMD ["python", "-m", "web.app"]
