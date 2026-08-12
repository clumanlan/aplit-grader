import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SetupScreen } from './SetupScreen'

const CRITERIA = {
  standalone: [
    { id: 'thesis', label: 'Thesis' },
    { id: 'conclusion', label: 'Conclusion' },
  ],
  groups: [
    {
      group: 'Body ¶1',
      items: [{ id: 'bp1-claim', label: 'Claim' }],
    },
  ],
}
const CLASSES = ['Period 3 — AP Lit', 'Period 5 — AP Lit']

describe('SetupScreen', () => {
  it('disables Start grading until a prompt and class are provided, then submits full-essay values', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<SetupScreen criteria={CRITERIA} classes={CLASSES} onSubmit={onSubmit} />)

    const submitButton = screen.getByRole('button', { name: /start grading/i })
    expect(submitButton).toBeDisabled()

    await user.type(
      screen.getByPlaceholderText(/analyze how fitzgerald/i),
      'Analyze a symbol.',
    )
    expect(submitButton).toBeDisabled()

    await user.selectOptions(screen.getByLabelText(/class/i), CLASSES[0])
    expect(submitButton).toBeEnabled()

    await user.click(submitButton)

    expect(onSubmit).toHaveBeenCalledWith({
      fullEssay: true,
      selectedCriteria: [],
      prompt: 'Analyze a symbol.',
      classId: CLASSES[0],
    })
  })

  it('switches off full-essay and submits only the picked criteria when one is selected', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<SetupScreen criteria={CRITERIA} classes={CLASSES} onSubmit={onSubmit} />)

    const fullEssayButton = screen.getByRole('button', { name: 'Full essay' })
    expect(fullEssayButton).toHaveAttribute('aria-pressed', 'true')

    await user.click(screen.getByRole('button', { name: 'Claim' }))
    expect(fullEssayButton).toHaveAttribute('aria-pressed', 'false')

    await user.type(
      screen.getByPlaceholderText(/analyze how fitzgerald/i),
      'Analyze a symbol.',
    )
    await user.selectOptions(screen.getByLabelText(/class/i), CLASSES[0])
    await user.click(screen.getByRole('button', { name: /start grading/i }))

    expect(onSubmit).toHaveBeenCalledWith({
      fullEssay: false,
      selectedCriteria: ['bp1-claim'],
      prompt: 'Analyze a symbol.',
      classId: CLASSES[0],
    })
  })

  it('keeps Start grading disabled when the prompt is only whitespace', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<SetupScreen criteria={CRITERIA} classes={CLASSES} onSubmit={onSubmit} />)

    await user.type(screen.getByPlaceholderText(/analyze how fitzgerald/i), '   ')
    await user.selectOptions(screen.getByLabelText(/class/i), CLASSES[0])

    expect(screen.getByRole('button', { name: /start grading/i })).toBeDisabled()
  })

  it('shows the New assignment eyebrow, heading, and explanatory subtext', () => {
    render(<SetupScreen criteria={CRITERIA} classes={CLASSES} onSubmit={vi.fn()} />)

    expect(screen.getByText('New assignment')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Set this up once' })).toBeInTheDocument()
    expect(
      screen.getByText(
        "This stays the same for every essay in this batch. You can change it anytime from the grading screen.",
      ),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument()
  })

  it('pre-fills from initialValues and shows Edit assignment / Save changes copy with a working Cancel', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    const onCancel = vi.fn()

    render(
      <SetupScreen
        criteria={CRITERIA}
        classes={CLASSES}
        initialValues={{
          fullEssay: false,
          selectedCriteria: ['bp1-claim'],
          prompt: 'Analyze a symbol.',
          classId: CLASSES[1],
        }}
        onSubmit={onSubmit}
        onCancel={onCancel}
      />,
    )

    expect(screen.getByText('Edit assignment')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Full essay' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: 'Claim' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByPlaceholderText(/analyze how fitzgerald/i)).toHaveValue('Analyze a symbol.')
    expect(screen.getByLabelText(/class/i)).toHaveValue(CLASSES[1])

    const submitButton = screen.getByRole('button', { name: 'Save changes' })
    expect(submitButton).toBeEnabled()

    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onCancel).toHaveBeenCalledOnce()

    await user.click(submitButton)
    expect(onSubmit).toHaveBeenCalledWith({
      fullEssay: false,
      selectedCriteria: ['bp1-claim'],
      prompt: 'Analyze a symbol.',
      classId: CLASSES[1],
    })
  })
})
