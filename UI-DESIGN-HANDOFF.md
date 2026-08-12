# AP Lit Essay Grader — UI Design Handoff

Companion to `README.md` and `CLAUDE.md`. This doc is the source of truth for frontend
implementation: the design system, the full screen flow, the data contract the UI expects
from the backend, and everywhere the reference mock takes a shortcut a real build can't.

**Reference implementation**: `ap-lit-grader-full-flow.jsx` — a single-file React mockup
covering the entire flow with mock data and simulated interactions. It is the visual and
interaction source of truth; this doc explains *why* it's built the way it is and *where*
it fakes something a real backend needs to actually provide.

## Design system

| Token | Value | Use |
|---|---|---|
| Chrome background | `#EDEAF6` | Pale lavender — nav bar, rubric key area, page background. Never the essay itself. |
| Card / accent | `#3F3550` | Dark plum — feedback panels, session bar, callouts, buttons |
| Paper | `#FAF8F4` | Essay surface — always the lightest thing on screen, legibility over theme |
| Ink | `#241F2E` | Primary text on light surfaces |
| Cream | `#F3EFE8` | Primary text on dark (card) surfaces |
| Strength tier | `#8FA98F` (sage) | Score 4, and "did well" bullet dots |
| Solid tier | `#D4B24C` (gold) | Score 3 |
| Developing tier | `#C97B6B` (coral) | Score 1-2, and "would strengthen" bullet dots |
| Missing tier | `#B3261E` (alert red) | A criterion with no content in the essay — deliberately outside the 1-4 color spectrum so it never reads as "just a low score" |

**Typography**: Fraunces (serif, variable) for the essay body and headings — makes the essay
read like a page, not an app. Inter for all UI chrome, labels, and feedback text — legibility
was the explicit fix for an earlier version that used a handwritten font for real feedback
copy and was unreadable. Caveat (handwritten) is reserved for small flourishes only (the
overall-score stamp badge) — never for anything that needs to be read carefully; that
mistake was made and corrected once already.

**Why this palette, not a generic template default**: modeled on pudding.cool's use of a
moody, saturated chrome paired with a restrained accent and high-contrast callout boxes for
text that must be legible over a busy background — adapted here as "the grading UI gets the
lavender/plum treatment, the essay itself stays plain and light because it's the thing being
read carefully."

## Full flow

```
setup ──(Start grading)──▶ paste ──(Grade this essay)──▶ loading ──▶ graded ──(Finish grading)──▶ paste (next essay)
  ▲                          │                                          │
  └──────(Adjust assignment)─┴──────────────(Adjust assignment)─────────┘
  
  newAssignment() resets everything and returns to a blank setup, from any state.
```

### 1. Setup (once per batch of essays)
Three fields, asked in this order because this is the order a teacher actually thinks in:
1. **What are we grading** — "Full essay" toggle, or multi-select individual criteria, grouped
   visually by essay part (see Rubric key grouping below) so "grade Evidence in both
   paragraphs" is a couple of clicks in visually adjacent places, not a hunt through a flat
   14-item list.
2. **Assignment prompt** — free text, the actual prompt she gave the class (distinct from the
   rubric, which is fixed and not re-entered).
3. **Class** — fixed dropdown (backend will maintain a class list + pseudonymous student-ID
   lookup table per README Phase 2 groundwork).

### 2. Cached session bar
Once setup is submitted, sections/prompt/class collapse into a persistent bar shown above
every subsequent screen (paste, loading, error, graded) until she explicitly changes it. The
bar always shows *when* it was set up and a running "N essays graded" count, so the cache is
visibly trustworthy rather than silently reused. Two distinct actions, deliberately different
weights:
- **"Adjust assignment"** (quiet, secondary) — reopens setup with current values pre-filled.
  Named to avoid the "is this the same as New assignment?" ambiguity an earlier "Edit" label
  caused.
- **"New assignment"** (loud, primary-colored) — wipes everything and starts a blank setup.
  Should be visually harder to hit by accident than Adjust.

### 3. Paste (repeats per essay)
Student name + essay text only — everything else is already cached above. "Grade this essay"
disabled until both fields are non-empty.

### 4. Loading
No fake determinate progress bar — real duration is variable (60-90s worst case per README),
so a bar that claims to know when it'll finish would be lying. Instead: a real elapsed-time
counter, rotating status text that follows the actual grading order (thesis → body 1 → body 2
→ conclusion, so it reads as genuine progress), and a reassurance line that only appears after
~20s so it doesn't clutter a fast response. The essay stays visible and dims rather than
disappearing, so nothing feels lost.

### 5. Error
Required by README's non-functional reliability spec ("visible error state, not a silent
hang"). Essay text is preserved untouched; one clear action, "Try again."

### 6. Graded — the core screen
All 14 criteria shown **expanded simultaneously**, not click-to-reveal one at a time — an
earlier version used a single-active-card pattern to avoid a "wall of text," but the actual
teacher use case (a returned, annotated paper) reads better as a live, fully-annotated page,
and structured per-card content (score → did well → strengthen) holds up at this density
better than the original single-line-note version did.

**Grouping, top rubric key**: Thesis alone / "Body ¶1" labeled row of its 6 criteria / "Body
¶2" labeled row of its 6 / Conclusion alone — mirrors the essay's actual structure and reading
order, not a flat alphabetized or generation-order list. This was a direct fix for a flat
14-chip row reading as cluttered.

