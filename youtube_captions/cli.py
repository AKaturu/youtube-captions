from __future__ import annotations

import argparse
import sys
from pathlib import Path

from youtube_captions.extractor import CaptionExtractor
from youtube_captions.formatters import to_json, to_srt, to_text, to_vtt

FORMAT_EXT = {
    "text": ".txt",
    "srt": ".srt",
    "vtt": ".vtt",
    "json": ".json",
}


def _output(content: str, args: argparse.Namespace, video_id: str) -> None:
    if args.output:
        path = Path(args.output)
        if path.is_dir():
            ext = FORMAT_EXT[args.format]
            path = path / f"{video_id}{ext}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Saved: {path}")
    else:
        print(content)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="yt-captions",
        description="Extract captions from YouTube videos",
    )
    parser.add_argument(
        "urls",
        nargs="+",
        help="YouTube URL(s) or video ID(s)",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["text", "srt", "vtt", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        metavar="PATH",
        help="Output file or directory (default: stdout)",
    )
    parser.add_argument(
        "-l", "--language",
        default=None,
        help="Preferred language code (default: en)",
    )
    parser.add_argument(
        "-t", "--translate",
        default=None,
        metavar="LANG",
        help="Translate transcript to target language",
    )
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="List available languages and exit",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show transcript statistics",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching",
    )
    parser.add_argument(
        "--cookie",
        default=None,
        metavar="FILE",
        help="Path to Netscape-format cookie file (for YouTube auth/IP ban bypass)",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        metavar="URL",
        help="Proxy URL: http://, https://, socks4://, socks5://, socks5h://",
    )

    args = parser.parse_args()
    extractor = CaptionExtractor(cookie_path=args.cookie, proxy_url=args.proxy)

    if args.list_languages:
        for url in args.urls:
            try:
                infos = extractor.list_available(url)
                video_id = CaptionExtractor.extract_video_id(url)
                print(f"\n  {video_id}:")
                for info in infos:
                    kind = "auto" if info.is_generated else "manual"
                    print(f"    {info.language_code:8s}  {info.language}  [{kind}]")
            except Exception as e:
                print(f"  Error: {e}", file=sys.stderr)
        return

    if args.stats:
        for url in args.urls:
            try:
                stats = extractor.get_stats(url)
                video_id = CaptionExtractor.extract_video_id(url)
                print(f"\n  {video_id}:")
                print(f"    Words:             {stats.word_count}")
                print(f"    Segments:          {stats.snippet_count}")
                print(f"    Duration:          {stats.duration_seconds:.1f}s")
                print(f"    Languages:         {stats.languages_available}")
            except Exception as e:
                print(f"  Error: {e}", file=sys.stderr)
        return

    formatter_map = {
        "text": to_text,
        "srt": to_srt,
        "vtt": to_vtt,
        "json": to_json,
    }
    formatter = formatter_map[args.format]

    for url in args.urls:
        try:
            transcript = extractor.extract(
                url,
                language=args.language,
                translate_to=args.translate,
                use_cache=not args.no_cache,
            )
            content = formatter(transcript)
            _output(content, args, transcript.video_id)
        except Exception as e:
            print(f"Error ({url}): {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
