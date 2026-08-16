import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import * as cognito from '../auth/cognito'
import { LoginScreen } from './LoginScreen'

vi.mock('../auth/cognito', async () => {
  const actual = await vi.importActual<typeof import('../auth/cognito')>('../auth/cognito')
  return {
    ...actual,
    signIn: vi.fn(),
    completeNewPassword: vi.fn(),
  }
})

describe('LoginScreen', () => {
  it('disables Sign in until both email and password are filled', async () => {
    const user = userEvent.setup()
    render(<LoginScreen onSignedIn={vi.fn()} />)

    const submitButton = screen.getByRole('button', { name: /sign in/i })
    expect(submitButton).toBeDisabled()

    await user.type(screen.getByLabelText(/email/i), 'teacher@example.com')
    expect(submitButton).toBeDisabled()

    await user.type(screen.getByLabelText(/^password$/i), 'hunter2')
    expect(submitButton).toBeEnabled()
  })

  it('calls onSignedIn with the access token on a successful sign-in', async () => {
    const user = userEvent.setup()
    const onSignedIn = vi.fn()
    vi.mocked(cognito.signIn).mockResolvedValue({
      status: 'signed_in',
      accessToken: 'fake-access-token',
      username: 'teacher@example.com',
    })

    render(<LoginScreen onSignedIn={onSignedIn} />)
    await user.type(screen.getByLabelText(/email/i), 'teacher@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'hunter2')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(cognito.signIn).toHaveBeenCalledWith('teacher@example.com', 'hunter2')
    expect(onSignedIn).toHaveBeenCalledWith('fake-access-token', 'teacher@example.com')
  })

  it('shows the sign-in error message on failure and does not call onSignedIn', async () => {
    const user = userEvent.setup()
    const onSignedIn = vi.fn()
    vi.mocked(cognito.signIn).mockRejectedValue(
      new cognito.CognitoAuthError('Incorrect username or password.'),
    )

    render(<LoginScreen onSignedIn={onSignedIn} />)
    await user.type(screen.getByLabelText(/email/i), 'teacher@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'wrong')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText(/incorrect username or password/i)).toBeInTheDocument()
    expect(onSignedIn).not.toHaveBeenCalled()
  })

  it('walks through the NEW_PASSWORD_REQUIRED challenge and then calls onSignedIn', async () => {
    const user = userEvent.setup()
    const onSignedIn = vi.fn()
    vi.mocked(cognito.signIn).mockResolvedValue({
      status: 'new_password_required',
      session: 'fake-session',
      username: 'teacher@example.com',
    })
    vi.mocked(cognito.completeNewPassword).mockResolvedValue({
      status: 'signed_in',
      accessToken: 'fake-access-token',
      username: 'teacher@example.com',
    })

    render(<LoginScreen onSignedIn={onSignedIn} />)
    await user.type(screen.getByLabelText(/email/i), 'teacher@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'temporary-password')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText(/set a permanent password/i)).toBeInTheDocument()

    const newPasswordSubmit = screen.getByRole('button', { name: /set password and sign in/i })
    expect(newPasswordSubmit).toBeDisabled()

    await user.type(screen.getByLabelText(/^new password$/i), 'new-secure-password')
    await user.type(screen.getByLabelText(/confirm new password/i), 'new-secure-password')
    expect(newPasswordSubmit).toBeEnabled()

    await user.click(newPasswordSubmit)

    expect(cognito.completeNewPassword).toHaveBeenCalledWith(
      'teacher@example.com',
      'new-secure-password',
      'fake-session',
    )
    expect(onSignedIn).toHaveBeenCalledWith('fake-access-token', 'teacher@example.com')
  })

  it('keeps the new-password submit disabled when the two entries do not match', async () => {
    const user = userEvent.setup()
    vi.mocked(cognito.signIn).mockResolvedValue({
      status: 'new_password_required',
      session: 'fake-session',
      username: 'teacher@example.com',
    })

    render(<LoginScreen onSignedIn={vi.fn()} />)
    await user.type(screen.getByLabelText(/email/i), 'teacher@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'temporary-password')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await screen.findByText(/set a permanent password/i)
    await user.type(screen.getByLabelText(/^new password$/i), 'new-secure-password')
    await user.type(screen.getByLabelText(/confirm new password/i), 'does-not-match')

    expect(screen.getByRole('button', { name: /set password and sign in/i })).toBeDisabled()
  })
})
