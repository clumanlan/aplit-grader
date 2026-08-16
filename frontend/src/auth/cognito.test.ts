import { afterEach, describe, expect, it, vi } from 'vitest'
import { completeNewPassword, signIn } from './cognito'

function mockCognitoResponse(body: unknown, status = 200): void {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(body), { status }))
}

describe('cognito signIn', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('calls Cognito InitiateAuth directly with USER_PASSWORD_AUTH and the configured client id', async () => {
    mockCognitoResponse({
      AuthenticationResult: { AccessToken: 'fake-token', IdToken: 'x', ExpiresIn: 3600, TokenType: 'Bearer' },
    })

    await signIn('teacher@example.com', 'hunter2')

    const fetchSpy = vi.mocked(globalThis.fetch)
    expect(fetchSpy).toHaveBeenCalledTimes(1)
    const [url, init] = fetchSpy.mock.calls[0]
    expect(url).toBe('https://cognito-idp.us-east-2.amazonaws.com/')

    const headers = new Headers(init?.headers)
    expect(headers.get('X-Amz-Target')).toBe('AWSCognitoIdentityProviderService.InitiateAuth')

    const body = JSON.parse(init?.body as string)
    expect(body).toEqual({
      AuthFlow: 'USER_PASSWORD_AUTH',
      ClientId: '7amuvrc9l1sn727kqp6paraoqk',
      AuthParameters: { USERNAME: 'teacher@example.com', PASSWORD: 'hunter2' },
    })
  })

  it('surfaces a NEW_PASSWORD_REQUIRED challenge instead of AuthenticationResult fields', async () => {
    mockCognitoResponse({ ChallengeName: 'NEW_PASSWORD_REQUIRED', Session: 'fake-session' })

    const result = await signIn('teacher@example.com', 'temporary-password')

    expect(result).toEqual({
      status: 'new_password_required',
      session: 'fake-session',
      username: 'teacher@example.com',
    })
  })

  it('sends only a plain JSON POST — no AWS SigV4/credential headers', async () => {
    mockCognitoResponse({
      AuthenticationResult: { AccessToken: 't', IdToken: 'i', ExpiresIn: 1, TokenType: 'Bearer' },
    })

    await signIn('teacher@example.com', 'hunter2')

    const [, init] = vi.mocked(globalThis.fetch).mock.calls[0]
    const headerNames = [...new Headers(init?.headers).keys()]
    expect(headerNames.sort()).toEqual(['content-type', 'x-amz-target'])
  })
})

describe('cognito completeNewPassword', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('defaults preferred_username to the email — the pool requires it but this app has no separate username', async () => {
    mockCognitoResponse({
      AuthenticationResult: { AccessToken: 'fake-token', IdToken: 'x', ExpiresIn: 3600, TokenType: 'Bearer' },
    })

    await completeNewPassword('teacher@example.com', 'new-secure-password', 'fake-session')

    const fetchSpy = vi.mocked(globalThis.fetch)
    const [, init] = fetchSpy.mock.calls[0]
    const headers = new Headers(init?.headers)
    expect(headers.get('X-Amz-Target')).toBe('AWSCognitoIdentityProviderService.RespondToAuthChallenge')

    const body = JSON.parse(init?.body as string)
    expect(body).toEqual({
      ChallengeName: 'NEW_PASSWORD_REQUIRED',
      ClientId: '7amuvrc9l1sn727kqp6paraoqk',
      Session: 'fake-session',
      ChallengeResponses: {
        USERNAME: 'teacher@example.com',
        NEW_PASSWORD: 'new-secure-password',
        'userAttributes.preferred_username': 'teacher@example.com',
      },
    })
  })
})
