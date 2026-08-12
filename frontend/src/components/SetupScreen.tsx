import { useState } from 'react'

export interface SetupCriterion {
  id: string
  label: string
}

export interface SetupCriteriaGroup {
  group: string
  items: SetupCriterion[]
}

export interface SetupCriteria {
  standalone: SetupCriterion[]
  groups: SetupCriteriaGroup[]
}

export interface SetupValues {
  fullEssay: boolean
  selectedCriteria: string[]
  prompt: string
  classId: string
}

export interface SetupScreenProps {
  criteria: SetupCriteria
  classes: string[]
  initialValues?: SetupValues
  onSubmit: (values: SetupValues) => void
  onCancel?: () => void
}

function chipClasses(selected: boolean) {
  return selected
    ? 'rounded border border-card bg-card px-3 py-1.5 text-sm font-medium text-cream'
    : 'rounded border border-field-border bg-white px-3 py-1.5 text-sm font-medium text-ink'
}

export function SetupScreen({ criteria, classes, initialValues, onSubmit, onCancel }: SetupScreenProps) {
  const isEditing = initialValues !== undefined
  const [fullEssay, setFullEssay] = useState(initialValues?.fullEssay ?? true)
  const [selectedCriteria, setSelectedCriteria] = useState<Set<string>>(
    new Set(initialValues?.selectedCriteria ?? []),
  )
  const [prompt, setPrompt] = useState(initialValues?.prompt ?? '')
  const [classId, setClassId] = useState(initialValues?.classId ?? '')

  const canSubmit = (fullEssay || selectedCriteria.size > 0) && prompt.trim() !== '' && classId !== ''

  const toggleCriterion = (id: string) => {
    setFullEssay(false)
    setSelectedCriteria((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleSubmit = () => {
    if (!canSubmit) return
    onSubmit({
      fullEssay,
      selectedCriteria: [...selectedCriteria],
      prompt: prompt.trim(),
      classId,
    })
  }

  return (
    <div className="rounded bg-paper px-8 py-8 text-ink shadow-sm">
      <p className="mb-1 text-xs uppercase tracking-[0.15em] text-muted">
        {isEditing ? 'Edit assignment' : 'New assignment'}
      </p>
      <h1 className="mb-1 font-serif text-2xl font-semibold">Set this up once</h1>
      <p className="mb-8 text-sm text-muted">
        This stays the same for every essay in this batch. You can change it anytime from the
        grading screen.
      </p>

      <div className="mb-8">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide">1 · What are we grading?</p>

        <div className="mb-3 inline-flex flex-wrap items-center gap-4 rounded bg-field p-3">
          <button
            type="button"
            onClick={() => {
              setFullEssay(true)
              setSelectedCriteria(new Set())
            }}
            aria-pressed={fullEssay}
            className={`rounded border px-4 py-2 text-sm font-semibold ${
              fullEssay ? 'border-card bg-card text-cream' : 'border-field-border bg-transparent text-ink'
            }`}
          >
            Full essay
          </button>
          <span className="text-xs text-muted">or pick specific criteria →</span>
        </div>

        <div
          className="space-y-3 rounded bg-field p-4 transition-opacity"
          style={{ opacity: fullEssay ? 0.45 : 1 }}
        >
          <div className="flex flex-wrap gap-2">
            {criteria.standalone.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => toggleCriterion(c.id)}
                aria-pressed={selectedCriteria.has(c.id)}
                className={chipClasses(selectedCriteria.has(c.id))}
              >
                {c.label}
              </button>
            ))}
          </div>
          {criteria.groups.map((g) => (
            <div key={g.group}>
              <p className="mb-1.5 text-xs uppercase tracking-wide text-muted">{g.group}</p>
              <div className="flex flex-wrap gap-2">
                {g.items.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => toggleCriterion(c.id)}
                    aria-pressed={selectedCriteria.has(c.id)}
                    className={chipClasses(selectedCriteria.has(c.id))}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-8">
        <label htmlFor="prompt" className="mb-3 block text-xs font-semibold uppercase tracking-wide">
          2 · Assignment prompt
        </label>
        <textarea
          id="prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. Analyze how Fitzgerald uses a symbol to develop a theme in The Great Gatsby."
          rows={3}
          className="w-full resize-none rounded border border-field-border bg-field px-3 py-2.5 text-sm text-ink outline-none"
        />
      </div>

      <div className="mb-9">
        <label htmlFor="class" className="mb-3 block text-xs font-semibold uppercase tracking-wide">
          3 · Class
        </label>
        <select
          id="class"
          value={classId}
          onChange={(e) => setClassId(e.target.value)}
          className="w-full rounded border border-field-border bg-field px-3 py-2.5 text-sm text-ink outline-none"
        >
          <option value="">Choose a class…</option>
          {classes.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      <div className="flex justify-end gap-3">
        {isEditing && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded px-4 py-2 text-sm font-semibold text-muted"
          >
            Cancel
          </button>
        )}
        <button
          type="button"
          disabled={!canSubmit}
          onClick={handleSubmit}
          className="rounded bg-card px-5 py-2.5 text-sm font-semibold uppercase tracking-wide text-cream disabled:cursor-not-allowed disabled:opacity-35"
        >
          {isEditing ? 'Save changes' : 'Start grading'}
        </button>
      </div>
    </div>
  )
}
