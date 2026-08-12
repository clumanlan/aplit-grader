import { TIER_CLASSES, tierFor } from '../lib/tier'

export interface EssayTagProps {
  label: string
  missing: boolean
  score: number | null
  isActive: boolean
  onClick: () => void
}

export function EssayTag({ label, missing, score, isActive, onClick }: EssayTagProps) {
  if (missing) {
    return (
      <button
        type="button"
        onClick={onClick}
        aria-label={`! ${label} missing`}
        className="mr-1 rounded border-[1.5px] border-dashed border-tier-missing px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-tier-missing"
      >
        ! {label} missing
      </button>
    )
  }

  const tier = tierFor(score as number)

  return (
    <button
      type="button"
      onClick={onClick}
      className={`align-super mr-1 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
        isActive ? 'bg-card text-cream' : TIER_CLASSES[tier]
      }`}
    >
      {label}
    </button>
  )
}
