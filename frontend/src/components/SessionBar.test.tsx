import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SessionBar } from './SessionBar'

describe('SessionBar', () => {
  it('shows setup time, singular essay count, and the sections/class chips', () => {
    render(
      <SessionBar
        session={{
          sections: 'Full essay',
          classId: 'Period 3 — AP Lit',
          prompt: 'Analyze a symbol.',
          setupAt: '2:14 PM',
          count: 1,
        }}
        onAdjustAssignment={vi.fn()}
        onNewAssignment={vi.fn()}
      />,
    )

    expect(screen.getByText('Set up 2:14 PM · 1 essay graded')).toBeInTheDocument()
    expect(screen.getByText('Full essay')).toBeInTheDocument()
    expect(screen.getByText('Period 3 — AP Lit')).toBeInTheDocument()
    expect(screen.getByText('Analyze a symbol.')).toBeInTheDocument()
  })

  it('pluralizes the essay count when more than one essay has been graded', () => {
    render(
      <SessionBar
        session={{
          sections: 'Full essay',
          classId: 'Period 3 — AP Lit',
          prompt: 'Analyze a symbol.',
          setupAt: '2:14 PM',
          count: 3,
        }}
        onAdjustAssignment={vi.fn()}
        onNewAssignment={vi.fn()}
      />,
    )

    expect(screen.getByText('Set up 2:14 PM · 3 essays graded')).toBeInTheDocument()
  })

  it('calls onAdjustAssignment and onNewAssignment when their buttons are clicked', async () => {
    const user = userEvent.setup()
    const onAdjustAssignment = vi.fn()
    const onNewAssignment = vi.fn()

    render(
      <SessionBar
        session={{
          sections: 'Full essay',
          classId: 'Period 3 — AP Lit',
          prompt: 'Analyze a symbol.',
          setupAt: '2:14 PM',
          count: 0,
        }}
        onAdjustAssignment={onAdjustAssignment}
        onNewAssignment={onNewAssignment}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Adjust assignment' }))
    expect(onAdjustAssignment).toHaveBeenCalledOnce()

    await user.click(screen.getByRole('button', { name: 'New assignment' }))
    expect(onNewAssignment).toHaveBeenCalledOnce()
  })

  it('truncates a long prompt to 40 characters with an ellipsis', () => {
    const longPrompt =
      'Analyze how Fitzgerald uses a symbol to develop a theme in The Great Gatsby.'

    render(
      <SessionBar
        session={{
          sections: 'Full essay',
          classId: 'Period 3 — AP Lit',
          prompt: longPrompt,
          setupAt: '2:14 PM',
          count: 0,
        }}
        onAdjustAssignment={vi.fn()}
        onNewAssignment={vi.fn()}
      />,
    )

    expect(screen.getByText(`${longPrompt.slice(0, 40)}…`)).toBeInTheDocument()
    expect(screen.queryByText(longPrompt)).not.toBeInTheDocument()
  })
})
