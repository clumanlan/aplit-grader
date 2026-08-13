from dataclasses import dataclass

from pydantic import BaseModel

from aplit_grader.schemas.rubric import ConfidenceLevel, CriterionResult, Sentence
from aplit_grader.services.inference import GradingModelClient, GradingModelError
from aplit_grader.services.rubric import get_rubric_text

_TOOL_NAME = "submit_thesis_grade"

_SYSTEM_PROMPT = (
    "You are grading the Thesis criterion of a student AP Lit essay against the "
    "provided rubric. You are also responsible for extracting the essay's stated "
    "argument as context for later grading calls: if a thesis is explicitly stated, "
    "extract it; if it is only implied across several sentences, reconstruct your best "
    "interpretation of it; if no argument is discernible at all, still provide your "
    "best reconstruction based on the essay's overall content so downstream grading "
    "has something to work against. Report your confidence in this thesis "
    "identification as a bucket (high/medium/low) with a short reason — do not "
    "self-report a numeric confidence score."
)


class _ThesisToolOutput(BaseModel):
    score: int | None
    missing: bool
    strengths: list[str]
    critiques: list[str]
    reasoning: str
    sentence_refs: list[int]
    confidence_level: ConfidenceLevel
    confidence_reason: str
    extracted_thesis: str


@dataclass
class ThesisCallResult:
    criterion: CriterionResult
    extracted_thesis: str


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
            "confidence_level": {"type": "string", "enum": ["high", "medium", "low"]},
            "confidence_reason": {"type": "string"},
            "extracted_thesis": {"type": "string"},
        },
        "required": [
            "score",
            "missing",
            "strengths",
            "critiques",
            "reasoning",
            "sentence_refs",
            "confidence_level",
            "confidence_reason",
            "extracted_thesis",
        ],
    }


def _build_user_prompt(essay_text: str, sentences: list[Sentence], assignment_prompt: str) -> str:
    thesis_sentences = [s for s in sentences if s.section == "thesis"]
    thesis_block = "\n".join(f"[{s.sentence_index}] {s.text}" for s in thesis_sentences) or "(none)"

    return (
        f"Assignment prompt the student was given (the rubric's 'answers all parts of the "
        f"prompt' language refers to this):\n{assignment_prompt}\n\n"
        f"Rubric for Thesis:\n{get_rubric_text('thesis')}\n\n"
        f"Full essay text (for context if the thesis needs to be reconstructed):\n{essay_text}\n\n"
        f"Sentences identified as the thesis section:\n{thesis_block}"
    )


async def run_thesis_call(
    client: GradingModelClient, essay_text: str, sentences: list[Sentence], assignment_prompt: str
) -> ThesisCallResult:
    raw = await client.generate_structured(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(essay_text, sentences, assignment_prompt),
        tool_name=_TOOL_NAME,
        tool_description="Grade the Thesis criterion and extract the essay's argument.",
        tool_input_schema=_tool_input_schema(),
    )

    try:
        parsed = _ThesisToolOutput.model_validate(raw)
        criterion = CriterionResult(
            criterion_id="thesis",
            score=parsed.score,
            missing=parsed.missing,
            strengths=parsed.strengths,
            critiques=parsed.critiques,
            reasoning=parsed.reasoning,
            sentence_refs=parsed.sentence_refs,
            confidence_level=parsed.confidence_level,
            confidence_reason=parsed.confidence_reason,
        )
    except Exception as exc:
        raise GradingModelError(f"Malformed thesis call output: {exc}") from exc

    return ThesisCallResult(criterion=criterion, extracted_thesis=parsed.extracted_thesis)
