import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import App from './App'
import { clearAuth, setAuthenticated } from './auth/authStore'

describe('App auth gating', () => {
  afterEach(() => {
    clearAuth()
  })

  it('shows the login screen and no sign-out button when signed out', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /sign out/i })).not.toBeInTheDocument()
  })

  it('shows the setup screen and a sign-out button once authenticated', () => {
    setAuthenticated('fake-access-token', 'teacher@example.com')
    render(<App />)

    expect(screen.getByRole('heading', { name: /set this up once/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument()
  })

  it('returns to the login screen and clears the token after clicking sign out', async () => {
    const user = userEvent.setup()
    setAuthenticated('fake-access-token', 'teacher@example.com')
    render(<App />)

    await user.click(screen.getByRole('button', { name: /sign out/i }))

    expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument()
  })
})
