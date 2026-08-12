import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { LoadingScreen } from './LoadingScreen'

describe('LoadingScreen', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('starts at 0s elapsed with the first status message and no reassurance line', () => {
    render(<LoadingScreen />)

    expect(screen.getByText('0s elapsed')).toBeInTheDocument()
    expect(screen.getByText('Reading the thesis…')).toBeInTheDocument()
    expect(screen.queryByText(/first grade of a session/i)).not.toBeInTheDocument()
  })

  it('advances the elapsed counter once per second', () => {
    render(<LoadingScreen />)

    act(() => {
      vi.advanceTimersByTime(3000)
    })

    expect(screen.getByText('3s elapsed')).toBeInTheDocument()
  })

  it('rotates to the next status message every 3.2s, following grading order', () => {
    render(<LoadingScreen />)

    act(() => {
      vi.advanceTimersByTime(3200)
    })
    expect(screen.getByText("Checking the first body paragraph's evidence…")).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(3200)
    })
    expect(screen.getByText('Weighing the reasoning…')).toBeInTheDocument()
  })

  it('shows the reassurance line only once 20s have elapsed', () => {
    render(<LoadingScreen />)

    act(() => {
      vi.advanceTimersByTime(19000)
    })
    expect(screen.queryByText(/first grade of a session can take up to a minute/i)).not.toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.getByText(/first grade of a session can take up to a minute/i)).toBeInTheDocument()
  })
})
