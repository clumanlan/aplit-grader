import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { CriterionCard } from './CriterionCard'

describe('CriterionCard', () => {
  it('renders a scored criterion with its tier badge, bullets, and a collapsed reasoning disclosure', async () => {
    const user = userEvent.setup()

    render(
      <CriterionCard
        label="Claim"
        group="Body ¶1"
        score={3}
        missing={false}
        strengths={['Sharp and arguable.']}
        critiques={['Push past the summary.']}
        reasoning="Held at 3 rather than 4 because..."
      />,
    )

    expect(screen.getByText('Body ¶1 · Claim')).toBeInTheDocument()
    expect(screen.getByText('3 / 4 · Solid')).toBeInTheDocument()
    expect(screen.getByText('Sharp and arguable.')).toBeInTheDocument()
    expect(screen.getByText('What would strengthen it')).toBeInTheDocument()
    expect(screen.getByText('Push past the summary.')).toBeInTheDocument()
    expect(screen.queryByText(/originally.*by claude/i)).not.toBeInTheDocument()

    expect(screen.queryByText('Held at 3 rather than 4 because...')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /show model's reasoning/i }))
    expect(screen.getByText('Held at 3 rather than 4 because...')).toBeInTheDocument()
  })

  it('renders a missing criterion with the alert badge and missing-state copy', () => {
    render(
      <CriterionCard
        label="Reasoning 1"
        group="Body ¶1"
        score={null}
        missing
        strengths={[]}
        critiques={['Add a sentence connecting the evidence to the claim.']}
        reasoning="No such sentence follows the first piece of evidence."
      />,
    )

    expect(screen.getByText('! Missing')).toBeInTheDocument()
    expect(
      screen.getByText('Nothing to point to yet — no reasoning sentence is present.'),
    ).toBeInTheDocument()
    expect(screen.getByText("What's missing")).toBeInTheDocument()
  })

  it('shows the audit line and drops the missing badge once a missing criterion is overridden', () => {
    render(
      <CriterionCard
        label="Reasoning 1"
        group="Body ¶1"
        score={null}
        missing
        strengths={[]}
        critiques={['Add a sentence connecting the evidence to the claim.']}
        reasoning="No such sentence follows the first piece of evidence."
        overriddenScore={1}
      />,
    )

    expect(screen.getByText('1 / 4 · Developing')).toBeInTheDocument()
    expect(screen.queryByText('! Missing')).not.toBeInTheDocument()
    expect(screen.getByText('Flagged as missing by Claude — scored 1/4 by you')).toBeInTheDocument()
  })

  it('shows the corrected-score audit line for a normal (non-missing) override', () => {
    render(
      <CriterionCard
        label="Thesis"
        group={null}
        score={3}
        missing={false}
        strengths={['Clear claim.']}
        critiques={[]}
        reasoning="..."
        overriddenScore={4}
      />,
    )

    expect(screen.getByText('4 / 4 · Strong')).toBeInTheDocument()
    expect(screen.getByText('Originally 3/4 by Claude — corrected to 4/4 by you')).toBeInTheDocument()
  })

  it('calls onDisagree when the disagree button is clicked', async () => {
    const user = userEvent.setup()
    const onDisagree = vi.fn()

    render(
      <CriterionCard
        label="Thesis"
        group={null}
        score={3}
        missing={false}
        strengths={[]}
        critiques={[]}
        reasoning="..."
        onDisagree={onDisagree}
      />,
    )

    await user.click(screen.getByRole('button', { name: /disagree with this score/i }))
    expect(onDisagree).toHaveBeenCalledOnce()
  })
})
