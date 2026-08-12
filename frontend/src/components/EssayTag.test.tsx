import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { EssayTag } from './EssayTag'

describe('EssayTag', () => {
  it('renders the criterion label and calls onClick when a scored tag is clicked', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()

    render(<EssayTag label="Evidence 1" missing={false} score={3} isActive={false} onClick={onClick} />)

    const tag = screen.getByRole('button', { name: 'Evidence 1' })
    await user.click(tag)
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('renders a dashed missing-placeholder chip and still calls onClick', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()

    render(<EssayTag label="Reasoning 1" missing score={null} isActive={false} onClick={onClick} />)

    const tag = screen.getByRole('button', { name: '! Reasoning 1 missing' })
    await user.click(tag)
    expect(onClick).toHaveBeenCalledOnce()
  })
})
