import { useState } from 'react'

export interface PasteValues {
  studentName: string
  essayText: string
}

export interface PasteScreenProps {
  onSubmit: (values: PasteValues) => void
}

export function PasteScreen({ onSubmit }: PasteScreenProps) {
  const [studentName, setStudentName] = useState('')
  const [essayText, setEssayText] = useState('')

  const canSubmit = studentName.trim() !== '' && essayText.trim() !== ''

  const handleSubmit = () => {
    if (!canSubmit) return
    onSubmit({ studentName, essayText })
  }

  return (
    <div className="relative overflow-hidden rounded bg-paper px-10 py-12 text-ink shadow-sm">
      <p className="mb-2 text-xs uppercase tracking-[0.15em] text-muted">New essay</p>
      <h1 className="mb-6 font-serif text-2xl font-semibold">Next essay</h1>

      <input
        value={studentName}
        onChange={(e) => setStudentName(e.target.value)}
        placeholder="Student name"
        className="mb-3 w-full rounded border border-field-border bg-field px-3 py-2.5 text-sm text-ink outline-none"
      />
      <textarea
        value={essayText}
        onChange={(e) => setEssayText(e.target.value)}
        placeholder="Paste the essay text here…"
        rows={12}
        className="w-full resize-none rounded border border-field-border bg-field px-4 py-4 font-serif text-[1.0625rem] leading-relaxed text-ink outline-none"
      />

      <div className="mt-5 flex justify-end">
        <button
          type="button"
          disabled={!canSubmit}
          onClick={handleSubmit}
          className="rounded bg-card px-5 py-2.5 text-sm font-semibold uppercase tracking-wide text-cream disabled:cursor-not-allowed disabled:opacity-35"
        >
          Grade this essay
        </button>
      </div>
    </div>
  )
}
