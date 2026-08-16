import { clearAuth, getAccessToken } from '../auth/authStore'
import type { CriterionResult } from '../types/essayLinking'
import type { DisputeMessage } from '../components/DisputeThread'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''

export interface DisputeTurnPayload {
  // No classId — the server derives teacher_id/class_id from essay_id (the essay
  // and its session), rather than trusting a client-supplied value, and rejects
  // the call if the signed-in teacher doesn't own that essay.
  essayId: string
  essayText: string
  assignmentPrompt: string
  original: CriterionResult
  messages: DisputeMessage[]
}

export interface DisputeTurnResult {
  message: string
  proposal: CriterionResult | null
  // Set only alongside proposal — echo this back verbatim to resolveDispute()
  // when she saves a correction, so the server knows which raw_grades row to point at.
  proposalRawGradeId: string | null
}

export type DisputeResolution = 'corrected' | 'kept_original'

export interface DisputeResolvePayload {
  essayId: string
  criterionId: string
  resolution: DisputeResolution
  // Required for 'corrected' (the accepted DisputeTurnResult's proposalRawGradeId);
  // omitted for 'kept_original' — the server looks up the original grade itself.
  rawGradeId?: string
}

export interface DisputeResolveResult {
  acceptedGradeId: string
  score: number | null
  missing: boolean
}

export class DisputeRequestError extends Error {
  cause?: unknown

  constructor(message: string, cause?: unknown) {
    super(message)
    this.cause = cause
  }
}

// Wire shape matches backend's DisputeMessage/CriterionResult schemas (snake_case,
// role 'assistant' not 'claude') — kept separate from the app-internal camelCase
// shapes, same seam pattern as api/grade.ts.
interface RawCriterionResult {
  criterion_id: string
  score: number | null
  missing: boolean
  strengths: string[]
  critiques: string[]
  reasoning: string
  sentence_refs: number[]
}

interface RawDisputeTurnResponse {
  message: string
  proposal: RawCriterionResult | null
  proposal_raw_grade_id: string | null
}

interface RawDisputeResolveResponse {
  accepted_grade_id: string
  score: number | null
  missing: boolean
}

function toRawProposal(proposal: RawCriterionResult): CriterionResult {
  return {
    id: proposal.criterion_id,
    // label/group are display-only computed fields the backend embeds on grading
    // responses — a proposal doesn't need them since it's never rendered as a
    // standalone CriterionResult card, only merged into the existing one client-side.
    label: '',
    group: null,
    score: proposal.score,
    missing: proposal.missing,
    strengths: proposal.strengths,
    critiques: proposal.critiques,
    reasoning: proposal.reasoning,
    sentence_refs: proposal.sentence_refs,
  }
}

export async function disputeTurn(payload: DisputeTurnPayload): Promise<DisputeTurnResult> {
  const accessToken = getAccessToken()
  if (!accessToken) {
    throw new DisputeRequestError('Not signed in.')
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/grade/dispute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        essay_id: payload.essayId,
        essay_text: payload.essayText,
        assignment_prompt: payload.assignmentPrompt,
        original: {
          criterion_id: payload.original.id,
          score: payload.original.score,
          missing: payload.original.missing,
          strengths: payload.original.strengths,
          critiques: payload.original.critiques,
          reasoning: payload.original.reasoning,
          sentence_refs: payload.original.sentence_refs,
        },
        messages: payload.messages.map((m) => ({
          role: m.role === 'claude' ? 'assistant' : 'teacher',
          content: m.text,
        })),
      }),
    })
  } catch (err) {
    throw new DisputeRequestError('Could not reach the grading service.', err)
  }

  if (response.status === 401) {
    clearAuth()
    throw new DisputeRequestError('Your session expired. Please sign in again.')
  }

  if (!response.ok) {
    let detail: unknown
    try {
      detail = await response.json()
    } catch {
      // Response body wasn't JSON — leave detail undefined.
    }
    throw new DisputeRequestError(`Dispute request failed (${response.status}).`, detail)
  }

  const raw = (await response.json()) as RawDisputeTurnResponse
  return {
    message: raw.message,
    proposal: raw.proposal ? toRawProposal(raw.proposal) : null,
    proposalRawGradeId: raw.proposal_raw_grade_id,
  }
}

export async function resolveDispute(payload: DisputeResolvePayload): Promise<DisputeResolveResult> {
  const accessToken = getAccessToken()
  if (!accessToken) {
    throw new DisputeRequestError('Not signed in.')
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/grade/dispute/resolve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        essay_id: payload.essayId,
        criterion_id: payload.criterionId,
        resolution: payload.resolution,
        raw_grade_id: payload.rawGradeId,
      }),
    })
  } catch (err) {
    throw new DisputeRequestError('Could not reach the grading service.', err)
  }

  if (response.status === 401) {
    clearAuth()
    throw new DisputeRequestError('Your session expired. Please sign in again.')
  }

  if (!response.ok) {
    let detail: unknown
    try {
      detail = await response.json()
    } catch {
      // Response body wasn't JSON — leave detail undefined.
    }
    throw new DisputeRequestError(`Dispute resolve request failed (${response.status}).`, detail)
  }

  const raw = (await response.json()) as RawDisputeResolveResponse
  return { acceptedGradeId: raw.accepted_grade_id, score: raw.score, missing: raw.missing }
}
