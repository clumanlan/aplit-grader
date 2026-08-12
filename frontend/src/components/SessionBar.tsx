export interface Session {
  sections: string
  classId: string
  prompt: string
  setupAt: string
  count: number
}

export interface SessionBarProps {
  session: Session
  onAdjustAssignment: () => void
  onNewAssignment: () => void
}

function truncatedPrompt(prompt: string) {
  return prompt.length > 40 ? `${prompt.slice(0, 40)}…` : prompt
}

export function SessionBar({ session, onAdjustAssignment, onNewAssignment }: SessionBarProps) {
  return (
    <div className="mb-6 rounded bg-card px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-cream/80">
            Set up {session.setupAt} · {session.count} essay{session.count === 1 ? '' : 's'} graded
          </p>
          <div className="flex flex-wrap gap-2">
            <span className="rounded bg-white/10 px-2.5 py-1 text-xs font-semibold text-cream">
              {session.sections}
            </span>
            <span className="rounded bg-white/10 px-2.5 py-1 text-xs font-semibold text-cream">
              {session.classId}
            </span>
            <span
              className="max-w-xs truncate rounded bg-white/10 px-2.5 py-1 text-xs font-semibold text-cream"
              title={session.prompt}
            >
              {truncatedPrompt(session.prompt)}
            </span>
          </div>
        </div>
        <div className="flex flex-shrink-0 gap-2">
          <button
            type="button"
            onClick={onAdjustAssignment}
            className="rounded bg-white/10 px-3 py-1.5 text-xs font-semibold text-cream"
          >
            Adjust assignment
          </button>
          <button
            type="button"
            onClick={onNewAssignment}
            className="rounded bg-cream px-3 py-1.5 text-xs font-semibold text-card"
          >
            New assignment
          </button>
        </div>
      </div>
    </div>
  )
}
