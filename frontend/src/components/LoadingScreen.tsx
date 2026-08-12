import { useEffect, useState } from 'react'

const STATUS_MESSAGES = [
  'Reading the thesis…',
  "Checking the first body paragraph's evidence…",
  'Weighing the reasoning…',
  'Looking at synthesis across paragraphs…',
  'Reading the conclusion…',
]

export function LoadingScreen() {
  const [elapsed, setElapsed] = useState(0)
  const [msgIndex, setMsgIndex] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const id = setInterval(
      () => setMsgIndex((i) => (i + 1) % STATUS_MESSAGES.length),
      3200,
    )
    return () => clearInterval(id)
  }, [])

  return (
    <div className="rounded bg-card px-5 py-5">
      <p className="mb-3 text-xs uppercase tracking-wide text-cream/80">Grading in progress</p>
      <p key={msgIndex} className="text-[0.9375rem] leading-relaxed text-cream">
        {STATUS_MESSAGES[msgIndex]}
      </p>
      <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-4">
        <span className="text-xs text-cream/55">{elapsed}s elapsed</span>
        {elapsed >= 20 && (
          <span className="max-w-[10rem] text-right text-xs text-cream/55">
            First grade of a session can take up to a minute.
          </span>
        )}
      </div>
    </div>
  )
}
