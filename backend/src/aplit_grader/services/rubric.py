from dataclasses import dataclass
from typing import Literal

CriterionId = Literal[
    "thesis",
    "bp1-claim",
    "bp1-evidence-1",
    "bp1-reasoning-1",
    "bp1-evidence-2",
    "bp1-reasoning-2",
    "bp1-synthesis",
    "bp2-claim",
    "bp2-evidence-1",
    "bp2-reasoning-1",
    "bp2-evidence-2",
    "bp2-reasoning-2",
    "bp2-synthesis",
    "conclusion",
]

Group = Literal["Thesis", "Body ¶1", "Body ¶2", "Conclusion"]

# Source: aplitrubric.pdf ("Essay Rubric for AP Lit"). The real rubric repeats identical
# score-band text across every instance of a given criterion type (e.g. all four Evidence
# rows are word-for-word identical) — these constants mirror that, one block per type,
# rather than duplicating (and risking drift on) the same text per criterion instance.

# Used by: thesis, bp1-claim, bp2-claim (PDF's "Thesis Statement" and "Claim" rows match).
_THESIS_STATEMENT_TEXT = (
    "4: Shows you thought deeply about the question AND text; answers all parts of the "
    "prompt; clear and easy to understand; concise.\n"
    "3: Too long, too much detail OR vague, lacking specificity OR accurate but poorly "
    "phrased.\n"
    "2: Only answers part of the prompt OR is inaccurate due to a misinterpretation.\n"
    "1: Does not address any part of the prompt; does not give an argument (merely facts "
    "or summary); does not make sense."
)

# Used by: bp1-evidence-1, bp1-evidence-2, bp2-evidence-1, bp2-evidence-2.
_EVIDENCE_TEXT = (
    "4: You have a direct quote (or a specific paraphrase if the situation is "
    "appropriate); the direct quote fully supports your claim; your direct quote has "
    "the context needed to understand the quote.\n"
    "3: No context, or not enough information given to make the context clear OR too "
    "long, difficult to identify which parts are significant.\n"
    "2: Paraphrased when a direct quote would be more appropriate OR tangential to the "
    "claim (related to the claim, but does not directly prove it).\n"
    "1: Evidence is entirely unrelated to the claim OR evidence is paraphrased poorly, "
    "thus too confusing to contribute to the argument."
)

# Used by: bp1-reasoning-1, bp1-reasoning-2, bp2-reasoning-1, bp2-reasoning-2.
_REASONING_TEXT = (
    "4: Identifies the significant aspects of the evidence; provides in-depth insight "
    "into the text & deepens readers' understanding; explains how the evidence proves "
    "the claim.\n"
    "3: Broad analysis of the text, not a specific analysis of the quote OR accurate, "
    "but surface-level OR accurate but not developed.\n"
    "2: Inaccurate OR too vague to give insight OR accurate but does not relate to "
    "claim.\n"
    "1: Incomprehensible OR wholly unrelated to evidence and claim OR evidence is "
    "summarized."
)

# Used by: bp1-synthesis, bp2-synthesis. NOTE: the real rubric text is identical for
# both — it says nothing about avoiding redundancy with Body 1. That instruction is a
# pipeline prompt-building concern for the Body 2 call (README's chosen framing,
# 2026-08-12), not part of the teacher's actual rubric, and must not be added here.
_SYNTHESIS_TEXT = (
    "4: Connections are made between all points in the paragraph; arrives at a final "
    "conclusion about the text based on synthesis; shows in-depth insight about text.\n"
    "3: Connections are present but surface-level OR conclusion is present but "
    "surface-level.\n"
    "2: Synthesis or conclusion is missing, inaccurate, or unrelated to paragraph OR "
    "too vague.\n"
    "1: All parts are inaccurate OR arguments are merely restated or summarized."
)