**Each criterion card contains, in this order**:
1. Criterion label + score badge (or a `!` "Missing" badge — see below)
2. If corrected: "Originally X/4 by Claude — corrected to Y/4 by you" (audit trail)
3. **What they did well** — bullet list, sage dots
4. **What would strengthen it** — bullet list, gold/coral dots
5. Collapsed **"Show model's reasoning"** disclosure — the model's rubric-boundary
   justification, in a different register than the coaching-voice bullets above (explicitly
   references which score-band boundary was weighed, e.g. "held at 3 rather than 4 because…").
   Exists specifically so a disagreement can be diagnosed, not just asserted.
6. **"Disagree with this score?"** — opens an independent per-criterion dispute thread.

**In-essay tags**: each sentence gets a small labeled chip (`EVIDENCE 1`, `REASONING 2`, etc.)
colored by score tier, positioned before the sentence it grades. Clicking a tag, or a rubric
key chip, scrolls the corresponding margin card into view and highlights it — navigation, not
selection, since everything is already visible.

### 7. Missing-criterion handling
Simulated in the mock as Body ¶1 / Reasoning 1. Deliberately distinct from a low score
everywhere it appears, because "nothing was written" and "something weak was written" are
different signals for both the teacher and the training pipeline:
- Top key + margin card badge: `!` in alert red, not a numeral in a tier color.
- **Inline in the essay itself**: a dashed, outlined placeholder chip sits where the sentence
  should have been (between Evidence 1 and Evidence 2 in the mock) — the gap is visible on the
  page she's reading, not just summarized in a sidebar.
- Margin card copy changes: "What they did well" → an honest "Nothing to point to yet" instead
  of an empty bullet list; "What would strengthen it" relabels to "What's missing."
- Disputing a missing criterion gets different simulated dialogue than disputing a weak one —
  Claude doesn't say "I weighted this too generously" (nothing was weighted); it confirms it
  still doesn't see the content and offers the real choice: keep flagged, or assign a floor
  score of 1/4.
- **Does not block "Finish grading."** An open, mid-conversation *dispute* does block finishing
  (she started a thought and would lose it) — an unaddressed *missing* flag doesn't, since it
  might just mean she agrees nothing is there. Soft warning text only.

### 8. Dispute / discussion flow
Per-criterion, independent, and can be open on multiple criteria at once. Chat-style thread
(her messages right-aligned cream, Claude's left-aligned translucent). Ends in an explicit
**"Finalize your score"** step: 1-4 chip picker, defaulting to whatever Claude proposed in
conversation but always requiring her own click before "Save correction" is enabled — Claude's
proposal is never auto-applied. This matters beyond UX: per README's data model, the DPO pair
is *her* correction vs. Claude's original, and that's only a clean signal if her decision is
unambiguous and deliberately made, not inferred from a conversation.

**"Save correction" vs. autosave**: this is the one place in the app that requires an explicit
save button, and it's a deliberate exception to "everything else autosaves." See README's
"Autosave-vs-explicit-save principle." Everything else in the app (typing in the essay
textarea, the chat draft, clicking through score options before deciding) is fluid with no
save step.

### 9. Finish grading
Full-width bar, bottom of page — the one clearly primary action on the screen once grading is
done. Shows a live summary ("2 criteria corrected · 12 accepted as graded") before commitment.
**Hard-blocks** if any dispute is open and unresolved (guards against silently losing a
half-formed critique or committing an unintended score). This is also the moment every
criterion she never disputed gets bulk-written to `accepted_grades` at Claude's original
score — the mechanic that generates README's "agreement case" training data. After finishing,
the bar becomes a confirmation ("✓ Grades saved — 4:12pm") with a **"Next essay →"** action
that resets per-essay state and returns to Paste with the same cached session.

### 10. Back to top
Floating button, bottom-right, appears only in the graded view once scrolled past ~400px —
needed once a graded essay is 14 cards deep.

## API contract the UI expects

Per criterion, the backend needs to return:

```jsonc
{
  "id": "bp1-reasoning-1",              // stable criterion id
  "label": "Reasoning 1",
  "group": "Body ¶1",                    // null for Thesis/Conclusion
  "score": null,                         // 1-4, or null if missing
  "missing": true,                       // explicit, not inferred from score being null elsewhere
  "strengths": [],                       // can be empty (see missing-state copy above)
  "critiques": ["...", "..."],
  "reasoning": "...",                    // rubric-boundary justification, always present
  "span": { "start": 412, "end": 498 }   // OPEN QUESTION — see below
}
```

**Open question, blocks a clean implementation**: the mock hardcodes which essay sentence
belongs to which criterion by matching ids in fixture data. A real essay needs the backend to
tell the frontend *where* in the raw essay text each criterion's feedback applies — character
offsets, sentence indices, or similar — so the inline tags and the "missing" placeholder can
be positioned correctly for arbitrary submitted text. Whether this is emitted directly by the
grading model or computed as a separate alignment pass is undecided; flagged in README's Open
questions. Nothing else in this doc depends on the answer, but the highlighting UI can't ship
without one.

## Known mock limitations (do not treat these as the target behavior)

- **The graded essay content is static demo data** (a fixed Gatsby analysis), regardless of
  what's actually pasted in. The paste/loading/error states do show her real typed input; only
  the graded view swaps to fixture data. A real build obviously renders the model's actual
  scored output against her actual submitted essay.
- **The simulated Claude dispute replies are canned**, not real model calls — real
  implementation calls the grading endpoint (or a lighter-weight discussion endpoint) with the
  conversation so far and returns a real response + proposed score.
- **Class list is hardcoded** (`Period 3/5/7`) — real version reads from the class table
  referenced in README's Tech stack / Phase 2 groundwork.
- **No persistence** — all state (overrides, disputes, session) lives in React state and is
  lost on refresh. Every place this doc says "written to `accepted_grades`" or similar is
  describing the intended backend write, not something the mock actually does.
