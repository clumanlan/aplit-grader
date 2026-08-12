import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { PasteScreen } from './PasteScreen'

describe('PasteScreen', () => {
  it('disables Grade this essay until both student name and essay text are filled', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<PasteScreen onSubmit={onSubmit} />)

    const submitButton = screen.getByRole('button', { name: /grade this essay/i })
    expect(submitButton).toBeDisabled()

    await user.type(screen.getByPlaceholderText(/student name/i), 'Jordan')
    expect(submitButton).toBeDisabled()

    await user.type(screen.getByPlaceholderText(/paste the essay text here/i), 'Once upon a time.')
    expect(submitButton).toBeEnabled()

    await user.click(submitButton)

    expect(onSubmit).toHaveBeenCalledWith({
      studentName: 'Jordan',
      essayText: 'Once upon a time.',
    })
  })

  it('keeps Grade this essay disabled when either field is only whitespace', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<PasteScreen onSubmit={onSubmit} />)

    await user.type(screen.getByPlaceholderText(/student name/i), '   ')
    await user.type(screen.getByPlaceholderText(/paste the essay text here/i), 'Once upon a time.')

    expect(screen.getByRole('button', { name: /grade this essay/i })).toBeDisabled()
  })
})
