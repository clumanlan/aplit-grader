from aplit_grader.services.rubric import criteria_for_section


def segmentation_response() -> dict:
    return {
        "sentence_sections": [
            {"sentence_index": 0, "section": "thesis"},
            {"sentence_index": 1, "section": "body_1"},
            {"sentence_index": 2, "section": "body_2"},
            {"sentence_index": 3, "section": "conclusion"},
        ],
        "segmentation_notes": None,
    }


def thesis_response() -> dict:
    return {
        "score": 3,
        "missing": False,
        "strengths": ["Clear claim"],
        "critiques": ["Could be sharper"],
        "reasoning": "Held at 3.",
        "sentence_refs": [0],
        "confidence_level": "high",
        "confidence_reason": "explicit thesis stated",
        "extracted_thesis": "Hope is doomed.",
    }


def body_response(section: str, coverage_summary: str) -> dict:
    return {
        "criteria": [
            {
                "criterion_id": criterion_id,
                "score": 3,
                "missing": False,
                "strengths": ["Good detail"],
                "critiques": ["Could go deeper"],
                "reasoning": "Held at 3.",
                "sentence_refs": [1 if section == "body_1" else 2],
            }
            for criterion_id in criteria_for_section(section)
        ],
        "coverage_summary": coverage_summary,
    }


def conclusion_response() -> dict:
    return {
        "score": 3,
        "missing": False,
        "strengths": ["Synthesizes both paragraphs"],
        "critiques": ["Fairly surface-level"],
        "reasoning": "Held at 3.",
        "sentence_refs": [3],
    }


def happy_path_responses() -> list[dict]:
    return [
        segmentation_response(),
        thesis_response(),
        body_response("body_1", "BP1 covers the green light."),
        body_response("body_2", "BP2 covers the mansion."),
        conclusion_response(),
    ]
