import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { GradedView, type RubricItem } from './GradedView'

const RUBRIC: RubricItem[] = [
  {
    id: 'thesis',
    label: 'Thesis',
    group: null,
    score: 3,
    missing: false,
    strengths: ['Clear claim.'],
    critiques: ['Push further.'],
    reasoning: 'Held at 3 because...',
  },
  {
    id: 'bp1-reasoning-1',
    label: 'Reasoning 1',
    group: 'Body ¶1',
    score: null,
    missing: true,
    strengths: [],
    critiques: ['Add a sentence connecting evidence to claim.'],
    reasoning: 'Nothing follows the evidence.',
  },
]

const ESSAY = {
  title: 'Test Essay',
  paras: [
    [{ id: 'thesis', text: 'This is the thesis sentence.' }],
    [{ id: 'bp1-reasoning-1', missing: true }],
  ],
}

function renderGradedView(onFinish = vi.fn(), onNextEssay = vi.fn()) {
  return render(
    <GradedView
      studentName="Jordan"
      classId="Period 3 — AP Lit"
      rubric={RUBRIC}
      essay={ESSAY}
      onFinish={onFinish}
      onNextEssay={onNextEssay}
    />,
  )
}

describe('GradedView', () => {
  it('opens a dispute, sends a message, and shows the simulated Claude reply with a proposed score', async () => {
    const user = userEvent.setup()
    renderGradedView()

    const disagreeButtons = screen.getAllByRole('button', { name: /disagree with this score/i })
    await user.click(disagreeButtons[0])

    await user.type(
      screen.getByPlaceholderText(/what feels off about this score/i),
      'This feels low for the evidence given.',
    )
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(screen.getByText('This feels low for the evidence given.')).toBeInTheDocument()
    expect(screen.getByText('Thinking…')).toBeInTheDocument()

    expect(await screen.findByText('Finalize your score', {}, { timeout: 2000 })).toBeInTheDocument()
  })

  it('saving a correction updates the badge, shows the audit line, and increments the corrected count in the Finish bar', async () => {
    const user = userEvent.setup()
    renderGradedView()

    await user.click(screen.getAllByRole('button', { name: /disagree with this score/i })[0])
    await user.type(screen.getByPlaceholderText(/what feels off about this score/i), 'Too generous.')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await screen.findByText('Finalize your score', {}, { timeout: 2000 })

    await user.click(screen.getByRole('button', { name: '2' }))
    await user.click(screen.getByRole('button', { name: 'Save correction' }))

    expect(screen.getByText('Originally 3/4 by Claude — corrected to 2/4 by you')).toBeInTheDocument()
    expect(screen.getByText('1 criterion corrected · 1 accepted as graded.')).toBeInTheDocument()
  })

  it('hard-blocks Finish grading while a dispute is open and unresolved', async () => {
    const user = userEvent.setup()
    const onFinish = vi.fn()
    renderGradedView(onFinish)

    await user.click(screen.getAllByRole('button', { name: /disagree with this score/i })[0])

    expect(screen.getByRole('button', { name: /finish grading/i })).toBeDisabled()
  })

  it('calls onFinish when nothing is blocking, then shows the confirmation state with Next essay wired to onNextEssay', async () => {
    const user = userEvent.setup()
    const onFinish = vi.fn()
    const onNextEssay = vi.fn()
    renderGradedView(onFinish, onNextEssay)

    await user.click(screen.getByRole('button', { name: /finish grading/i }))
    expect(onFinish).toHaveBeenCalledOnce()

    await user.click(screen.getByRole('button', { name: /next essay/i }))
    expect(onNextEssay).toHaveBeenCalledOnce()
  })
})
