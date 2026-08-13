from aplit_grader.services.rubric import RUBRIC, criteria_for_section, get_rubric_text


def test_rubric_has_exactly_fourteen_criteria():
    assert len(RUBRIC) == 14


def test_rubric_has_no_duplicate_criterion_ids():
    ids = list(RUBRIC.keys())
    assert len(ids) == len(set(ids))


def test_rubric_group_counts_match_essay_structure():
    counts: dict[str, int] = {}
    for criterion in RUBRIC.values():
        counts[criterion.group] = counts.get(criterion.group, 0) + 1

    assert counts == {
        "Thesis": 1,
        "Body ¶1": 6,
        "Body ¶2": 6,
        "Conclusion": 1,
    }


def test_every_criterion_has_non_empty_label_group_and_score_band_text():
    for criterion_id, criterion in RUBRIC.items():
        assert criterion.label.strip(), f"{criterion_id} missing label"
        assert criterion.group.strip(), f"{criterion_id} missing group"
        assert criterion.score_band_text.strip(), f"{criterion_id} missing score_band_text"


def test_criteria_for_section_returns_body_1_criteria_in_reading_order():
    assert criteria_for_section("body_1") == [
        "bp1-claim",
        "bp1-evidence-1",
        "bp1-reasoning-1",
        "bp1-evidence-2",
        "bp1-reasoning-2",
        "bp1-synthesis",
    ]


def test_criteria_for_section_returns_single_criterion_for_thesis():
    assert criteria_for_section("thesis") == ["thesis"]


def test_get_rubric_text_returns_the_criterions_score_band_text():
    assert get_rubric_text("bp1-evidence-1") == RUBRIC["bp1-evidence-1"].score_band_text


def test_no_criterion_uses_placeholder_text():
    for criterion_id, criterion in RUBRIC.items():
        assert "PLACEHOLDER" not in criterion.score_band_text, (
            f"{criterion_id} still has placeholder rubric text"
        )


def test_thesis_and_claim_criteria_share_identical_real_rubric_text():
    # Source: aplitrubric.pdf, "Thesis Statement" / "Claim" rows — identical wording
    # across the Thesis Statement table and both Body Paragraph Claim rows.
    text = RUBRIC["thesis"].score_band_text
    assert "Shows you thought deeply about the question AND text" in text
    assert "does not give an argument (merely facts or summary)" in text
    assert RUBRIC["bp1-claim"].score_band_text == text
    assert RUBRIC["bp2-claim"].score_band_text == text


def test_evidence_criteria_share_identical_real_rubric_text():
    # Source: aplitrubric.pdf, "Evidence" rows — identical across BP1/BP2, both instances.
    text = RUBRIC["bp1-evidence-1"].score_band_text
    assert "the direct quote fully supports your claim" in text
    assert "Evidence is entirely unrelated to the claim" in text
    assert RUBRIC["bp1-evidence-2"].score_band_text == text
    assert RUBRIC["bp2-evidence-1"].score_band_text == text
    assert RUBRIC["bp2-evidence-2"].score_band_text == text


def test_reasoning_criteria_share_identical_real_rubric_text():
    # Source: aplitrubric.pdf, "Reasoning" rows — identical across BP1/BP2, both instances.
    text = RUBRIC["bp1-reasoning-1"].score_band_text
    assert "Identifies the significant aspects of the evidence" in text
    assert "Incomprehensible" in text
    assert RUBRIC["bp1-reasoning-2"].score_band_text == text
    assert RUBRIC["bp2-reasoning-1"].score_band_text == text
    assert RUBRIC["bp2-reasoning-2"].score_band_text == text


def test_synthesis_criteria_share_identical_real_rubric_text():
    # Source: aplitrubric.pdf, "Synthesis" rows — identical across BP1/BP2.
    text = RUBRIC["bp1-synthesis"].score_band_text
    assert "Connections are made between all points in the paragraph" in text
    assert RUBRIC["bp2-synthesis"].score_band_text == text


def test_body_2_synthesis_text_has_no_invented_redundancy_language():
    # The pipeline's "avoid redundancy with BP1" framing (README's chosen framing,
    # 2026-08-12) is a prompt-building instruction for the Body 2 call, not part of
    # the teacher's actual rubric text — it must not be baked into the rubric data.
    text = RUBRIC["bp2-synthesis"].score_band_text
    assert "redundan" not in text.lower()
    assert "¶1" not in text


def test_conclusion_text_is_distinct_from_synthesis_paragraph_level_wording():
    # Source: aplitrubric.pdf "Conclusion" row — same pattern as Synthesis but scoped
    # to "all paragraphs" rather than "all points in the paragraph".
    text = RUBRIC["conclusion"].score_band_text
    assert "Connections are made between all paragraphs" in text
    assert text != RUBRIC["bp1-synthesis"].score_band_text
