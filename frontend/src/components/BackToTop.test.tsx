import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BackToTop } from './BackToTop'

describe('BackToTop', () => {
  beforeEach(() => {
    window.scrollTo = vi.fn()
    Object.defineProperty(window, 'scrollY', { value: 0, writable: true, configurable: true })
  })

  it('stays hidden until scrolled past 400px, then appears and scrolls to top on click', () => {
    render(<BackToTop />)

    expect(screen.queryByRole('button', { name: /back to top/i })).not.toBeInTheDocument()

    Object.defineProperty(window, 'scrollY', { value: 500, writable: true, configurable: true })
    fireEvent.scroll(window)

    const button = screen.getByRole('button', { name: /back to top/i })
    fireEvent.click(button)
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' })
  })

  it('hides again once scrolled back above the threshold', () => {
    render(<BackToTop />)

    Object.defineProperty(window, 'scrollY', { value: 500, writable: true, configurable: true })
    fireEvent.scroll(window)
    expect(screen.getByRole('button', { name: /back to top/i })).toBeInTheDocument()

    Object.defineProperty(window, 'scrollY', { value: 100, writable: true, configurable: true })
    fireEvent.scroll(window)
    expect(screen.queryByRole('button', { name: /back to top/i })).not.toBeInTheDocument()
  })
})
