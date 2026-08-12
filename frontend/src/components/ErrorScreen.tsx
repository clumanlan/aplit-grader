export interface ErrorScreenProps {
  onRetry: () => void
}

export function ErrorScreen({ onRetry }: ErrorScreenProps) {
  return (
    <div className="rounded bg-card px-5 py-5">
      <div className="mb-2 flex items-center gap-2">
        <span className="h-2 w-2 flex-shrink-0 rounded-full bg-tier-developing" />
        <p className="text-xs uppercase tracking-wide text-[#E3B7AB]">Grading failed</p>
      </div>
      <p className="text-[0.9375rem] leading-relaxed text-cream">
        The grading model didn't respond in time. Nothing was lost — the essay is still here.
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 w-full rounded bg-tier-developing px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[#2E1712]"
      >
        Try again
      </button>
    </div>
  )
}
