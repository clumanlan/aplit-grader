import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { GradedView } from './GradedView'
import type { GradedEssay } from '../types/essayLinking'
import { disputeTurn, resolveDispute } from '../api/dispute'

vi.mock('../api/dispute', () => ({
  disputeTurn: vi.fn(),
  resolveDispute: vi.fn(),
  DisputeRequestError: class DisputeRequestError extends Error {},
}))

const mockedDisputeTurn = vi.mocked(disputeTurn)
const mockedResolveDispute = vi.mocked(resolveDispute)

const GRADED_ESSAY: GradedEssay = {
  essayId: 'essay-123',
  sentences: [{ index: 0, text: 'This is the thesis sentence.' }],
  sectionOf: { 0: 'thesis' },
  citingCriteria: { 0: ['thesis'] },
  criteria: [
    {
      id: 'thesis',
      label: 'Thesis',
      group: null,
      score: 3,
      missing: false,
      strengths: ['Clear claim.'],
      critiques: ['Push further.'],
      reasoning: 'Held at 3 because...',
      sentence_refs: [0],
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
      sentence_refs: [],
    },
  ],
}

function renderGradedView(onFinish = vi.fn(), onNextEssay = vi.fn()) {
  return render(
    <GradedView
      studentName="Jordan"
      classId="Period 3 — AP Lit"
      assignmentPrompt="Analyze the symbolism"
      essayText="This is the thesis sentence."
      gradedEssay={GRADED_ESSAY}
      onFinish={onFinish}
      onNextEssay={onNextEssay}
    />,
  )
}

describe('GradedView', () => {
  it('opens a dispute, sends a message, and shows Claude\'s reply with a proposed score', async () => {
    mockedDisputeTurn.mockResolvedValue({
      message: "You're right to push on this — I'd put this at 2/4 instead.",
      proposal: { ...GRADED_ESSAY.criteria[0], score: 2 },
      proposalRawGradeId: 'raw-grade-1',
    })
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

    expect(await screen.findByText('Finalize your score', {}, { timeout: 2000 })).toBeInTheDocument()
    expect(mockedDisputeTurn).toHaveBeenCalledWith(
      expect.objectContaining({
        essayText: 'This is the thesis sentence.',
        assignmentPrompt: 'Analyze the symbolism',
        original: expect.objectContaining({ id: 'thesis' }),
        messages: [{ role: 'teacher', text: 'This feels low for the evidence given.' }],
      }),
    )
  })

  it('saving a correction updates the badge, shows the audit line, and increments the corrected count in the Finish bar', async () => {
    mockedDisputeTurn.mockResolvedValue({
      message: "You're right — I'd put this at 2/4 instead.",
      proposal: { ...GRADED_ESSAY.criteria[0], score: 2 },
      proposalRawGradeId: 'raw-grade-1',
    })
    mockedResolveDispute.mockResolvedValue({ acceptedGradeId: 'accepted-1', score: 2, missing: false })
    const user = userEvent.setup()
    renderGradedView()

    await user.click(screen.getAllByRole('button', { name: /disagree with this score/i })[0])
    await user.type(screen.getByPlaceholderText(/what feels off about this score/i), 'Too generous.')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await screen.findByText('Finalize your score', {}, { timeout: 2000 })

    await user.click(screen.getByRole('button', { name: '2' }))
    await user.click(screen.getByRole('button', { name: 'Save correction' }))

    expect(
      await screen.findByText('Originally 3/4 by Claude — corrected to 2/4 by you'),
    ).toBeInTheDocument()
    expect(screen.getByText('1 criterion corrected · 1 accepted as graded.')).toBeInTheDocument()
    expect(mockedResolveDispute).toHaveBeenCalledWith({
      essayId: 'essay-123',
      criterionId: 'thesis',
      resolution: 'corrected',
      rawGradeId: 'raw-grade-1',
    })
  })

  it('keeping the original calls resolveDispute with kept_original and no rawGradeId', async () => {
    mockedDisputeTurn.mockResolvedValue({
      message: "Fair enough, but I'd still put this at 2/4.",
      proposal: { ...GRADED_ESSAY.criteria[0], score: 2 },
      proposalRawGradeId: 'raw-grade-1',
    })
    mockedResolveDispute.mockResolvedValue({ acceptedGradeId: 'accepted-2', score: 3, missing: false })
    const user = userEvent.setup()
    renderGradedView()

    await user.click(screen.getAllByRole('button', { name: /disagree with this score/i })[0])
    await user.type(screen.getByPlaceholderText(/what feels off about this score/i), 'Never mind.')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await screen.findByText('Finalize your score', {}, { timeout: 2000 })

    await user.click(screen.getByRole('button', { name: 'Keep original' }))

    expect(mockedResolveDispute).toHaveBeenCalledWith({
      essayId: 'essay-123',
      criterionId: 'thesis',
      resolution: 'kept_original',
      rawGradeId: undefined,
    })
    expect(await screen.findByText('Resolved — original score kept.')).toBeInTheDocument()
  })

  it('shows a fallback message and keeps the thread open when the dispute request fails', async () => {
    mockedDisputeTurn.mockRejectedValue(new Error('network down'))
    const user = userEvent.setup()
    renderGradedView()

    await user.click(screen.getAllByRole('button', { name: /disagree with this score/i })[0])
    await user.type(screen.getByPlaceholderText(/what feels off about this score/i), 'Too generous.')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(
      await screen.findByText('Something went wrong reaching the grading service. Try again.'),
    ).toBeInTheDocument()
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
