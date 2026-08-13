from pydantic import BaseModel

from aplit_grader.schemas.rubric import CriterionResult, Sentence
from aplit_grader.services.inference import GradingModelClient, GradingModelError
from aplit_grader.services.rubric import get_rubric_text

_TOOL_NAME = "submit_conclusion_grade"

_SYSTEM_PROMPT = (
    "You are grading the Conclusion criterion of a student AP Lit essay against the "
    "provided rubric. Grade it as a synthesis of both body paragraphs: does it draw "
    "real connections between what Body Paragraph 1 and Body Paragraph 2 each argued, "
    "and arrive at a final insight, rather than simply restating the thesis or "
    "summarizing the paragraphs."
)


class _ConclusionToolOutput(BaseModel):
    score: int | None
    missing: bool
    strengths: list[str]
    critiques: list[str]
    reasoning: str
    sentence_refs: list[int]


def _tool_input_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "score": {"type": ["integer", "null"]},
            "missing": {"type": "boolean"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "critiques": {"type": "array", "items": {"type": "string"}},
            "reasoning": {"type": "string"},
            "sentence_refs": {"type": "array", "items": {"type": "integer"}},
        },
        "required": ["score", "missing", "strengths", "critiques", "reasoning", "sentence_refs"],
    }


def _build_user_prompt(
    essay_text: str,
    sentences: list[Sentence],
    extracted_thesis: str,
    body1_coverage_summary: str,
    body2_coverage_summary: str,
    assignment_prompt: str,
) -> str:
    conclusion_sentences = [s for s in sentences if s.section == "conclusion"]
    sentence_block = "\n".join(f"[{s.sentence_index}] {s.text}" for s in conclusion_sentences) or "(none)"

    return (
        f"Assignment prompt the student was given:\n{assignment_prompt}\n\n"
        f"Rubric for Conclusion:\n{get_rubric_text('conclusion')}\n\n"
        f"Extracted thesis:\n{extracted_thesis}\n\n"
        f"Body Paragraph 1 coverage summary:\n{body1_coverage_summary}\n\n"
        f"Body Paragraph 2 coverage summary:\n{body2_coverage_summary}\n\n"
        f"Full essay text (for context):\n{essay_text}\n\n"
        f"Sentences identified as the conclusion:\n{sentence_block}"
    )


async def run_conclusion_call(
    client: GradingModelClient,
    essay_text: str,
    sentences: list[Sentence],
    extracted_thesis: str,
    body1_coverage_summary: str,
    body2_coverage_summary: str,
    assignment_prompt: str,
) -> CriterionResult:
    raw = await client.generate_structured(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(
            essay_text,
            sentences,
            extracted_thesis,
            body1_coverage_summary,
            body2_coverage_summary,
            assignment_prompt,
        ),
        tool_name=_TOOL_NAME,
        tool_description="Grade the Conclusion criterion as a synthesis of both body paragraphs.",
        tool_input_schema=_tool_input_schema(),
    )

    try:
        parsed = _ConclusionToolOutput.model_validate(raw)
        return CriterionResult(
            criterion_id="conclusion",
            score=parsed.score,
            missing=parsed.missing,
            strengths=parsed.strengths,
            critiques=parsed.critiques,
            reasoning=parsed.reasoning,
            sentence_refs=parsed.sentence_refs,
        )
    except Exception as exc:
        raise GradingModelError(f"Malformed conclusion call output: {exc}") from exc