# Used by: conclusion. Same pattern as Synthesis but scoped to "all paragraphs" rather
# than "all points in the paragraph".
_CONCLUSION_TEXT = (
    "4: Connections are made between all paragraphs; arrives at a final conclusion "
    "about the text based on synthesis; shows in-depth insight about text.\n"
    "3: Connections are present but surface-level OR conclusion is present but "
    "surface-level.\n"
    "2: Synthesis or conclusion is missing, inaccurate, or unrelated to paragraph OR "
    "too vague.\n"
    "1: All parts are inaccurate OR arguments are merely restated or summarized."
)


@dataclass(frozen=True)
class RubricCriterion:
    label: str
    group: Group
    score_band_text: str


RUBRIC: dict[CriterionId, RubricCriterion] = {
    "thesis": RubricCriterion(
        label="Thesis",
        group="Thesis",
        score_band_text=_THESIS_STATEMENT_TEXT,
    ),
    "bp1-claim": RubricCriterion(
        label="Claim",
        group="Body ¶1",
        score_band_text=_THESIS_STATEMENT_TEXT,
    ),
    "bp1-evidence-1": RubricCriterion(
        label="Evidence 1",
        group="Body ¶1",
        score_band_text=_EVIDENCE_TEXT,
    ),
    "bp1-reasoning-1": RubricCriterion(
        label="Reasoning 1",
        group="Body ¶1",
        score_band_text=_REASONING_TEXT,
    ),
    "bp1-evidence-2": RubricCriterion(
        label="Evidence 2",
        group="Body ¶1",
        score_band_text=_EVIDENCE_TEXT,
    ),
    "bp1-reasoning-2": RubricCriterion(
        label="Reasoning 2",
        group="Body ¶1",
        score_band_text=_REASONING_TEXT,
    ),
    "bp1-synthesis": RubricCriterion(
        label="Synthesis",
        group="Body ¶1",
        score_band_text=_SYNTHESIS_TEXT,
    ),
    "bp2-claim": RubricCriterion(
        label="Claim",
        group="Body ¶2",
        score_band_text=_THESIS_STATEMENT_TEXT,
    ),
    "bp2-evidence-1": RubricCriterion(
        label="Evidence 1",
        group="Body ¶2",
        score_band_text=_EVIDENCE_TEXT,
    ),
    "bp2-reasoning-1": RubricCriterion(
        label="Reasoning 1",
        group="Body ¶2",
        score_band_text=_REASONING_TEXT,
    ),
    "bp2-evidence-2": RubricCriterion(
        label="Evidence 2",
        group="Body ¶2",
        score_band_text=_EVIDENCE_TEXT,
    ),
    "bp2-reasoning-2": RubricCriterion(
        label="Reasoning 2",
        group="Body ¶2",
        score_band_text=_REASONING_TEXT,
    ),
    "bp2-synthesis": RubricCriterion(
        label="Synthesis",
        group="Body ¶2",
        score_band_text=_SYNTHESIS_TEXT,
    ),
    "conclusion": RubricCriterion(
        label="Conclusion",
        group="Conclusion",
        score_band_text=_CONCLUSION_TEXT,
    ),
}

Section = Literal["thesis", "body_1", "body_2", "conclusion"]

_SECTION_CRITERIA: dict[Section, list[CriterionId]] = {
    "thesis": ["thesis"],
    "body_1": [
        "bp1-claim",
        "bp1-evidence-1",
        "bp1-reasoning-1",
        "bp1-evidence-2",
        "bp1-reasoning-2",
        "bp1-synthesis",
    ],
    "body_2": [
        "bp2-claim",
        "bp2-evidence-1",
        "bp2-reasoning-1",
        "bp2-evidence-2",
        "bp2-reasoning-2",
        "bp2-synthesis",
    ],
    "conclusion": ["conclusion"],
}


def criteria_for_section(section: Section) -> list[CriterionId]:
    return list(_SECTION_CRITERIA[section])


def get_rubric_text(criterion_id: CriterionId) -> str:
    return RUBRIC[criterion_id].score_band_text
