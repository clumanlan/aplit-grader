import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { RubricKey } from './RubricKey'

const ITEMS = [
  { id: 'thesis', label: 'Thesis', group: null, score: 3, missing: false },
  { id: 'bp1-claim', label: 'Claim', group: 'Body ¶1', score: 4, missing: false },
  { id: 'bp1-reasoning-1', label: 'Reasoning 1', group: 'Body ¶1', score: null, missing: true },
  { id: 'bp2-claim', label: 'Claim', group: 'Body ¶2', score: 4, missing: false },
  { id: 'conclusion', label: 'Conclusion', group: null, score: 3, missing: false },
]

describe('RubricKey', () => {
  it('groups criteria under Body ¶1 / Body ¶2 labels, leaving Thesis and Conclusion standalone', () => {
    render(<RubricKey items={ITEMS} activeId="thesis" onSelect={vi.fn()} />)

    expect(screen.getByText('Body ¶1')).toBeInTheDocument()
    expect(screen.getByText('Body ¶2')).toBeInTheDocument()

    const thesisChip = screen.getByRole('button', { name: /Thesis/ })
    expect(thesisChip).toBeInTheDocument()
  })

  it("shows each criterion's score, or a missing badge when flagged missing", () => {
    render(<RubricKey items={ITEMS} activeId="thesis" onSelect={vi.fn()} />)

    const thesisChip = screen.getByRole('button', { name: /^Thesis 3$/ })
    expect(within(thesisChip).getByText('3')).toBeInTheDocument()

    const missingChip = screen.getByRole('button', { name: /Reasoning 1/ })
    expect(within(missingChip).getByText('!')).toBeInTheDocument()
  })

  it('marks the active criterion and calls onSelect with the clicked id', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(<RubricKey items={ITEMS} activeId="thesis" onSelect={onSelect} />)

    expect(screen.getByRole('button', { name: /^Thesis 3$/ })).toHaveAttribute('aria-current', 'true')
    expect(screen.getByRole('button', { name: /^Conclusion 3$/ })).toHaveAttribute('aria-current', 'false')

    await user.click(screen.getByRole('button', { name: /^Conclusion 3$/ }))
    expect(onSelect).toHaveBeenCalledWith('conclusion')
  })
})
