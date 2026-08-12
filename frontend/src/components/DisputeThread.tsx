import { useState } from 'react'

export interface DisputeMessage {
  role: 'teacher' | 'claude'
  text: string
}

export interface DisputeThreadProps {
  messages: DisputeMessage[]
  proposedScore: number | null
  isSending: boolean
  isResolved: boolean
  resolvedSummary?: string
  onSend: (text: string) => void
  onSaveCorrection: (score: number) => void
  onKeepOriginal: () => void
}

export function DisputeThread({
  messages,
  proposedScore,
  isSending,
  isResolved,
  resolvedSummary,
  onSend,
  onSaveCorrection,
  onKeepOriginal,
}: DisputeThreadProps) {
  const [draft, setDraft] = useState('')
  const [pickedScore, setPickedScore] = useState<number | null>(null)

  const canSend = draft.trim() !== ''

  const handleSend = () => {
    if (!canSend) return
    onSend(draft.trim())
    setDraft('')
  }

  return (
    <div>
      <p className="mb-3 text-[10px] uppercase tracking-wide text-card-muted">Discuss this grade</p>

      <div className="mb-3 space-y-2.5">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'teacher' ? 'flex justify-end' : 'flex justify-start'}>
            <div
              className={`max-w-[85%] rounded px-3 py-2 text-sm leading-relaxed ${
                m.role === 'teacher' ? 'bg-cream text-ink' : 'bg-white/8 text-cream'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {isSending && (
          <div className="flex justify-start">
            <div className="rounded bg-white/8 px-3 py-2 text-sm text-cream/60">Thinking…</div>
          </div>
        )}
      </div>

      {isResolved ? (
        <p className="text-xs text-card-muted">{resolvedSummary}</p>
      ) : (
        <>
          <div className="mb-3 flex gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="What feels off about this score?"
              className="flex-1 rounded bg-white/8 px-3 py-2 text-sm text-cream outline-none"
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!canSend}
              className="rounded bg-cream px-3 py-2 text-xs font-semibold text-card disabled:opacity-40"
            >
              Send
            </button>
          </div>

          {proposedScore != null && (
            <div className="rounded bg-white/6 px-3 py-3">
              <p className="mb-2 text-[10px] uppercase tracking-wide text-card-muted">Finalize your score</p>
              <div className="mb-3 flex gap-2">
                {[1, 2, 3, 4].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setPickedScore(n)}
                    className={`h-9 w-9 rounded-full text-sm font-semibold ${
                      pickedScore === n ? 'bg-cream text-card' : 'bg-white/10 text-cream'
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={pickedScore == null}
                  onClick={() => pickedScore != null && onSaveCorrection(pickedScore)}
                  className="flex-1 rounded bg-cream py-2 text-xs font-semibold text-card disabled:opacity-40"
                >
                  Save correction
                </button>
                <button
                  type="button"
                  onClick={onKeepOriginal}
                  className="rounded px-3 py-2 text-xs font-semibold text-card-muted"
                >
                  Keep original
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
