import { useState } from 'react'
import { CognitoAuthError, completeNewPassword, signIn } from '../auth/cognito'

export interface LoginScreenProps {
  onSignedIn: (accessToken: string, username: string) => void
}

type Stage =
  | { name: 'credentials' }
  | { name: 'new_password_required'; session: string; username: string }

export function LoginScreen({ onSignedIn }: LoginScreenProps) {
  const [stage, setStage] = useState<Stage>({ name: 'credentials' })
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const canSubmitCredentials = username.trim() !== '' && password !== '' && !isSubmitting
  const canSubmitNewPassword =
    newPassword !== '' && newPassword === confirmNewPassword && !isSubmitting

  const handleSignIn = async () => {
    if (!canSubmitCredentials) return
    setError(null)
    setIsSubmitting(true)
    try {
      const result = await signIn(username.trim(), password)
      if (result.status === 'new_password_required') {
        setStage({ name: 'new_password_required', session: result.session, username: result.username })
      } else {
        onSignedIn(result.accessToken, result.username)
      }
    } catch (err) {
      setError(err instanceof CognitoAuthError ? err.message : 'Sign-in failed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSetNewPassword = async () => {
    if (stage.name !== 'new_password_required' || !canSubmitNewPassword) return
    setError(null)
    setIsSubmitting(true)
    try {
      const result = await completeNewPassword(stage.username, newPassword, stage.session)
      onSignedIn(result.accessToken, result.username)
    } catch (err) {
      setError(err instanceof CognitoAuthError ? err.message : 'Could not set the new password.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (stage.name === 'new_password_required') {
    return (
      <div className="rounded bg-paper px-8 py-8 text-ink shadow-sm">
        <p className="mb-1 text-xs uppercase tracking-[0.15em] text-muted">First sign-in</p>
        <h1 className="mb-1 font-serif text-2xl font-semibold">Set a permanent password</h1>
        <p className="mb-8 text-sm text-muted">Signed in as {stage.username}.</p>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            void handleSetNewPassword()
          }}
        >
          <label htmlFor="new-password" className="mb-2 block text-xs font-semibold uppercase tracking-wide">
            New password
          </label>
          <input
            id="new-password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
            className="mb-4 w-full rounded border border-field-border bg-field px-3 py-2.5 text-sm text-ink outline-none"
          />

          <label
            htmlFor="confirm-new-password"
            className="mb-2 block text-xs font-semibold uppercase tracking-wide"
          >
            Confirm new password
          </label>
          <input
            id="confirm-new-password"
            type="password"
            value={confirmNewPassword}
            onChange={(e) => setConfirmNewPassword(e.target.value)}
            autoComplete="new-password"
            className="mb-2 w-full rounded border border-field-border bg-field px-3 py-2.5 text-sm text-ink outline-none"
          />

          {error && <p className="mb-4 text-sm text-tier-missing">{error}</p>}

          <div className="mt-6 flex justify-end">
            <button
              type="submit"
              disabled={!canSubmitNewPassword}
              className="rounded bg-card px-5 py-2.5 text-sm font-semibold uppercase tracking-wide text-cream disabled:cursor-not-allowed disabled:opacity-35"
            >
              {isSubmitting ? 'Setting password…' : 'Set password and sign in'}
            </button>
          </div>
        </form>
      </div>
    )
  }

  return (
    <div className="rounded bg-paper px-8 py-8 text-ink shadow-sm">
      <p className="mb-1 text-xs uppercase tracking-[0.15em] text-muted">AP Lit Essay Grader</p>
      <h1 className="mb-8 font-serif text-2xl font-semibold">Sign in</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          void handleSignIn()
        }}
      >
        <label htmlFor="username" className="mb-2 block text-xs font-semibold uppercase tracking-wide">
          Email
        </label>
        <input
          id="username"
          type="email"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          className="mb-4 w-full rounded border border-field-border bg-field px-3 py-2.5 text-sm text-ink outline-none"
        />

        <label htmlFor="password" className="mb-2 block text-xs font-semibold uppercase tracking-wide">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          className="mb-2 w-full rounded border border-field-border bg-field px-3 py-2.5 text-sm text-ink outline-none"
        />

        {error && <p className="mb-4 text-sm text-tier-missing">{error}</p>}

        <div className="mt-6 flex justify-end">
          <button
            type="submit"
            disabled={!canSubmitCredentials}
            className="rounded bg-card px-5 py-2.5 text-sm font-semibold uppercase tracking-wide text-cream disabled:cursor-not-allowed disabled:opacity-35"
          >
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </button>
        </div>
      </form>
    </div>
  )
}
