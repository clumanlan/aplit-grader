import html
from dataclasses import dataclass

from aplit_grader.schemas.requests import GradeResponse
from aplit_grader.schemas.rubric import CriterionResult, Sentence
from aplit_grader.services.rubric import RUBRIC, criteria_for_section


def _esc(text: str) -> str:
    # No user content in this module ever lands in an HTML attribute, only
    # element text — quote=False avoids noisy &#x27; for ordinary apostrophes
    # in essay text/reasoning while still escaping <, >, & for safety.
    return html.escape(text, quote=False)


@dataclass
class EssayReportData:
    essay_name: str
    essay_text: str
    assignment_prompt: str
    result: GradeResponse


_SECTION_ORDER = [
    ("thesis", "Thesis"),
    ("body_1", "Body ¶1"),
    ("body_2", "Body ¶2"),
    ("conclusion", "Conclusion"),
]
_SECTION_LABELS = dict(_SECTION_ORDER)


def _tier_class(criterion: CriterionResult) -> str:
    if criterion.missing:
        return "tier-missing"
    if criterion.score == 4:
        return "tier-4"
    if criterion.score == 3:
        return "tier-3"
    return "tier-12"


def _sentence_criterion_map(criteria: list[CriterionResult]) -> dict[int, list[CriterionResult]]:
    mapping: dict[int, list[CriterionResult]] = {}
    for criterion in criteria:
        for sentence_index in criterion.sentence_refs:
            mapping.setdefault(sentence_index, []).append(criterion)
    return mapping


def _sentence_tags(sentence: Sentence, citing_criteria: list[CriterionResult]) -> str:
    if citing_criteria:
        return "".join(
            f'<span class="sentence-tag {_tier_class(c)}">{_esc(RUBRIC[c.criterion_id].label)}</span>'
            for c in citing_criteria
        )
    # No criterion cited this sentence directly — fall back to the section it
    # was classified into, so every sentence still gets some orientation.
    section_label = _SECTION_LABELS.get(sentence.section, sentence.section)
    return f'<span class="sentence-tag tag-section">{_esc(section_label)}</span>'


def _run_key(sentence: Sentence, citing_criteria: list[CriterionResult]) -> tuple:
    if citing_criteria:
        return ("criteria", tuple(c.criterion_id for c in citing_criteria))
    return ("section", sentence.section)


def _tagged_essay_html(essay_text: str, sentences: list[Sentence], criteria: list[CriterionResult]) -> str:
    if not sentences:
        return _esc(essay_text)

    sentence_criteria = _sentence_criterion_map(criteria)
    ordered = sorted(sentences, key=lambda s: s.span_start)
    pieces: list[str] = []
    cursor = 0
    previous_run_key: tuple | None = None
    for sentence in ordered:
        pieces.append(_esc(essay_text[cursor : sentence.span_start]))
        citing = sentence_criteria.get(sentence.sentence_index, [])
        run_key = _run_key(sentence, citing)
        # Only tag the first sentence of a run of consecutive sentences that
        # share the same citation (same criterion/criteria, or same section
        # fallback) — a 3-sentence Evidence 2 span gets one "Evidence 2" tag
        # at its start, not one repeated before every sentence in it.
        if run_key != previous_run_key:
            pieces.append(_sentence_tags(sentence, citing))
        pieces.append(
            f'<span class="sentence tag-{sentence.section}">'
            f"{_esc(essay_text[sentence.span_start : sentence.span_end])}"
            f"</span>"
        )
        cursor = sentence.span_end
        previous_run_key = run_key
    pieces.append(_esc(essay_text[cursor:]))
    return "".join(pieces)


def _score_chip(criterion: CriterionResult) -> str:
    label = RUBRIC[criterion.criterion_id].label
    display = "!" if criterion.missing else str(criterion.score)
    return (
        f"<span class='chip {_tier_class(criterion)}' title='{_esc(label)}'>"
        f"<span class='chip-score'>{display}</span>"
        f"<span class='chip-label'>{_esc(label)}</span>"
        f"</span>"
    )

