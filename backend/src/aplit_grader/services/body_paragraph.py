from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from aplit_grader.schemas.rubric import CriterionResult, EssaySection, Sentence
from aplit_grader.services.inference import GradingModelClient, GradingModelError
from aplit_grader.services.rubric import criteria_for_section, get_rubric_text

_TOOL_NAME = "submit_body_paragraph_grades"

_BASE_SYSTEM_PROMPT = (
    "You are grading one body paragraph of a student AP Lit essay against the provided "
    "rubric, criterion by criterion (Claim, Evidence 1, Reasoning 1, Evidence 2, "
    "Reasoning 2, Synthesis). {framing} You must also write a short coverage_summary "
    "describing what this paragraph argued and which evidence it used — this is passed "
    "forward as context for grading the next section of the essay."
)

_BP1_FRAMING = "Grade this paragraph on how well it supports the thesis."
_BP2_FRAMING = (
    "Grade this paragraph on how well it *completes* the support for the thesis — not "
    "just whether it's relevant, but whether it adds coverage Body Paragraph 1 didn't "
    "already provide. A paragraph that is accurate but redundant with Body Paragraph 1's "
    "coverage should be scored down for that redundancy. Use the Body Paragraph 1 "
    "coverage summary below to judge this."
)


class _BodyCriterionOutput(BaseModel):
    criterion_id: str
    score: int | None
    missing: bool
    strengths: list[str]
    critiques: list[str]
    reasoning: str
    sentence_refs: list[int]


class _BodyParagraphToolOutput(BaseModel):
    criteria: list[_BodyCriterionOutput]
    coverage_summary: str


@dataclass
class BodyParagraphCallResult:
    criteria: list[CriterionResult]
    coverage_summary: str


def _section_for(paragraph_num: Literal[1, 2]) -> EssaySection:
    return "body_1" if paragraph_num == 1 else "body_2"


def _tool_input_schema(criterion_ids: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "criteria": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "criterion_id": {"type": "string", "enum": criterion_ids},
                        "score": {"type": ["integer", "null"]},
                        "missing": {"type": "boolean"},
                        "strengths": {"type": "array", "items": {"type": "string"}},
                        "critiques": {"type": "array", "items": {"type": "string"}},
                        "reasoning": {"type": "string"},
                        "sentence_refs": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": [
                        "criterion_id",
                        "score",
                        "missing",
                        "strengths",
                        "critiques",
                        "reasoning",
                        "sentence_refs",
                    ],
                },
            },
            "coverage_summary": {"type": "string"},
        },
        "required": ["criteria", "coverage_summary"],
    }


def _build_user_prompt(
    essay_text: str,
    sentences: list[Sentence],
    section: EssaySection,
    criterion_ids: list[str],
    extracted_thesis: str,
    assignment_prompt: str,
    prior_coverage_summary: str | None,
) -> str:
    section_sentences = [s for s in sentences if s.section == section]
    sentence_block = "\n".join(f"[{s.sentence_index}] {s.text}" for s in section_sentences) or "(none)"
    rubric_block = "\n\n".join(f"{criterion_id}:\n{get_rubric_text(criterion_id)}" for criterion_id in criterion_ids)

    assignment_prompt_line = (
        f"Assignment prompt the student was given (the Claim criterion's 'answers all "
        f"parts of the prompt' language refers to this):\n{assignment_prompt}"
    )
    parts = [
        assignment_prompt_line,
        f"Extracted thesis:\n{extracted_thesis}",
        f"Rubric for this paragraph's criteria:\n{rubric_block}",
        f"Full essay text (for context):\n{essay_text}",
        f"Sentences identified as this paragraph:\n{sentence_block}",
    ]
    if prior_coverage_summary is not None:
        parts.insert(2, f"Body Paragraph 1 coverage summary:\n{prior_coverage_summary}")

    return "\n\n".join(parts)


async def run_body_paragraph_call(
    client: GradingModelClient,
    essay_text: str,
    sentences: list[Sentence],
    paragraph_num: Literal[1, 2],
    extracted_thesis: str,
    assignment_prompt: str,
    prior_coverage_summary: str | None = None,
) -> BodyParagraphCallResult:
    section = _section_for(paragraph_num)
    criterion_ids = criteria_for_section(section)
    framing = _BP1_FRAMING if paragraph_num == 1 else _BP2_FRAMING

    raw = await client.generate_structured(
        system_prompt=_BASE_SYSTEM_PROMPT.format(framing=framing),
        user_prompt=_build_user_prompt(
            essay_text,
            sentences,
            section,
            criterion_ids,
            extracted_thesis,
            assignment_prompt,
            prior_coverage_summary,
        ),
        tool_name=_TOOL_NAME,
        tool_description="Grade this body paragraph's 6 criteria and summarize its coverage.",
        tool_input_schema=_tool_input_schema(criterion_ids),
    )

    try:
        parsed = _BodyParagraphToolOutput.model_validate(raw)
    except Exception as exc:
        raise GradingModelError(f"Malformed body paragraph output: {exc}") from exc

    returned_ids = {c.criterion_id for c in parsed.criteria}
    if returned_ids != set(criterion_ids):
        raise GradingModelError(
            f"Body paragraph {paragraph_num} call returned unexpected criteria "
            f"(expected {sorted(criterion_ids)}, got {sorted(returned_ids)})"
        )

    try:
        criteria = [
            CriterionResult(
                criterion_id=c.criterion_id,
                score=c.score,
                missing=c.missing,
                strengths=c.strengths,
                critiques=c.critiques,
                reasoning=c.reasoning,
                sentence_refs=c.sentence_refs,
            )
            for c in parsed.criteria
        ]
    except Exception as exc:
        raise GradingModelError(f"Malformed body paragraph criterion: {exc}") from exc

    return BodyParagraphCallResult(criteria=criteria, coverage_summary=parsed.coverage_summary)
