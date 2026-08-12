export type Tier = 'strong' | 'solid' | 'developing' | 'missing'

export const TIER_LABEL: Record<Exclude<Tier, 'missing'>, string> = {
  strong: 'Strong',
  solid: 'Solid',
  developing: 'Developing',
}

export const TIER_CLASSES: Record<Tier, string> = {
  strong: 'bg-tier-strong text-tier-strong-text',
  solid: 'bg-tier-solid text-tier-solid-text',
  developing: 'bg-tier-developing text-tier-developing-text',
  missing: 'bg-tier-missing text-tier-missing-text',
}

export function tierFor(score: number): Exclude<Tier, 'missing'> {
  if (score >= 4) return 'strong'
  if (score === 3) return 'solid'
  return 'developing'
}
