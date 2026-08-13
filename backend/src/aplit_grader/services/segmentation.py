from dataclasses import dataclass

from pydantic import BaseModel

from aplit_grader.schemas.rubric import EssaySection, Sentence
from aplit_grader.services.inference import GradingModelClient, GradingModelError
from aplit_grader.services.sentence_splitter import SplitSentence, split_into_sentences

_TOOL_NAME = "submit_segmentation"

_SYSTEM_PROMPT = (
    "You are segmenting a student AP Lit essay into its structural sections. You will "
    "be given a list of sentences, already split and indexed by the server. For every "
    "sentence index, assign exactly one section: 'thesis', 'body_1', 'body_2', or "
    "'conclusion'. Essays don't reliably have exactly 4 paragraphs — force the essay "
    "into this 4-section shape as best you can, but if you had to make a judgment call "
    "(e.g. merging 3 body paragraphs into 2, or an essay with no clean section breaks), "
    "explain the judgment call in segmentation_notes. Never leave a sentence unassigned."
)


class _SentenceSectionAssignment(BaseModel):
    sentence_index: int
    section: EssaySection


class _SegmentationToolOutput(BaseModel):
    sentence_sections: list[_SentenceSectionAssignment]
    segmentation_notes: str | None = None


@dataclass
class SegmentationResult:
    sentences: list[Sentence]
    segmentation_notes: str | None


def _build_user_prompt(split_sentences: list[SplitSentence]) -> str:
    lines = [f"[{s.index}] {s.text}" for s in split_sentences]
    return "Sentences:\n" + "\n".join(lines)


def _tool_input_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "sentence_sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "sentence_index": {"type": "integer"},
                        "section": {
                            "type": "string",
                            "enum": ["thesis", "body_1", "body_2", "conclusion"],
                        },
                    },
                    "required": ["sentence_index", "section"],
                },
            },
            "segmentation_notes": {"type": ["string", "null"]},
        },
        "required": ["sentence_sections"],
    }


async def run_segmentation_call(client: GradingModelClient, essay_text: str) -> SegmentationResult:
    split_sentences = split_into_sentences(essay_text)

    raw = await client.generate_structured(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(split_sentences),
        tool_name=_TOOL_NAME,
        tool_description="Assign each sentence index to an essay section.",
        tool_input_schema=_tool_input_schema(),
    )

    try:
        parsed = _SegmentationToolOutput.model_validate(raw)
    except Exception as exc:
        raise GradingModelError(f"Malformed segmentation output: {exc}") from exc

    section_by_index = {a.sentence_index: a.section for a in parsed.sentence_sections}
    expected_indices = {s.index for s in split_sentences}
    if set(section_by_index) != expected_indices:
        raise GradingModelError(
            "Segmentation call did not assign a section to every sentence "
            f"(expected {sorted(expected_indices)}, got {sorted(section_by_index)})"
        )

    sentences = [
        Sentence(
            sentence_index=s.index,
            section=section_by_index[s.index],
            span_start=s.span_start,
            span_end=s.span_end,
            text=s.text,
        )
        for s in split_sentences
    ]

    return SegmentationResult(sentences=sentences, segmentation_notes=parsed.segmentation_notes)
