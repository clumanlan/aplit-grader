import { useState } from 'react'
import { TIER_CLASSES, TIER_LABEL, tierFor, type Tier } from '../lib/tier'

export interface CriterionCardProps {
  label: string
  group: string | null
  score: number | null
  missing: boolean
  strengths: string[]
  critiques: string[]
  reasoning: string
  overriddenScore?: number
  onDisagree?: () => void
  disputeSlot?: React.ReactNode
}

export function CriterionCard({
  label,
  group,
  score,
  missing,
  strengths,
  critiques,
  reasoning,
  overriddenScore,
  onDisagree,
  disputeSlot,
}: CriterionCardProps) {
  const [showReasoning, setShowReasoning] = useState(false)

  const isOverridden = overriddenScore !== undefined
  const displayMissing = missing && !isOverridden
  const displayScore = overriddenScore ?? score
  const tier: Tier = displayMissing ? 'missing' : tierFor(displayScore as number)

  return (
    <div className="rounded bg-card px-5 py-5">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-card-label">
          {group ? `${group} · ` : ''}
          {label}
        </span>
        <span className={`flex-shrink-0 rounded px-2 py-0.5 text-xs font-semibold ${TIER_CLASSES[tier]}`}>
          {displayMissing ? '! Missing' : `${displayScore} / 4 · ${TIER_LABEL[tier as Exclude<Tier, 'missing'>]}`}
        </span>
      </div>

      {isOverridden && (
        <p className="mb-3 text-[11px] text-card-muted">
          {missing
            ? `Flagged as missing by Claude — scored ${overriddenScore}/4 by you`
            : `Originally ${score}/4 by Claude — corrected to ${overriddenScore}/4 by you`}
        </p>
      )}
      {!isOverridden && <div className="mb-3" />}

      <p className="mb-2 text-[10px] uppercase tracking-wide text-card-muted">What they did well</p>
      {displayMissing && strengths.length === 0 ? (
        <p className="mb-5 text-sm italic text-cream/55">
          Nothing to point to yet — no reasoning sentence is present.
        </p>
      ) : (
        <ul className="mb-5 space-y-2.5">
          {strengths.map((s, i) => (
            <li key={i} className="flex gap-2.5 text-[0.9375rem] leading-relaxed text-cream">
              <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-tier-strong" />
              <span>{s}</span>
            </li>
          ))}
        </ul>
      )}

      <p className="mb-2 text-[10px] uppercase tracking-wide text-card-muted">
        {displayMissing ? "What's missing" : 'What would strengthen it'}
      </p>
      <ul className="mb-4 space-y-2.5">
        {critiques.map((c, i) => (
          <li key={i} className="flex gap-2.5 text-[0.9375rem] leading-relaxed text-cream">
            <span
              className={`mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full ${displayMissing ? 'bg-tier-missing' : 'bg-tier-solid'}`}
            />
            <span>{c}</span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={() => setShowReasoning((v) => !v)}
        className="flex w-full items-center gap-1.5 border-t border-white/10 pt-3 text-left text-xs text-card-muted"
      >
        <span className={showReasoning ? 'inline-block rotate-90 transition-transform' : 'inline-block transition-transform'}>
          ▸
        </span>
        {showReasoning ? "Hide model's reasoning" : "Show model's reasoning"}
      </button>
      {showReasoning && (
        <p className="mt-2 text-xs italic leading-relaxed text-cream/70">{reasoning}</p>
      )}

      <div className="mt-4 border-t border-white/10 pt-4">
        {disputeSlot ?? (
          <button
            type="button"
            onClick={onDisagree}
            className="w-full rounded bg-white/8 py-2 text-xs font-semibold text-cream"
          >
            Disagree with this score?
          </button>
        )}
      </div>
    </div>
  )
}
