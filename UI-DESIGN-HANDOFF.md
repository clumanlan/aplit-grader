# AP Lit Essay Grader — UI Design Handoff

Companion to `README.md` and `CLAUDE.md`. This doc is the source of truth for frontend
implementation: the design system, the full screen flow, the data contract the UI expects
from the backend, and everywhere the reference mock takes a shortcut a real build can't.

**Reference implementation**: `ap-lit-grader-full-flow.jsx` — a single-file React mockup
covering the entire flow with mock data and simulated interactions. It is the visual and
interaction source of truth; this doc explains *why* it's built the way it is and *where*
it fakes something a real backend needs to actually provide.

## Implementation status

The real frontend is built, in `frontend/` — Vite + React + TypeScript + Tailwind v4, per
README's Tech stack, test-driven with Vitest + React Testing Library (43 tests, all passing).
Every screen in the Full flow below exists as a tested component and is wired together in
`frontend/src/App.tsx`: Setup (including edit mode via "Adjust assignment"), the cached session
bar, Paste, Loading, Error, and the full Graded view (rubric key, all 14 criterion cards,
in-essay tags including the missing-criterion placeholder, per-criterion dispute threads, Finish
grading, Back to top).

Two known gaps, both expected at this stage and blocked on backend work, not frontend work:
- **No backend yet.** The Graded view always renders the same fixture essay/scores
  (`frontend/src/fixtures/demoGrading.ts`, ported from this doc's reference mock data) rather
  than a real model response to whatever was actually pasted — this is the mock's own documented
  limitation, still true of the real build until Phase 0/1 backend work lands.
- **Class list is still hardcoded** (`Period 3/5/7` in `App.tsx`) — real version reads from the
  class table referenced in README's Tech stack / Phase 2 groundwork, same as the mock.

Several places where the real build was built intentionally *unlike* the reference mock — not
oversights — are called out inline below as "Implementation note" callouts: exact hex values
(not the nearest Tailwind default) for the paper/chrome/field surfaces, a Petrona swap-in for
Fraunces after its Google Fonts variable-axis import wouldn't reliably load, Paste/Loading
staying full-width and stacked instead of copying the mock's idle sidebar, the dispute
finalize-picker requiring her own click rather than the mock's auto-applied default, and the
Graded view's criterion cards rendering full-width below the essay instead of in a narrow
margin-notes column.

## Design system

| Token | Value | Use |
|---|---|---|
| Chrome background | `#EDEAF6` | Pale lavender — nav bar, rubric key area, page background. Never the essay itself. |
| Card / accent | `#3F3550` | Dark plum — feedback panels, session bar, callouts, buttons |
| Paper | `#FAF8F4` | Essay/setup-card surface — always the lightest thing on screen, legibility over theme. Pale, cool, almost-white — closer to white than to cream. |
| Field | `#F0ECE3` | Input/textarea/select fields sitting on paper — slightly deeper than paper so form fields read as a distinct surface, not indistinguishable from the card behind them |
| Field border | `#D9D2C4` | 1px border on fields and unselected criteria chips |
| Ink | `#241F2E` | Primary text on light surfaces |
| Cream | `#F3EFE8` | Primary text on dark (card) surfaces |
| Strength tier | `#8FA98F` (sage) | Score 4, and "did well" bullet dots |
| Solid tier | `#D4B24C` (gold) | Score 3 |
| Developing tier | `#C97B6B` (coral) | Score 1-2, and "would strengthen" bullet dots |
| Missing tier | `#B3261E` (alert red) | A criterion with no content in the essay — deliberately outside the 1-4 color spectrum so it never reads as "just a low score" |

**Typography**: Petrona (serif) for the essay body and headings — makes the essay read like a
page, not an app. (Originally speced as Fraunces; swapped during Phase 1 build because Fraunces'
variable-axis Google Fonts import wasn't reliably resolving to a loaded webfont — see
Implementation note below. Petrona was picked as the closest match to Fraunces' warmth, and is
requested via plain static weights, no variable axes, per the same bulletproofing.) Inter for all
UI chrome, labels, and feedback text — legibility was the explicit fix for an earlier version
that used a handwritten font for real feedback copy and was unreadable. Caveat (handwritten) is
reserved for small flourishes only (the overall-score stamp badge) — never for anything that
needs to be read carefully; that
mistake was made and corrected once already.

**Why this palette, not a generic template default**: modeled on pudding.cool's use of a
moody, saturated chrome paired with a restrained accent and high-contrast callout boxes for
text that must be legible over a busy background — adapted here as "the grading UI gets the
lavender/plum treatment, the essay itself stays plain and light because it's the thing being
read carefully."

**Implementation note — use the literal hex, not the nearest Tailwind default**: paper, chrome,
and field are three deliberately close, deliberately distinct near-white/pale surfaces, and a
framework default will not land on any of them.
- Paper (`#FAF8F4`) is not `bg-white`, not `bg-gray-50`, not `bg-amber-50` — it must read pale,
  cool, almost-white, never warmer/creamier than the literal value.
- Field (`#F0ECE3`) exists specifically so inputs/textareas/selects sitting on paper don't
  default to browser/framework white — an unstyled `<input>`/`<textarea>`/`<select>` background
  reads as a jarring pure-white against paper and collapses the paper/field/chrome layering the
  design depends on. Every form control needs its background set explicitly.
- This was caught in the first Setup-screen build: the criteria-picker chips weren't boxed in a
  field-colored container per the mock, and text inputs had no explicit background at all
  (defaulting to white). Check every new component against the literal hex — an inherited
  default filling in for paper/chrome/field is a bug, not a close-enough approximation.
- Setup's "what are we grading" chips (full-essay toggle + individual criteria) sit inside a
  field-colored (`#F0ECE3`) box with a `#D9D2C4` border; each chip itself is bordered
  (`#D9D2C4`), with card-colored fill + cream text when selected, white fill + ink text when not
  — not a flat, unboxed row of text buttons.

**Implementation note — verify webfonts actually load, don't just verify the import is present**:
a font `<link>`/`@import` can be syntactically correct and still never reach the rendered page —
the CSS custom property resolves fine, the `@font-face` rule exists, and the browser still falls
back silently to a system font with no console error. `document.fonts.check('16px <Family>')` in
the browser console is the fast way to catch this (`true` only once that family is actually
loaded and available, not just declared). Caught during Phase 1 build: Fraunces, requested via
Google Fonts' variable-axis syntax (`family=Fraunces:opsz,wght@9..144,400;...`), never resolved
to a loaded font in testing even though the stylesheet request itself returned valid `@font-face`
rules — root cause not fully isolated, but a plain static-weight request (`family=Petrona:wght@
500;600;700`, no `opsz` axis) did resolve reliably, so Petrona replaced Fraunces as the essay/
heading serif. If a future font swap has the same symptom, check `document.fonts.check(...)`
before trusting that adding the link tag was sufficient — and prefer plain static-weight Google
Fonts URLs over variable-axis ones as the more reliable default.

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
disabled until both fields are non-empty. Full-width — no sidebar. The reference mock renders a
persistent right-column sidebar next to the essay from Paste through Graded (empty placeholder
copy at Paste, the loading card at Loading, margin notes at Graded); a real build should not copy
that literally for the Paste/Loading pair. An idle sidebar showing "scores will appear here" next
to a form that hasn't been submitted yet is clutter, not a preview — there's nothing to preview.

### 4. Loading
No fake determinate progress bar — real duration is variable (60-90s worst case per README),
so a bar that claims to know when it'll finish would be lying. Instead: a real elapsed-time
counter, rotating status text that follows the actual grading order (thesis → body 1 → body 2
→ conclusion, so it reads as genuine progress), and a reassurance line that only appears after
~20s so it doesn't clutter a fast response. The essay stays visible and dims rather than
disappearing, so nothing feels lost — and per that same logic, Loading is not a new page:
submitting Paste keeps her on the same full-width screen, dims the essay in place, and the
grading-in-progress card appears stacked directly below it (where the "Grade this essay" button
was), not beside it in a sidebar. A page navigation at this step would itself make the essay feel
lost for a moment, which is exactly what the dim-in-place treatment is meant to avoid. The sidebar
layout only earns its keep once there's per-line content to anchor to — i.e. at Graded, where the
right column becomes real margin notes tied to specific sentences.

### 5. Error
Required by README's non-functional reliability spec ("visible error state, not a silent
hang"). Essay text is preserved untouched; one clear action, "Try again."

### 6. Graded — the core screen
All 14 criteria shown **expanded simultaneously**, not click-to-reveal one at a time — an
earlier version used a single-active-card pattern to avoid a "wall of text," but the actual
teacher use case (a returned, annotated paper) reads better as a live, fully-annotated page,
and structured per-card content (score → did well → strengthen) holds up at this density
better than the original single-line-note version did.

**Layout — full-width, stacked, not a margin-notes sidebar.** The reference mock renders the
essay and the 14 criterion cards side by side (essay in a wide left column, cards in a narrow
360px-ish right column meant to evoke a teacher's margin annotations). The real build does not
keep that split: the essay panel takes the full page width, and the criterion cards render
below it, also full width, stacked one per row — not squeezed into a narrow sidebar column and
not split into a multi-column grid either. The in-essay tags still work the same way (click a
tag, jump to its card via anchor + scroll), it's just that the destination is a full-width card
below the essay instead of a slim column beside it. Reasoning: a 360px column is fine for one
line of badge but cramped for a card that has to hold a score badge, an audit line, two bullet
lists, a reasoning disclosure, and a full dispute thread — full width gives that content room
without shrinking the essay to make space for it, and without introducing a second reading
column to track.

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

**Implementation note — the reference mock takes exactly the shortcut this section warns
against; don't copy it.** In the mock, `dispute.pick` is auto-set to Claude's proposed score the
moment Claude replies, and "Save correction" has no `disabled` check beyond "is a value picked at
all" — so clicking Save without ever touching a chip silently applies Claude's number. That
directly contradicts "always requiring her own click" and "Claude's proposal is never
auto-applied" above. The real `DisputeThread` component does not carry this over: the picker
starts with nothing selected regardless of what Claude proposed, and "Save correction" stays
disabled until she clicks a chip herself (she can still click the same number Claude suggested —
the requirement is the click, not disagreement).

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
