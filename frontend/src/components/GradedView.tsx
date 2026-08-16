import { useState } from 'react'
import { disputeTurn, resolveDispute, DisputeRequestError } from '../api/dispute'
import { BackToTop } from './BackToTop'
import { CriterionCard } from './CriterionCard'
import { DisputeThread, type DisputeMessage } from './DisputeThread'
import { EssayTag } from './EssayTag'
import { FinishGradingBar } from './FinishGradingBar'
import { RubricKey } from './RubricKey'
import {
  CRITERION_ORDER_BY_SECTION,
  resolveMissingPlacement,
  type CriterionResult,
  type GradedEssay,
  type SectionId,
  type SectionOfMap,
} from '../types/essayLinking'

interface DisputeState {
  open: boolean
  messages: DisputeMessage[]
  sending: boolean
  resolved: boolean
  resolving: boolean
  proposedScore: number | null
  // Set alongside proposedScore — the raw_grades row a "Save correction" click
  // resolves against. Required by POST /grade/dispute/resolve for resolution='corrected'.
  proposalRawGradeId: string | null
}

const EMPTY_DISPUTE: DisputeState = {
  open: true,
  messages: [],
  sending: false,
  resolved: false,
  resolving: false,
  proposedScore: null,
  proposalRawGradeId: null,
}

export interface GradedViewProps {
  studentName: string
  classId: string
  assignmentPrompt: string
  essayText: string
  gradedEssay: GradedEssay
  onFinish: () => void
  onNextEssay: () => void
}

type RenderItem = { kind: 'sentence'; index: number } | { kind: 'missing'; criterionId: string; afterIndex: number }

const SECTIONS: SectionId[] = ['thesis', 'bp1', 'bp2', 'conclusion']

function buildSectionRenderItems(
  section: SectionId,
  sectionIndices: number[],
  missingCriteriaInSection: string[],
  rubric: CriterionResult[],
  sectionOf: SectionOfMap,
): RenderItem[] {
  const items: RenderItem[] = sectionIndices.map((index) => ({ kind: 'sentence', index }))

  for (const criterionId of missingCriteriaInSection) {
    const afterIndex = resolveMissingPlacement(criterionId, section, rubric, sectionOf)
    if (afterIndex === null) continue
    items.push({ kind: 'missing', criterionId, afterIndex })
  }

  const sortKey = (item: RenderItem) => (item.kind === 'sentence' ? item.index : item.afterIndex + 0.5)
  return items.sort((a, b) => sortKey(a) - sortKey(b))
}

