export interface FinishGradingBarProps {
  totalCriteria: number
  correctedCount: number
  openUnresolvedCount: number
  unaddressedMissingCount: number
  isFinished: boolean
  studentName: string
  finishedAt?: string
  onFinish: () => void
  onNextEssay: () => void
}

export function FinishGradingBar({
  totalCriteria,
  correctedCount,
  openUnresolvedCount,
  unaddressedMissingCount,
  isFinished,
  studentName,
  finishedAt,
  onFinish,
  onNextEssay,
}: FinishGradingBarProps) {
  if (isFinished) {
    return (
      <div className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded bg-card px-6 py-5">
        <p className="text-[0.9375rem] text-cream">
          <span className="font-bold text-tier-strong">✓</span> Grades saved for {studentName} —{' '}
          {finishedAt}.
        </p>
        <button
          type="button"
          onClick={onNextEssay}
          className="rounded bg-cream px-4 py-2 text-xs font-semibold uppercase tracking-wide text-card"
        >
          Next essay →
        </button>
      </div>
    )
  }

  const acceptedAsIsCount = totalCriteria - correctedCount
  const summary =
    correctedCount > 0
      ? `${correctedCount} ${correctedCount > 1 ? 'criteria' : 'criterion'} corrected · ${acceptedAsIsCount} accepted as graded.`
      : `All ${totalCriteria} criteria accepted as graded — no corrections made.`

  return (
    <div className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded bg-card px-6 py-5">
      <div>
        <p className="text-[0.9375rem] font-semibold text-cream">Ready to finish grading this essay?</p>
        <p className="mt-1 text-xs text-card-muted">
          {summary}
          {openUnresolvedCount > 0 && (
            <span className="text-[#E3B7AB]">
              {' '}
              You have {openUnresolvedCount} open discussion{openUnresolvedCount > 1 ? 's' : ''} to
              resolve first.
            </span>
          )}
          {openUnresolvedCount === 0 && unaddressedMissingCount > 0 && (
            <span className="text-[#E3B7AB]">
              {' '}
              {unaddressedMissingCount} {unaddressedMissingCount > 1 ? 'criteria' : 'criterion'} still
              flagged as missing — you can finish anyway, or discuss it first.
            </span>
          )}
        </p>
      </div>
      <button
        type="button"
        disabled={openUnresolvedCount > 0}
        onClick={onFinish}
        className="rounded bg-cream px-5 py-2.5 text-sm font-semibold uppercase tracking-wide text-card disabled:cursor-not-allowed disabled:opacity-40"
      >
        Finish grading
      </button>
    </div>
  )
}