def _criterion_card(criterion: CriterionResult) -> str:
    label = RUBRIC[criterion.criterion_id].label
    tier = _tier_class(criterion)
    badge = "!" if criterion.missing else str(criterion.score)
    strengths = "".join(f"<li>{_esc(s)}</li>" for s in criterion.strengths) or "<li class='empty'>Nothing to point to yet</li>"
    critiques_heading = "What's missing" if criterion.missing else "What would strengthen it"
    critiques = "".join(f"<li>{_esc(c)}</li>" for c in criterion.critiques) or "<li class='empty'>None noted</li>"

    return f"""
    <article class="criterion {tier}">
      <header class="criterion-head">
        <h4>{_esc(label)}</h4>
        <span class="badge {tier}">{badge}</span>
      </header>
      <div class="criterion-body">
        <div class="feedback-col">
          <p class="feedback-label">What they did well</p>
          <ul class="strengths">{strengths}</ul>
        </div>
        <div class="feedback-col">
          <p class="feedback-label">{critiques_heading}</p>
          <ul class="critiques">{critiques}</ul>
        </div>
      </div>
      <details class="reasoning">
        <summary>Model's reasoning</summary>
        <p>{_esc(criterion.reasoning)}</p>
      </details>
    </article>
    """


def _group_section(section: str, group_label: str, criteria_by_id: dict[str, CriterionResult]) -> str:
    cards = "".join(_criterion_card(criteria_by_id[cid]) for cid in criteria_for_section(section))
    return f"""
    <section class="group">
      <h3 class="group-title">{_esc(group_label)}</h3>
      <div class="group-cards">{cards}</div>
    </section>
    """


def _essay_section(report: EssayReportData, index: int) -> str:
    criteria_by_id = {c.criterion_id: c for c in report.result.criteria}
    chips = "".join(
        _score_chip(criteria_by_id[cid])
        for section, _ in _SECTION_ORDER
        for cid in criteria_for_section(section)
    )
    groups = "".join(_group_section(section, label, criteria_by_id) for section, label in _SECTION_ORDER)
    missing_count = sum(1 for c in report.result.criteria if c.missing)
    open_attr = "open" if index == 0 else ""

    return f"""
    <details class="essay" {open_attr}>
      <summary class="essay-summary">
        <span class="essay-name">{_esc(report.essay_name)}</span>
        <span class="essay-meta">{missing_count} flagged missing</span>
      </summary>
      <div class="essay-body">
        <div class="essay-text-panel">
          <p class="essay-text">{_tagged_essay_html(report.essay_text, report.result.sentences, report.result.criteria)}</p>
        </div>
        <div class="chip-strip">{chips}</div>
        {groups}
      </div>
    </details>
    """


