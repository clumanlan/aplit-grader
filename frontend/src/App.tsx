import { useRef, useState } from 'react'
import { SetupScreen, type SetupValues } from './components/SetupScreen'
import { SessionBar, type Session } from './components/SessionBar'
import { PasteScreen, type PasteValues } from './components/PasteScreen'
import { LoadingScreen } from './components/LoadingScreen'
import { ErrorScreen } from './components/ErrorScreen'
import { GradedView } from './components/GradedView'
import { DEMO_RUBRIC, DEMO_ESSAY } from './fixtures/demoGrading'

const SETUP_CRITERIA = {
  standalone: [
    { id: 'thesis', label: 'Thesis' },
    { id: 'conclusion', label: 'Conclusion' },
  ],
  groups: [
    {
      group: 'Body ¶1',
      items: [
        { id: 'bp1-claim', label: 'Claim' },
        { id: 'bp1-evidence-1', label: 'Evidence 1' },
        { id: 'bp1-reasoning-1', label: 'Reasoning 1' },
        { id: 'bp1-evidence-2', label: 'Evidence 2' },
        { id: 'bp1-reasoning-2', label: 'Reasoning 2' },
        { id: 'bp1-synthesis', label: 'Synthesis' },
      ],
    },
    {
      group: 'Body ¶2',
      items: [
        { id: 'bp2-claim', label: 'Claim' },
        { id: 'bp2-evidence-1', label: 'Evidence 1' },
        { id: 'bp2-reasoning-1', label: 'Reasoning 1' },
        { id: 'bp2-evidence-2', label: 'Evidence 2' },
        { id: 'bp2-reasoning-2', label: 'Reasoning 2' },
        { id: 'bp2-synthesis', label: 'Synthesis' },
      ],
    },
  ],
}
const CLASSES = ['Period 3 — AP Lit', 'Period 5 — AP Lit', 'Period 7 — AP Lit']
const GRADING_DURATION_MS = 3000

function sectionsLabel(values: SetupValues): string {
  if (values.fullEssay) return 'Full essay'
  return values.selectedCriteria.join(', ')
}

type EssayView = 'paste' | 'loading' | 'error' | 'graded'

function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [setupValues, setSetupValues] = useState<SetupValues | null>(null)
  const [isAdjusting, setIsAdjusting] = useState(false)
  const [essay, setEssay] = useState<PasteValues | null>(null)
  const [view, setView] = useState<EssayView>('paste')
  const gradingTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  const startGrading = () => {
    setView('loading')
    gradingTimeout.current = setTimeout(() => setView('graded'), GRADING_DURATION_MS)
  }

  const handleStartSession = (values: SetupValues) => {
    setSetupValues(values)
    setSession({
      sections: sectionsLabel(values),
      classId: values.classId,
      prompt: values.prompt,
      setupAt: new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }),
      count: session?.count ?? 0,
    })
    setIsAdjusting(false)
  }

  const handleAdjustAssignment = () => setIsAdjusting(true)
  const handleCancelAdjust = () => setIsAdjusting(false)

  const handleNewAssignment = () => {
    if (gradingTimeout.current) clearTimeout(gradingTimeout.current)
    setSession(null)
    setSetupValues(null)
    setIsAdjusting(false)
    setEssay(null)
    setView('paste')
  }

  const handleGradeEssay = (values: PasteValues) => {
    setEssay(values)
    startGrading()
  }

  const handleFinish = () => {
    setSession((s) => (s ? { ...s, count: s.count + 1 } : s))
  }

  const handleNextEssay = () => {
    if (gradingTimeout.current) clearTimeout(gradingTimeout.current)
    setEssay(null)
    setView('paste')
  }

  const isGraded = session && !isAdjusting && view === 'graded'

  return (
    <div className="min-h-screen w-full bg-chrome">
      <div className="border-b border-black/10">
        <div className="mx-auto max-w-6xl px-6 py-3">
          <span className="font-sans text-xs font-bold uppercase tracking-[0.18em] text-chrome-text-strong">
            AP Lit Essay Grader
          </span>
        </div>
      </div>
      <div className={isGraded ? 'mx-auto max-w-6xl px-6 py-10' : 'mx-auto max-w-3xl px-6 py-10'}>
        {(!session || isAdjusting) && (
          <SetupScreen
            criteria={SETUP_CRITERIA}
            classes={CLASSES}
            initialValues={isAdjusting ? (setupValues ?? undefined) : undefined}
            onSubmit={handleStartSession}
            onCancel={isAdjusting ? handleCancelAdjust : undefined}
          />
        )}
        {session && !isAdjusting && (
          <>
            <SessionBar
              session={session}
              onAdjustAssignment={handleAdjustAssignment}
              onNewAssignment={handleNewAssignment}
            />

            {view === 'paste' && <PasteScreen onSubmit={handleGradeEssay} />}

            {(view === 'loading' || view === 'error') && essay && (
              <div className="flex flex-col gap-6">
                <div className="rounded bg-paper px-10 py-12 text-ink shadow-sm">
                  <p className="mb-2 text-xs uppercase tracking-[0.15em] text-muted">
                    {essay.studentName} · {session.classId}
                  </p>
                  <h1 className="mb-8 font-serif text-2xl font-semibold leading-tight">
                    {session.prompt}
                  </h1>
                  <div className="whitespace-pre-line font-serif text-[1.0625rem] leading-loose opacity-45">
                    {essay.essayText}
                  </div>
                </div>
                {view === 'error' ? (
                  <ErrorScreen onRetry={startGrading} />
                ) : (
                  <>
                    <LoadingScreen />
                    <div className="text-right">
                      <button
                        type="button"
                        onClick={() => {
                          if (gradingTimeout.current) clearTimeout(gradingTimeout.current)
                          setView('error')
                        }}
                        className="text-[10px] uppercase tracking-wide text-chrome-text-strong/35"
                      >
                        Preview: simulate failure
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            {view === 'graded' && essay && (
              <GradedView
                studentName={essay.studentName}
                classId={session.classId}
                rubric={DEMO_RUBRIC}
                essay={DEMO_ESSAY}
                onFinish={handleFinish}
                onNextEssay={handleNextEssay}
              />
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default App
