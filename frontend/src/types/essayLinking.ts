// Resolved sentence-centric essay/criterion linking model.
// See FRONTEND-BACKEND-INTEGRATION.md ("Resolved: essay/criterion linking model")
// for the design rationale. Replaces the old EssayChunk / EssayFixture shape,
// which assumed one contiguous chunk per criterion and couldn't represent
// many-to-many or interleaved sentence_refs.

/** One sentence from the deterministic (code-based, not model) tokenizer. */
export interface EssaySentence {
  /** Stable index into the essay's sentence list. Referenced by sectionOf and citingCriteria. */
  index: number;
  text: string;
}

/** The 4 fixed structural sections, produced by the segmentation call. */
export type SectionId = "thesis" | "bp1" | "bp2" | "conclusion";

/**
 * Geography: which section a sentence renders in. Roughly 1:1 (one section per
 * sentence). Produced by the segmentation call and independent of scoring —
 * this is what still tells you where a *missing* criterion's section is, even
 * when citingCriteria has no entry for it.
 */
export type SectionOfMap = Record<number, SectionId>;

/**
 * Purpose: which rubric criteria cite this sentence, and therefore which
 * in-essay tag chip(s) render before it. Derived from each criterion's
 * sentence_refs. Many-to-many: a sentence may be cited by zero, one, or
 * several criteria; a criterion may cite zero, one, or several sentences,
 * and citations can interleave with another criterion's (see
 * bp2-evidence-2 / bp2-reasoning-2 in the integration doc).
 */
export type CitingCriteriaMap = Record<number, string[]>; // sentence index -> criterion ids

/** Fixed rubric order within a section, used only for missing-criterion placement inference. */
export const CRITERION_ORDER_BY_SECTION: Record<SectionId, string[]> = {
  thesis: ["thesis"],
  bp1: [
    "bp1-claim",
    "bp1-evidence-1",
    "bp1-reasoning-1",
    "bp1-evidence-2",
    "bp1-reasoning-2",
    "bp1-synthesis",
  ],
  bp2: [
    "bp2-claim",
    "bp2-evidence-1",
    "bp2-reasoning-1",
    "bp2-evidence-2",
    "bp2-reasoning-2",
    "bp2-synthesis",
  ],
  conclusion: ["conclusion"],
};

export interface CriterionResult {
  id: string; // aligned from backend's criterion_id per integration doc's "Criterion shape" resolution
  label: string; // embedded by backend, sourced from services/rubric.py's RUBRIC dict
  group: string | null; // display label, e.g. "Body ¶1" — NOT a SectionId. null for Thesis/Conclusion, matching group semantics elsewhere in the app (CriterionCard/RubricKey render this directly as text)
  score: number | null; // 1-4, or null if missing
  missing: boolean;
  strengths: string[];
  critiques: string[];
  reasoning: string;
  sentence_refs: number[]; // raw backend field; citingCriteria is the inverted/derived view of this across all criteria
}

/** Full response shape the /grade endpoint returns (or a client-side inversion produces). */
export interface GradedEssay {
  sentences: EssaySentence[];
  sectionOf: SectionOfMap;
  citingCriteria: CitingCriteriaMap;
  criteria: CriterionResult[];
}

/**
 * Builds citingCriteria from the raw per-criterion sentence_refs, if the backend
 * sends only the raw criteria list. Prefer having the backend send citingCriteria
 * precomputed (it already builds an equivalent map in services/report.py's
 * _sentence_criterion_map) — this is a fallback for deriving it client-side.
 */
export function buildCitingCriteria(criteria: CriterionResult[]): CitingCriteriaMap {
  const map: CitingCriteriaMap = {};
  for (const c of criteria) {
    for (const idx of c.sentence_refs) {
      if (!map[idx]) map[idx] = [];
      map[idx].push(c.id);
    }
  }
  return map;
}

/**
 * Resolves the inline placement (sentence index to insert *after*) for a missing
 * criterion. Returns null only if the section has no sentences at all to anchor to.
 * See FRONTEND-BACKEND-INTEGRATION.md "Resolved: missing-criterion inline placement".
 */
export function resolveMissingPlacement(
  missingCriterionId: string,
  section: SectionId,
  criteria: CriterionResult[],
  sectionOf: SectionOfMap
): number | null {
  const order = CRITERION_ORDER_BY_SECTION[section];
  const position = order.indexOf(missingCriterionId);
  if (position < 0) return null;

  // Walk backwards through the fixed order to find the nearest preceding
  // criterion that actually has sentence refs (defensive: a preceding
  // criterion could itself be missing).
  for (let i = position - 1; i >= 0; i--) {
    const preceding = criteria.find((c) => c.id === order[i]);
    if (preceding && preceding.sentence_refs.length > 0) {
      return Math.max(...preceding.sentence_refs);
    }
  }

  // Fallback: nothing precedes it (or all preceding criteria are also
  // missing) — anchor to the start of the section's sentence range.
  const sectionIndices = Object.entries(sectionOf)
    .filter(([, s]) => s === section)
    .map(([idx]) => Number(idx));
  if (sectionIndices.length === 0) return null;
  return Math.min(...sectionIndices) - 1; // "insert before the first sentence in the section"
}
