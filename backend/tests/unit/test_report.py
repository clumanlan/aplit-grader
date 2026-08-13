from aplit_grader.schemas.requests import GradeResponse
from aplit_grader.schemas.rubric import CriterionResult, Sentence
from aplit_grader.services.report import EssayReportData, render_report_html
from aplit_grader.services.rubric import RUBRIC


def _criterion(criterion_id: str, **overrides) -> CriterionResult:
    defaults = {
        "criterion_id": criterion_id,
        "score": 3,
        "missing": False,
        "strengths": ["A strength"],
        "critiques": ["A critique"],
        "reasoning": "Some reasoning text.",
        "sentence_refs": [],
    }
    defaults.update(overrides)
    return CriterionResult(**defaults)


def _full_result(sentences: list[Sentence] | None = None, **criterion_overrides: dict) -> GradeResponse:
    criteria = [
        _criterion(criterion_id, **criterion_overrides.get(criterion_id, {})) for criterion_id in RUBRIC
    ]
    return GradeResponse(criteria=criteria, sentences=sentences or [], segmentation_notes=None)


def test_renders_essay_name_and_text():
    report = EssayReportData(
        essay_name="essay_1",
        essay_text="Once upon a time in Gatsby's mansion.",
        assignment_prompt="Analyze the symbolism.",
        result=_full_result(),
    )

    html = render_report_html([report])

    assert "essay_1" in html
    assert "Once upon a time in Gatsby's mansion." in html
    assert "Analyze the symbolism." in html


def test_renders_a_scored_criterions_content():
    report = EssayReportData(
        essay_name="essay_1",
        essay_text="...",
        assignment_prompt="...",
        result=_full_result(
            thesis={
                "score": 3,
                "strengths": ["Clear claim"],
                "critiques": ["Could be sharper"],
                "reasoning": "Held at 3 because it's accurate but wordy.",
            }
        ),
    )

    html = render_report_html([report])

    assert "Thesis" in html
    assert "Clear claim" in html
    assert "Could be sharper" in html
    assert "Held at 3 because it's accurate but wordy." in html


def test_renders_all_fourteen_criteria_grouped_by_section():
    report = EssayReportData(
        essay_name="essay_1", essay_text="...", assignment_prompt="...", result=_full_result()
    )

    html = render_report_html([report])

    # Group headers (h3.group-title) present, in essay reading order — searching
    # the group-title markup specifically, since criterion labels (e.g. the
    # "Conclusion" criterion's own label) can otherwise collide with group names.
    def group_title(name: str) -> str:
        return f'class="group-title">{name}</h3>'

    assert (
        html.index(group_title("Thesis"))
        < html.index(group_title("Body ¶1"))
        < html.index(group_title("Body ¶2"))
        < html.index(group_title("Conclusion"))
    )
    # Spot-check a criterion from each group renders its label.
    for label in ("Evidence 1", "Reasoning 2", "Synthesis", "Claim"):
        assert label in html


def test_renders_a_missing_criterion_distinctly_not_as_a_score():
    report = EssayReportData(
        essay_name="essay_1",
        essay_text="...",
        assignment_prompt="...",
        result=_full_result(
            **{
                "bp1-reasoning-1": {
                    "score": None,
                    "missing": True,
                    "strengths": [],
                    "critiques": ["Nothing to point to yet"],
                    "reasoning": "No sentences addressed this criterion.",
                }
            }
        ),
    )

    html = render_report_html([report])

    assert "Nothing to point to yet" in html
    # Missing is marked distinctly — a "!" badge and a "What's missing" heading,
    # not a numeric score (mirrors UI-DESIGN-HANDOFF.md's missing-criterion spec).
    assert 'class="badge tier-missing">!</span>' in html
    assert "What's missing" in html


def test_renders_multiple_essays_in_separate_sections():
    reports = [
        EssayReportData(
            essay_name="essay_1", essay_text="First essay.", assignment_prompt="...", result=_full_result()
        ),
        EssayReportData(
            essay_name="essay_2", essay_text="Second essay.", assignment_prompt="...", result=_full_result()
        ),
    ]

    html = render_report_html(reports)

    assert "essay_1" in html
    assert "essay_2" in html
    assert "First essay." in html
    assert "Second essay." in html


