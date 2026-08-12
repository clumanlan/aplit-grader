import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ErrorScreen } from './ErrorScreen'

describe('ErrorScreen', () => {
  it('shows the failure copy and calls onRetry when Try again is clicked', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(<ErrorScreen onRetry={onRetry} />)

    expect(screen.getByText('Grading failed')).toBeInTheDocument()
    expect(
      screen.getByText("The grading model didn't respond in time. Nothing was lost — the essay is still here."),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /try again/i }))
    expect(onRetry).toHaveBeenCalledOnce()
  })
})