export function GradedView({
  studentName,
  classId,
  assignmentPrompt,
  essayText,
  gradedEssay,
  onFinish,
  onNextEssay,
}: GradedViewProps) {
  const { criteria: rubric, sentences, sectionOf, citingCriteria } = gradedEssay
  const [active, setActive] = useState(rubric[0]?.id ?? '')
  const [overrides, setOverrides] = useState<Record<string, number>>({})
  const [disputes, setDisputes] = useState<Record<string, DisputeState>>({})
  const [finished, setFinished] = useState(false)
  const [finishedAt, setFinishedAt] = useState<string | null>(null)

  const byId = (id: string) => rubric.find((r) => r.id === id)!

  const effScore = (id: string) => {
    if (overrides[id] !== undefined) return overrides[id]
    const item = byId(id)
    return item.missing ? 0 : (item.score as number)
  }

  const scrollToElement = (elementId: string) => {
    const el = document.getElementById(elementId)
    el?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
  }

  const jumpToEssay = (id: string) => {
    setActive(id)
    scrollToElement(`para-${id}`)
  }

  const jumpToCard = (id: string) => {
    setActive(id)
    scrollToElement(`note-${id}`)
  }

  const openDispute = (id: string) => {
    setDisputes((d) => ({
      ...d,
      [id]: d[id] ? { ...d[id], open: true } : EMPTY_DISPUTE,
    }))
  }

  const sendMessage = (id: string, text: string) => {
    const priorMessages = disputes[id]?.messages ?? []
    const outgoing: DisputeMessage = { role: 'teacher', text }

    setDisputes((d) => {
      const prev = d[id] ?? EMPTY_DISPUTE
      return {
        ...d,
        [id]: { ...prev, open: true, messages: [...prev.messages, outgoing], sending: true },
      }
    })

    const item = byId(id)
    disputeTurn({
      essayId: gradedEssay.essayId,
      essayText,
      assignmentPrompt,
      original: item,
      messages: [...priorMessages, outgoing],
    })
      .then((result) => {
        setDisputes((d) => {
          const prev = d[id]
          return {
            ...d,
            [id]: {
              ...prev,
              messages: [...prev.messages, { role: 'claude', text: result.message }],
              sending: false,
              proposedScore: result.proposal?.score ?? prev.proposedScore,
              proposalRawGradeId: result.proposalRawGradeId ?? prev.proposalRawGradeId,
            },
          }
        })
      })
      .catch((err: unknown) => {
        if (err instanceof DisputeRequestError) {
          console.error(err.message, err.cause)
        }
        setDisputes((d) => {
          const prev = d[id]
          return {
            ...d,
            [id]: {
              ...prev,
              messages: [
                ...prev.messages,
                { role: 'claude', text: "Something went wrong reaching the grading service. Try again." },
              ],
              sending: false,
            },
          }
        })
      })
  }

  const resolveDisputeWith = (id: string, resolution: 'corrected' | 'kept_original', score?: number) => {
    setDisputes((d) => ({ ...d, [id]: { ...d[id], resolving: true } }))

    resolveDispute({
      essayId: gradedEssay.essayId,
      criterionId: id,
      resolution,
      rawGradeId: resolution === 'corrected' ? (disputes[id]?.proposalRawGradeId ?? undefined) : undefined,
    })
      .then(() => {
        if (score !== undefined) {
          setOverrides((o) => ({ ...o, [id]: score }))
        }
        setDisputes((d) => ({ ...d, [id]: { ...d[id], resolved: true, resolving: false } }))
      })
      .catch((err: unknown) => {
        if (err instanceof DisputeRequestError) {
          console.error(err.message, err.cause)
        }
        // Left unresolved on failure — Finish grading stays blocked, same as any
        // other open dispute, rather than silently pretending the save succeeded.
        setDisputes((d) => ({ ...d, [id]: { ...d[id], resolving: false } }))
      })
  }

  const saveCorrection = (id: string, score: number) => resolveDisputeWith(id, 'corrected', score)

  const keepOriginal = (id: string) => resolveDisputeWith(id, 'kept_original')

  const openUnresolvedCount = Object.values(disputes).filter((d) => d.open && !d.resolved).length
  const correctedCount = Object.keys(overrides).length
  const unaddressedMissingCount = rubric.filter((r) => r.missing && overrides[r.id] === undefined).length
  const overall = (rubric.reduce((sum, r) => sum + effScore(r.id), 0) / rubric.length).toFixed(1)

  const finish = () => {
    if (openUnresolvedCount > 0) return
    setFinished(true)
    setFinishedAt(new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }))
    onFinish()
  }

  return (
    <div>
      <RubricKey
        items={rubric.map((r) => ({
          id: r.id,
          label: r.label,
          group: r.group,
          score: overrides[r.id] ?? r.score,
          missing: r.missing && overrides[r.id] === undefined,
        }))}
        activeId={active}
        onSelect={jumpToEssay}
      />

      <div className="relative rounded bg-paper px-10 py-12 text-ink shadow-sm">
        <div className="absolute -right-3 -top-4 rotate-[-6deg] rounded bg-card px-3 py-1.5 text-cream">
          <span className="font-flourish text-2xl font-bold">{overall}</span>
          <span className="ml-1 text-[10px] tracking-wide opacity-75">/ 4 avg</span>
        </div>

        <p className="mb-2 text-xs uppercase tracking-[0.15em] text-muted">
          {studentName} · {classId}
        </p>
        <h1 className="mb-8 pr-20 font-serif text-3xl font-semibold leading-tight">{assignmentPrompt}</h1>

        <div className="font-serif text-[1.0625rem] leading-loose">
          {(() => {
            const usedParaIds = new Set<string>()
            const markParaId = (criterionId: string) => {
              if (usedParaIds.has(criterionId)) return false
              usedParaIds.add(criterionId)
              return true
            }

            return SECTIONS.map((section) => {
              const sectionIndices = Object.entries(sectionOf)
                .filter(([, s]) => s === section)
                .map(([idx]) => Number(idx))
                .sort((a, b) => a - b)
              const missingInSection = CRITERION_ORDER_BY_SECTION[section].filter(
                (id) => rubric.find((r) => r.id === id)?.missing ?? false,
              )
              const renderItems = buildSectionRenderItems(section, sectionIndices, missingInSection, rubric, sectionOf)

              return (
                <p key={section} className="mb-5">
                  {renderItems.map((item) => {
                    if (item.kind === 'missing') {
                      const criterion = byId(item.criterionId)
                      const showId = markParaId(item.criterionId)
                      return (
                        <span key={`missing-${item.criterionId}`} id={showId ? `para-${item.criterionId}` : undefined}>
                          <EssayTag
                            label={criterion.label}
                            missing
                            score={null}
                            isActive={active === item.criterionId}
                            onClick={() => jumpToCard(item.criterionId)}
                          />
                        </span>
                      )
                    }

                    const sentence = sentences.find((s) => s.index === item.index)!
                    const citingIds = citingCriteria[item.index] ?? []
                    return (
                      <span key={`sentence-${item.index}`}>
                        {citingIds.map((criterionId) => {
                          const criterion = byId(criterionId)
                          const showId = markParaId(criterionId)
                          return (
                            <span key={criterionId} id={showId ? `para-${criterionId}` : undefined}>
                              <EssayTag
                                label={criterion.label}
                                missing={false}
                                score={criterion.score}
                                isActive={active === criterionId}
                                onClick={() => jumpToCard(criterionId)}
                              />
                            </span>
                          )
                        })}
                        {sentence.text}
                      </span>
                    )
                  })}
                </p>
              )
            })
          })()}
        </div>
      </div>

      <div className="mt-8 flex flex-col gap-4">
        {rubric.map((item) => {
          const dispute = disputes[item.id]
          return (
            <div key={item.id} id={`note-${item.id}`}>
              <CriterionCard
                label={item.label}
                group={item.group}
                score={item.score}
                missing={item.missing}
                strengths={item.strengths}
                critiques={item.critiques}
                reasoning={item.reasoning}
                overriddenScore={overrides[item.id]}
                onDisagree={() => openDispute(item.id)}
                disputeSlot={
                  dispute?.open ? (
                    <DisputeThread
                      messages={dispute.messages}
                      proposedScore={dispute.proposedScore}
                      isSending={dispute.sending}
                      isResolved={dispute.resolved}
                      resolvedSummary={
                        overrides[item.id] !== undefined
                          ? `Resolved — score corrected to ${overrides[item.id]}/4.`
                          : 'Resolved — original score kept.'
                      }
                      onSend={(text) => sendMessage(item.id, text)}
                      onSaveCorrection={(score) => saveCorrection(item.id, score)}
                      onKeepOriginal={() => keepOriginal(item.id)}
                    />
                  ) : undefined
                }
              />
            </div>
          )
        })}
      </div>

      <FinishGradingBar
        totalCriteria={rubric.length}
        correctedCount={correctedCount}
        openUnresolvedCount={openUnresolvedCount}
        unaddressedMissingCount={unaddressedMissingCount}
        isFinished={finished}
        studentName={studentName}
        finishedAt={finishedAt ?? undefined}
        onFinish={finish}
        onNextEssay={onNextEssay}
      />

      <BackToTop />
    </div>
  )
}