def test_tags_each_sentence_inline_with_its_section_and_preserves_gaps_between_them():
    sentence_0_text = "The green light shows hope."
    sentence_1_text = "Gatsby buys a mansion."
    sentence_2_text = "He waits by the water."
    essay_text = f"{sentence_0_text}\n\n{sentence_1_text} {sentence_2_text}"

    def _sentence(index: int, section: str, text: str) -> Sentence:
        start = essay_text.index(text)
        return Sentence(
            sentence_index=index, section=section, span_start=start, span_end=start + len(text), text=text
        )

    sentences = [
        _sentence(0, "thesis", sentence_0_text),
        _sentence(1, "body_1", sentence_1_text),
        _sentence(2, "body_1", sentence_2_text),
    ]
    report = EssayReportData(
        essay_name="essay_1",
        essay_text=essay_text,
        assignment_prompt="...",
        result=_full_result(sentences=sentences),
    )

    html = render_report_html([report])

    # No criterion cites these sentences (sentence_refs=[] everywhere in
    # _full_result's default), so tags fall back to the generic section label.
    # Tags appear, in reading order, immediately before their sentence's text.
    thesis_tag_pos = html.index(">Thesis<", html.index("essay-text"))
    body1_first_tag_pos = html.index(">Body ¶1<", thesis_tag_pos)
    assert thesis_tag_pos < html.index("The green light shows hope.") < body1_first_tag_pos
    assert body1_first_tag_pos < html.index("Gatsby buys a mansion.")
    # The paragraph break between sentence 0 and sentence 1 (essay_text[28:30] ==
    # "\n\n") is preserved literally in the markup, not collapsed — the tagging
    # must not just concatenate sentence.text values, which would lose it.
    between = html[html.index("The green light shows hope.") : html.index("Gatsby buys a mansion.")]
    assert "\n\n" in between


def test_sentence_cited_by_a_criterion_shows_that_criterions_label_not_the_section():
    claim_text = "Brooks uses 'we' to include everyone."
    evidence_text = "'We are things of dry hours,' she writes."
    essay_text = f"{claim_text} {evidence_text}"

    def _sentence(index: int, section: str, text: str) -> Sentence:
        start = essay_text.index(text)
        return Sentence(
            sentence_index=index, section=section, span_start=start, span_end=start + len(text), text=text
        )

    sentences = [
        _sentence(0, "body_1", claim_text),
        _sentence(1, "body_1", evidence_text),
    ]
    report = EssayReportData(
        essay_name="essay_1",
        essay_text=essay_text,
        assignment_prompt="...",
        result=_full_result(
            sentences=sentences,
            **{
                "bp1-claim": {"sentence_refs": [0], "score": 4},
                "bp1-evidence-1": {"sentence_refs": [1], "score": 3},
            },
        ),
    )

    html = render_report_html([report])

    essay_text_start = html.index('<p class="essay-text">')
    essay_text_end = html.index("</p>", essay_text_start)
    tagged_essay_html = html[essay_text_start:essay_text_end]

    claim_tag_pos = tagged_essay_html.index(">Claim<")
    evidence_tag_pos = tagged_essay_html.index(">Evidence 1<")
    assert claim_tag_pos < tagged_essay_html.index(claim_text)
    assert evidence_tag_pos < tagged_essay_html.index(evidence_text)
    # The generic "Body ¶1" section label should NOT appear as a per-sentence
    # tag here — every sentence is cited by a specific criterion, so the
    # criterion's own label (colored by that criterion's score tier) wins.
    assert "Body ¶1" not in tagged_essay_html


def test_consecutive_sentences_citing_the_same_criterion_tag_only_once_at_the_start():
    sentence_texts = [
        "The kitchen light flickers.",
        "It hums a low, constant note.",
        "No one turns it off.",
    ]
    essay_text = " ".join(sentence_texts)

    def _sentence(index: int, text: str) -> Sentence:
        start = essay_text.index(text)
        return Sentence(
            sentence_index=index,
            section="body_1",
            span_start=start,
            span_end=start + len(text),
            text=text,
        )

    sentences = [_sentence(i, t) for i, t in enumerate(sentence_texts)]
    report = EssayReportData(
        essay_name="essay_1",
        essay_text=essay_text,
        assignment_prompt="...",
        result=_full_result(
            sentences=sentences,
            **{"bp1-evidence-2": {"sentence_refs": [0, 1, 2], "score": 3}},
        ),
    )

    html = render_report_html([report])

    essay_text_start = html.index('<p class="essay-text">')
    essay_text_end = html.index("</p>", essay_text_start)
    tagged_essay_html = html[essay_text_start:essay_text_end]

    # The tag appears exactly once, before the first sentence of the run —
    # not repeated before sentences 2 and 3, which cite the same criterion.
    assert tagged_essay_html.count(">Evidence 2<") == 1
    tag_pos = tagged_essay_html.index(">Evidence 2<")
    assert tag_pos < tagged_essay_html.index(sentence_texts[0])
    assert tagged_essay_html.index(sentence_texts[0]) < tagged_essay_html.index(sentence_texts[1])
    assert tagged_essay_html.index(sentence_texts[1]) < tagged_essay_html.index(sentence_texts[2])
