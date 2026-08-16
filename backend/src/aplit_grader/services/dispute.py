from dataclasses import dataclass

from pydantic import BaseModel

from aplit_grader.schemas.rubric import CriterionResult
from aplit_grader.services.inference import GradingModelClient, GradingModelError
from aplit_grader.services.rubric import (
    MISSING_FIELD_GUIDANCE,
    RUBRIC,
    CriterionId,
    get_rubric_text,
)

_TOOL_NAME = "propose_revised_grade"

_TOOL_DESCRIPTION = (
    "Propose a revised grade for this criterion. Only call this when the teacher has "
    "introduced something you had not already weighed — specific textual evidence, a "
    "rubric point you misapplied, or a reading of the essay you hadn't considered. Do "
    "not call this merely because she restated disagreement without new grounds."
)

# Anti-sycophancy posture, grounded in research rather than intuition (see README's
# 2026-08-16 Decisions log entry for the full citations): sycophancy research
# distinguishes models updating because a user introduced something genuinely worth
# weighing (correct) from models updating purely because a user pushed back (the
# failure mode this project's own business metric already penalizes as
# rubber-stamping). Grade-appeal best practice converges on the same shape — a
# legitimate appeal points to something concrete, not just disagreement.
_INSTRUCTIONS = (
    "You are discussing one rubric criterion's grade with the teacher who assigned "
    "it, after she opened a dispute on it. You are not trying to keep her happy — "
    "you are a second reader defending a score you already gave for a specific, "
    "stated reason.\n\n"
    "Default to holding the score: restate and defend your original reasoning "
    "against the rubric first. Only call propose_revised_grade when she introduces "
    "something you had not already accounted for — a specific sentence or piece of "
    "textual evidence, a rubric point you misapplied, or a reading of the essay you "
    "hadn't considered. Disagreement alone ('I think this deserves a 3') is not "
    "sufficient grounds by itself — if she hasn't pointed to something concrete "
    "yet, ask her to. When she does give you real grounds, say so explicitly in "
    "your reply and then use the tool to revise the score, missing, strengths, "
    "critiques, and reasoning to reflect it. This applies from her very first "
    "message too — if it already contains a concrete argument, act on it "
    "immediately rather than making her repeat herself.\n\n"
) + MISSING_FIELD_GUIDANCE


class _ProposalToolOutput(BaseModel):
    score: int | None
    missing: bool
    strengths: list[str]
    critiques: list[str]
    reasoning: str
    sentence_refs: list[int]


@dataclass
class DisputeTurnResult:
    message: str
    proposal: CriterionResult | None


def _tool_input_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "score": {"type": ["integer", "null"]},
            "missing": {"type": "boolean", "description": MISSING_FIELD_GUIDANCE},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "critiques": {"type": "array", "items": {"type": "string"}},
            "reasoning": {"type": "string"},
            "sentence_refs": {"type": "array", "items": {"type": "integer"}},
        },
        "required": ["score", "missing", "strengths", "critiques", "reasoning", "sentence_refs"],
    }


def _build_system_prompt(
    criterion_id: CriterionId, assignment_prompt: str, essay_text: str, original: CriterionResult
) -> str:
    return (
        f"{_INSTRUCTIONS}\n\n"
        f"Assignment prompt the student was given: {assignment_prompt}\n\n"
        f"Rubric for {RUBRIC[criterion_id].label}:\n{get_rubric_text(criterion_id)}\n\n"
        f"Full essay text:\n{essay_text}\n\n"
        f"The grade currently on record for this criterion — score={original.score}, "
        f"missing={original.missing}:\n"
        f"Reasoning: {original.reasoning}\n"
        f"Strengths: {original.strengths}\n"
        f"Critiques: {original.critiques}\n"
        f"Cited sentence indices: {original.sentence_refs}"
    )


async def run_dispute_turn(
    client: GradingModelClient,
    essay_text: str,
    assignment_prompt: str,
    original: CriterionResult,
    messages: list[dict[str, str]],
) -> DisputeTurnResult:
    result = await client.generate_chat_turn(
        system_prompt=_build_system_prompt(original.criterion_id, assignment_prompt, essay_text, original),
        messages=messages,
        tool_name=_TOOL_NAME,
        tool_description=_TOOL_DESCRIPTION,
        tool_input_schema=_tool_input_schema(),
    )

    proposal: CriterionResult | None = None
    if result.tool_input is not None:
        try:
            parsed = _ProposalToolOutput.model_validate(result.tool_input)
            proposal = CriterionResult(
                criterion_id=original.criterion_id,
                score=parsed.score,
                missing=parsed.missing,
                strengths=parsed.strengths,
                critiques=parsed.critiques,
                reasoning=parsed.reasoning,
                sentence_refs=parsed.sentence_refs,
            )
        except Exception as exc:
            raise GradingModelError(f"Malformed dispute proposal output: {exc}") from exc

    message = result.text.strip()
    if not message:
        if proposal is None:
            raise GradingModelError("Dispute turn produced neither a message nor a proposal")
        message = "Updated the grade to reflect that."

    return DisputeTurnResult(message=message, proposal=proposal)
