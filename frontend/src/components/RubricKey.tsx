import { TIER_CLASSES, tierFor } from '../lib/tier'

export interface RubricKeyItem {
  id: string
  label: string
  group: string | null
  score: number | null
  missing: boolean
}

export interface RubricKeyProps {
  items: RubricKeyItem[]
  activeId: string
  onSelect: (id: string) => void
}

function groupOrder(items: RubricKeyItem[]) {
  const seen: (string | null)[] = []
  for (const item of items) {
    if (!seen.includes(item.group)) seen.push(item.group)
  }
  return seen
}

export function RubricKey({ items, activeId, onSelect }: RubricKeyProps) {
  return (
    <div className="mb-6 space-y-3">
      <p className="mb-1 text-xs uppercase tracking-[0.15em] text-chrome-text-muted">Rubric key</p>
      {groupOrder(items).map((group) => (
        <div key={group ?? 'standalone'}>
          {group && (
            <p className="mb-1 text-[10px] uppercase tracking-wide text-chrome-text-muted/70">{group}</p>
          )}
          <div className="flex flex-wrap gap-2">
            {items
              .filter((item) => item.group === group)
              .map((item) => {
                const tier = item.missing ? 'missing' : tierFor(item.score as number)
                const isActive = item.id === activeId
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onSelect(item.id)}
                    aria-current={isActive}
                    className={`flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-semibold ${
                      isActive ? 'bg-card text-cream' : 'bg-card/6 text-chrome-text-muted'
                    }`}
                  >
                    {item.label}{' '}
                    <span
                      className={`flex h-4 w-4 items-center justify-center rounded-full text-[10px] ${TIER_CLASSES[tier]}`}
                    >
                      {item.missing ? '!' : item.score}
                    </span>
                  </button>
                )
              })}
          </div>
        </div>
      ))}
    </div>
  )
}