_STYLE = """
:root {
  --chrome: #EDEAF6;
  --card: #3F3550;
  --paper: #FAF8F4;
  --field: #F0ECE3;
  --field-border: #D9D2C4;
  --ink: #241F2E;
  --cream: #F3EFE8;
  --tier-4: #8FA98F;
  --tier-3: #D4B24C;
  --tier-12: #C97B6B;
  --tier-missing: #B3261E;
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", Georgia, serif;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, monospace;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--chrome);
  color: var(--ink);
  font-family: var(--sans);
  line-height: 1.5;
}

header.page-head {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--card);
  color: var(--cream);
  padding: 1.25rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

header.page-head h1 {
  font-family: var(--serif);
  font-weight: 600;
  font-size: 1.5rem;
  margin: 0;
  text-wrap: balance;
}

header.page-head .prompt {
  font-size: 0.95rem;
  opacity: 0.85;
  max-width: 70ch;
}

header.page-head .meta {
  font-family: var(--mono);
  font-size: 0.8rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  opacity: 0.7;
}

main {
  max-width: 920px;
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

details.essay {
  background: var(--paper);
  border: 1px solid var(--field-border);
  border-radius: 10px;
  overflow: hidden;
}

summary.essay-summary {
  cursor: pointer;
  list-style: none;
  padding: 1rem 1.25rem;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  background: var(--field);
  border-bottom: 1px solid var(--field-border);
}

summary.essay-summary::-webkit-details-marker { display: none; }

.essay-name {
  font-family: var(--mono);
  font-size: 0.85rem;
  letter-spacing: 0.02em;
  color: var(--ink);
  word-break: break-all;
}

.essay-meta {
  font-family: var(--sans);
  font-size: 0.8rem;
  color: var(--tier-missing);
  white-space: nowrap;
}

.essay-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.essay-text-panel {
  background: var(--paper);
  border: 1px solid var(--field-border);
  border-radius: 8px;
  padding: 1rem 1.25rem;
  max-height: 260px;
  overflow-y: auto;
}

.essay-text {
  font-family: var(--serif);
  font-size: 1.02rem;
  line-height: 1.7;
  margin: 0;
  white-space: pre-wrap;
}

.sentence-tag {
  display: inline-block;
  font-family: var(--sans);
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--cream);
  background: var(--card);
  border-radius: 4px;
  padding: 0.05rem 0.35rem;
  margin-right: 0.35rem;
  vertical-align: 0.15em;
}

/* Tags for sentences a specific criterion cites — colored by that criterion's
   score tier, matching the real product's "colored by score tier" spec. */
.sentence-tag.tier-4 { background: var(--tier-4); }
.sentence-tag.tier-3 { background: var(--tier-3); }
.sentence-tag.tier-12 { background: var(--tier-12); }
.sentence-tag.tier-missing { background: var(--tier-missing); }

/* Fallback for sentences no criterion directly cited — muted, so tier-colored
   (criterion-cited) tags visually stand out as the more specific signal. */
.sentence-tag.tag-section {
  background: transparent;
  color: var(--ink);
  opacity: 0.55;
  border: 1px solid var(--field-border);
}

.sentence {
  background: var(--field);
  border-radius: 3px;
  box-shadow: 0 0 0 2px var(--field);
}

.chip-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border-radius: 999px;
  padding: 0.2rem 0.6rem 0.2rem 0.4rem;
  font-size: 0.75rem;
  border: 1px solid var(--field-border);
  background: var(--field);
}

.chip-score {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.3rem;
  height: 1.3rem;
  border-radius: 50%;
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  color: var(--cream);
}

.chip-label {
  font-family: var(--sans);
  color: var(--ink);
}

.tier-4 .chip-score, .badge.tier-4 { background: var(--tier-4); }
.tier-3 .chip-score, .badge.tier-3 { background: var(--tier-3); }
.tier-12 .chip-score, .badge.tier-12 { background: var(--tier-12); }
.tier-missing .chip-score, .badge.tier-missing { background: var(--tier-missing); }

.group-title {
  font-family: var(--sans);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--card);
  margin: 0 0 0.6rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--field-border);
}

.group:first-of-type .group-title { border-top: none; padding-top: 0; }

.group-cards {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

article.criterion {
  background: var(--card);
  color: var(--cream);
  border-radius: 8px;
  padding: 0.9rem 1.1rem;
  border-left: 4px solid var(--field-border);
}

article.criterion.tier-4 { border-left-color: var(--tier-4); }
article.criterion.tier-3 { border-left-color: var(--tier-3); }
article.criterion.tier-12 { border-left-color: var(--tier-12); }
article.criterion.tier-missing { border-left-color: var(--tier-missing); }

.criterion-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.6rem;
}

.criterion-head h4 {
  font-family: var(--sans);
  font-size: 0.95rem;
  font-weight: 600;
  margin: 0;
}

.badge {
  font-family: var(--mono);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--cream);
  border-radius: 50%;
  width: 1.7rem;
  height: 1.7rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.criterion-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.feedback-label {
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  opacity: 0.75;
  margin: 0 0 0.3rem;
}

.criterion-body ul {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.88rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.criterion-body ul.strengths li::marker { color: var(--tier-4); }
.criterion-body ul.critiques li::marker { color: var(--tier-3); }
.criterion-body li.empty { opacity: 0.6; font-style: italic; }

details.reasoning {
  margin-top: 0.75rem;
  font-size: 0.85rem;
}

details.reasoning summary {
  cursor: pointer;
  opacity: 0.8;
  font-size: 0.78rem;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

details.reasoning p {
  margin: 0.5rem 0 0;
  opacity: 0.9;
  line-height: 1.55;
}

@media (max-width: 600px) {
  .criterion-body { grid-template-columns: 1fr; }
}
"""


def render_report_html(reports: list[EssayReportData]) -> str:
    shared_prompt = reports[0].assignment_prompt if reports else ""
    essays = "".join(_essay_section(r, i) for i, r in enumerate(reports))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Grading Review</title>
<style>{_STYLE}</style>
</head>
<body>
  <header class="page-head">
    <h1>Grading Review</h1>
    <p class="prompt">{_esc(shared_prompt)}</p>
    <p class="meta">{len(reports)} essay(s) &middot; Phase 0 pipeline output</p>
  </header>
  <main>
    {essays}
  </main>
</body>
</html>"""
