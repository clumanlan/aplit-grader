import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { DisputeThread } from './DisputeThread'

describe('DisputeThread', () => {
  it('renders the conversation so far and a thinking indicator while a reply is pending', () => {
    render(
      <DisputeThread
        messages={[
          { role: 'teacher', text: 'This feels low for the evidence given.' },
          { role: 'claude', text: "You're right to push on this..." },
        ]}
        proposedScore={null}
        isSending
        isResolved={false}
        onSend={vi.fn()}
        onSaveCorrection={vi.fn()}
        onKeepOriginal={vi.fn()}
      />,
    )

    expect(screen.getByText('This feels low for the evidence given.')).toBeInTheDocument()
    expect(screen.getByText("You're right to push on this...")).toBeInTheDocument()
    expect(screen.getByText('Thinking…')).toBeInTheDocument()
  })

  it('sends the trimmed draft and clears the input, disabled while empty or whitespace-only', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    render(
      <DisputeThread
        messages={[]}
        proposedScore={null}
        isSending={false}
        isResolved={false}
        onSend={onSend}
        onSaveCorrection={vi.fn()}
        onKeepOriginal={vi.fn()}
      />,
    )

    const input = screen.getByPlaceholderText(/what feels off about this score/i)
    const sendButton = screen.getByRole('button', { name: 'Send' })
    expect(sendButton).toBeDisabled()

    await user.type(input, '   ')
    expect(sendButton).toBeDisabled()

    await user.clear(input)
    await user.type(input, 'This feels low.')
    expect(sendButton).toBeEnabled()

    await user.click(sendButton)
    expect(onSend).toHaveBeenCalledWith('This feels low.')
    expect(input).toHaveValue('')
  })

  it('also sends on Enter', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    render(
      <DisputeThread
        messages={[]}
        proposedScore={null}
        isSending={false}
        isResolved={false}
        onSend={onSend}
        onSaveCorrection={vi.fn()}
        onKeepOriginal={vi.fn()}
      />,
    )

    await user.type(screen.getByPlaceholderText(/what feels off about this score/i), 'Push back{Enter}')
    expect(onSend).toHaveBeenCalledWith('Push back')
  })

  it('only shows the finalize picker once Claude has proposed a score, and requires her own click before Save correction is enabled', async () => {
    const user = userEvent.setup()
    const onSaveCorrection = vi.fn()

    const { rerender } = render(
      <DisputeThread
        messages={[]}
        proposedScore={null}
        isSending={false}
        isResolved={false}
        onSend={vi.fn()}
        onSaveCorrection={onSaveCorrection}
        onKeepOriginal={vi.fn()}
      />,
    )

    expect(screen.queryByText('Finalize your score')).not.toBeInTheDocument()

    rerender(
      <DisputeThread
        messages={[]}
        proposedScore={2}
        isSending={false}
        isResolved={false}
        onSend={vi.fn()}
        onSaveCorrection={onSaveCorrection}
        onKeepOriginal={vi.fn()}
      />,
    )

    expect(screen.getByText('Finalize your score')).toBeInTheDocument()
    const saveButton = screen.getByRole('button', { name: 'Save correction' })
    expect(saveButton).toBeDisabled()

    await user.click(screen.getByRole('button', { name: '3' }))
    expect(saveButton).toBeEnabled()

    await user.click(saveButton)
    expect(onSaveCorrection).toHaveBeenCalledWith(3)
  })

  it('calls onKeepOriginal when Keep original is clicked', async () => {
    const user = userEvent.setup()
    const onKeepOriginal = vi.fn()

    render(
      <DisputeThread
        messages={[]}
        proposedScore={2}
        isSending={false}
        isResolved={false}
        onSend={vi.fn()}
        onSaveCorrection={vi.fn()}
        onKeepOriginal={onKeepOriginal}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Keep original' }))
    expect(onKeepOriginal).toHaveBeenCalledOnce()
  })

  it('shows the resolved summary instead of the input and finalize UI once resolved', () => {
    render(
      <DisputeThread
        messages={[{ role: 'teacher', text: 'Hi' }]}
        proposedScore={2}
        isSending={false}
        isResolved
        resolvedSummary="Resolved — score corrected to 2/4."
        onSend={vi.fn()}
        onSaveCorrection={vi.fn()}
        onKeepOriginal={vi.fn()}
      />,
    )

    expect(screen.getByText('Resolved — score corrected to 2/4.')).toBeInTheDocument()
    expect(screen.queryByPlaceholderText(/what feels off about this score/i)).not.toBeInTheDocument()
    expect(screen.queryByText('Finalize your score')).not.toBeInTheDocument()
  })
})
