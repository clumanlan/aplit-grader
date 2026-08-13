"""Run the 5-call grading pipeline against real essays and report per-essay,
per-step latency, to sanity-check the ~60-90s budget and produce the "Claude API
zero-shot" baseline (see README.md's Expected lift over heuristic baseline).

Usage:
    uv run python scripts/zero_shot_eval.py --essays-dir path/to/essays --prompt-file path/to/prompt.txt

Each essay is a .txt file; the filename stem is used as the essay's name in the
report and result logs. All essays in a directory are graded against the same
assignment prompt (matching README's session model — one prompt per batch of
essays), read from --prompt-file. Results are logged via LocalResultLogger by
default (one directory per essay run, containing each of the 5 pipeline calls'
raw JSON output plus a final_result.json) — matching CLAUDE.md's Phase 0 scope
(S3-logged results, no database).
"""

import argparse
import asyncio
from pathlib import Path

from aplit_grader.services.eval import format_report, run_eval
from aplit_grader.services.inference import AnthropicGradingClient
from aplit_grader.storage.result_logger import LocalResultLogger


def _load_essays_from_dir(essays_dir: Path) -> list[tuple[str, str]]:
    return [(path.stem, path.read_text()) for path in sorted(essays_dir.glob("*.txt"))]


async def _run(essays_dir: Path, prompt_file: Path, output_dir: Path, model: str) -> None:
    essays = _load_essays_from_dir(essays_dir)
    if not essays:
        print(f"No .txt essays found in {essays_dir}")
        return

    assignment_prompt = prompt_file.read_text().strip()
    if not assignment_prompt:
        print(f"{prompt_file} is empty — the assignment prompt is required to grade Thesis/Claim.")
        return

    client = AnthropicGradingClient(model=model)
    logger = LocalResultLogger(base_dir=output_dir)

    print(f"Grading {len(essays)} essay(s) with model={model}, prompt from {prompt_file}...")
    results = await run_eval(client, logger, essays, assignment_prompt)
    print(format_report(results))
    print(f"\nResults logged under {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--essays-dir", type=Path, required=True, help="Directory of .txt essay files")
    parser.add_argument(
        "--prompt-file",
        type=Path,
        required=True,
        help="Text file containing the assignment prompt, shared across all essays in --essays-dir",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("./grading_results"), help="Where to log results"
    )
    parser.add_argument("--model", type=str, default="claude-sonnet-5", help="Model version to use")
    args = parser.parse_args()

    asyncio.run(_run(args.essays_dir, args.prompt_file, args.output_dir, args.model))


if __name__ == "__main__":
    main()
