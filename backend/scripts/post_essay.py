"""Post a real essay + assignment prompt to a running POST /grade server.

Reads both from plain .txt files and lets httpx/json handle all JSON escaping
(quotes, newlines, etc.) — avoids the "Invalid control character" / JSON decode
errors that come from pasting raw essay text directly into curl -d or Swagger's
raw JSON textarea.

Usage:
    uv run python scripts/post_essay.py --essay-file path/to/essay.txt --prompt-file path/to/prompt.txt
"""

import argparse
import json
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--essay-file", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--student-name", type=str, default="Test Student")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8000/grade")
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    payload = {
        "essay_text": args.essay_file.read_text(),
        "assignment_prompt": args.prompt_file.read_text(),
        "student_name": args.student_name,
    }

    print(f"POST {args.url} ...")
    response = httpx.post(args.url, json=payload, timeout=args.timeout)
    print(f"status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
