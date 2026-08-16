import { beforeEach, describe, expect, it, vi } from 'vitest'
import { clearAuth, getAccessToken, getAuthState, setAuthenticated, subscribeAuth } from './authStore'

describe('authStore', () => {
  beforeEach(() => {
    clearAuth()
  })

  it('starts with no access token', () => {
    expect(getAccessToken()).toBeNull()
    expect(getAuthState()).toEqual({ accessToken: null, username: null })
  })

  it('stores the token and username after setAuthenticated', () => {
    setAuthenticated('fake-token', 'teacher@example.com')

    expect(getAccessToken()).toBe('fake-token')
    expect(getAuthState()).toEqual({ accessToken: 'fake-token', username: 'teacher@example.com' })
  })

  it('clears the token on clearAuth', () => {
    setAuthenticated('fake-token', 'teacher@example.com')
    clearAuth()

    expect(getAccessToken()).toBeNull()
  })

  it('notifies subscribers on change and lets them unsubscribe', () => {
    const listener = vi.fn()
    const unsubscribe = subscribeAuth(listener)

    setAuthenticated('fake-token', 'teacher@example.com')
    expect(listener).toHaveBeenCalledTimes(1)

    unsubscribe()
    setAuthenticated('another-token', 'teacher@example.com')
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('does not notify subscribers when clearAuth runs with no active session', () => {
    const listener = vi.fn()
    subscribeAuth(listener)

    clearAuth()

    expect(listener).not.toHaveBeenCalled()
  })
})
