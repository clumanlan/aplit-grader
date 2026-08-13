"""Render a readable HTML report from logged grading results.

Usage:
    uv run python scripts/render_report.py --results-dir grading_results --prompt-file ../sample_prompt.txt -o report.html

Scans --results-dir for */final_result.json (written by ResultLogger, via either
api/routes.py's POST /grade or scripts/zero_shot_eval.py), and renders one section
per essay grouped by rubric section (Thesis / Body ¶1 / Body ¶2 / Conclusion),
distinguishing missing criteria from low scores. A static page for reviewing raw
pipeline output during Phase 0 development — not a replacement for the real
frontend's designed Graded view.
"""

import argparse
import json
from pathlib import Path

from aplit_grader.schemas.requests import GradeResponse
from aplit_grader.services.report import EssayReportData, render_report_html


def _load_reports(results_dir: Path, assignment_prompt: str) -> list[EssayReportData]:
    reports = []
    for final_result_path in sorted(results_dir.glob("*/final_result.json")):
        data = json.loads(final_result_path.read_text())
        result = GradeResponse.model_validate(data["result"])
        reports.append(
            EssayReportData(
                essay_name=final_result_path.parent.name,
                essay_text=data["essay_text"],
                assignment_prompt=assignment_prompt,
                result=result,
            )
        )
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir", type=Path, required=True, help="Directory containing */final_result.json"
    )
    parser.add_argument(
        "--prompt-file", type=Path, required=True, help="Assignment prompt shown for context"
    )
    parser.add_argument("--output", "-o", type=Path, default=Path("report.html"))
    args = parser.parse_args()

    reports = _load_reports(args.results_dir, args.prompt_file.read_text().strip())
    if not reports:
        print(f"No final_result.json files found under {args.results_dir}")
        return

    args.output.write_text(render_report_html(reports))
    print(f"Wrote {len(reports)} essay report(s) to {args.output}")


if __name__ == "__main__":
    main()
