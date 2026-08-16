import { clearAuth, getAccessToken } from '../auth/authStore'
import type { CriterionResult, EssaySentence, GradedEssay, SectionId } from '../types/essayLinking'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export interface GradeRequestPayload {
  essayText: string
  assignmentPrompt: string
  studentName?: string
}

export class GradeRequestError extends Error {
  cause?: unknown

  constructor(message: string, cause?: unknown) {
    super(message)
    this.cause = cause
  }
}

// Raw wire shape from POST /grade — deliberately kept separate from the
// camelCase GradedEssay/CriterionResult app-internal shape. This file's
// transformGradeResponse() is the one seam that converts between them.
interface RawCriterionResult {
  criterion_id: string
  label: string
  group: string | null
  score: number | null
  missing: boolean
  strengths: string[]
  critiques: string[]
  reasoning: string
  sentence_refs: number[]
}

interface RawSentence {
  sentence_index: number
  text: string
}

interface RawGradeResponse {
  criteria: RawCriterionResult[]
  sentences: RawSentence[]
  section_of: Record<string, SectionId>
  citing_criteria: Record<string, string[]>
}

function transformGradeResponse(raw: RawGradeResponse): GradedEssay {
  const sentences: EssaySentence[] = raw.sentences.map((s) => ({ index: s.sentence_index, text: s.text }))

  const criteria: CriterionResult[] = raw.criteria.map((c) => ({
    id: c.criterion_id,
    label: c.label,
    group: c.group,
    score: c.score,
    missing: c.missing,
    strengths: c.strengths,
    critiques: c.critiques,
    reasoning: c.reasoning,
    sentence_refs: c.sentence_refs,
  }))

  return {
    sentences,
    sectionOf: raw.section_of,
    citingCriteria: raw.citing_criteria,
    criteria,
  }
}

export async function gradeEssay(payload: GradeRequestPayload): Promise<GradedEssay> {
  const accessToken = getAccessToken()
  if (!accessToken) {
    throw new GradeRequestError('Not signed in.')
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/grade`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        essay_text: payload.essayText,
        assignment_prompt: payload.assignmentPrompt,
        student_name: payload.studentName,
      }),
    })
  } catch (err) {
    throw new GradeRequestError('Could not reach the grading service.', err)
  }

  if (response.status === 401) {
    clearAuth()
    throw new GradeRequestError('Your session expired. Please sign in again.')
  }

  if (!response.ok) {
    let detail: unknown
    try {
      detail = await response.json()
    } catch {
      // Response body wasn't JSON — leave detail undefined.
    }
    throw new GradeRequestError(`Grading request failed (${response.status}).`, detail)
  }

  const raw = (await response.json()) as RawGradeResponse
  return transformGradeResponse(raw)
}
