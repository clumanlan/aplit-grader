import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { FinishGradingBar } from './FinishGradingBar'

describe('FinishGradingBar', () => {
  it('shows the corrected/accepted summary and calls onFinish when nothing is blocking', async () => {
    const user = userEvent.setup()
    const onFinish = vi.fn()

    render(
      <FinishGradingBar
        totalCriteria={14}
        correctedCount={2}
        openUnresolvedCount={0}
        unaddressedMissingCount={0}
        isFinished={false}
        studentName="Jordan"
        onFinish={onFinish}
        onNextEssay={vi.fn()}
      />,
    )

    expect(screen.getByText('2 criteria corrected · 12 accepted as graded.')).toBeInTheDocument()
    const finishButton = screen.getByRole('button', { name: /finish grading/i })
    expect(finishButton).toBeEnabled()

    await user.click(finishButton)
    expect(onFinish).toHaveBeenCalledOnce()
  })

  it('shows the no-corrections copy when nothing was corrected', () => {
    render(
      <FinishGradingBar
        totalCriteria={14}
        correctedCount={0}
        openUnresolvedCount={0}
        unaddressedMissingCount={0}
        isFinished={false}
        studentName="Jordan"
        onFinish={vi.fn()}
        onNextEssay={vi.fn()}
      />,
    )

    expect(
      screen.getByText('All 14 criteria accepted as graded — no corrections made.'),
    ).toBeInTheDocument()
  })

  it('hard-blocks Finish grading and reports the open-discussion count when disputes are unresolved', () => {
    render(
      <FinishGradingBar
        totalCriteria={14}
        correctedCount={0}
        openUnresolvedCount={2}
        unaddressedMissingCount={0}
        isFinished={false}
        studentName="Jordan"
        onFinish={vi.fn()}
        onNextEssay={vi.fn()}
      />,
    )

    expect(screen.getByText(/you have 2 open discussions to resolve first\./i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /finish grading/i })).toBeDisabled()
  })

  it('shows a soft missing-criteria warning without blocking Finish', () => {
    render(
      <FinishGradingBar
        totalCriteria={14}
        correctedCount={0}
        openUnresolvedCount={0}
        unaddressedMissingCount={1}
        isFinished={false}
        studentName="Jordan"
        onFinish={vi.fn()}
        onNextEssay={vi.fn()}
      />,
    )

    expect(
      screen.getByText(/1 criterion still flagged as missing — you can finish anyway, or discuss it first\./i),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /finish grading/i })).toBeEnabled()
  })

  it('shows the confirmation state with a Next essay action once finished', async () => {
    const user = userEvent.setup()
    const onNextEssay = vi.fn()

    render(
      <FinishGradingBar
        totalCriteria={14}
        correctedCount={2}
        openUnresolvedCount={0}
        unaddressedMissingCount={0}
        isFinished
        studentName="Jordan"
        finishedAt="4:12 PM"
        onFinish={vi.fn()}
        onNextEssay={onNextEssay}
      />,
    )

    expect(screen.getByText('Grades saved for Jordan — 4:12 PM.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /next essay/i }))
    expect(onNextEssay).toHaveBeenCalledOnce()
  })
})
