// Talks to Cognito's IdP API directly over HTTPS (the same requests the AWS SDK's
// InitiateAuthCommand/RespondToAuthChallengeCommand would make) — no AWS SDK
// dependency needed for a single public app client with USER_PASSWORD_AUTH enabled.

// Region + app client ID are the only two pieces of Cognito config this direct
// InitiateAuth call needs — the user pool ID isn't part of the public
// InitiateAuth request (only AdminInitiateAuth takes it); the pool ID matters
// server-side, for JWKS validation. Both env vars are non-secret (this app
// client has no client secret), so hardcoded fallbacks are safe to ship.
const COGNITO_REGION = (import.meta.env.VITE_COGNITO_REGION as string | undefined) ?? 'us-east-2'
const COGNITO_APP_CLIENT_ID =
  (import.meta.env.VITE_COGNITO_APP_CLIENT_ID as string | undefined) ?? '4tpkjhn2v74cjr9rbmca3kjih8'
const COGNITO_ENDPOINT = `https://cognito-idp.${COGNITO_REGION}.amazonaws.com/`

export class CognitoAuthError extends Error {
  code?: string

  constructor(message: string, code?: string) {
    super(message)
    this.code = code
  }
}

interface AuthenticationResult {
  AccessToken: string
  IdToken: string
  RefreshToken?: string
  ExpiresIn: number
  TokenType: string
}

interface CognitoResponse {
  ChallengeName?: string
  Session?: string
  AuthenticationResult?: AuthenticationResult
  message?: string
  __type?: string
}

async function cognitoRequest(target: string, body: Record<string, unknown>): Promise<CognitoResponse> {
  let response: Response
  try {
    response = await fetch(COGNITO_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-amz-json-1.1',
        'X-Amz-Target': `AWSCognitoIdentityProviderService.${target}`,
      },
      body: JSON.stringify(body),
    })
  } catch {
    throw new CognitoAuthError('Could not reach the sign-in service.')
  }

  const data = (await response.json().catch(() => ({}))) as CognitoResponse

  if (!response.ok) {
    throw new CognitoAuthError(data.message ?? 'Sign-in failed.', data.__type)
  }

  return data
}

export interface SignedIn {
  status: 'signed_in'
  accessToken: string
  username: string
}

export interface NewPasswordRequired {
  status: 'new_password_required'
  session: string
  username: string
}

export type SignInOutcome = SignedIn | NewPasswordRequired

export async function signIn(username: string, password: string): Promise<SignInOutcome> {
  const data = await cognitoRequest('InitiateAuth', {
    AuthFlow: 'USER_PASSWORD_AUTH',
    ClientId: COGNITO_APP_CLIENT_ID,
    AuthParameters: { USERNAME: username, PASSWORD: password },
  })

  if (data.ChallengeName === 'NEW_PASSWORD_REQUIRED') {
    if (!data.Session) throw new CognitoAuthError('Sign-in failed.')
    return { status: 'new_password_required', session: data.Session, username }
  }

  if (!data.AuthenticationResult) throw new CognitoAuthError('Sign-in failed.')
  return {
    status: 'signed_in',
    accessToken: data.AuthenticationResult.AccessToken,
    username,
  }
}

export async function completeNewPassword(
  username: string,
  newPassword: string,
  session: string,
): Promise<SignedIn> {
  const data = await cognitoRequest('RespondToAuthChallenge', {
    ChallengeName: 'NEW_PASSWORD_REQUIRED',
    ClientId: COGNITO_APP_CLIENT_ID,
    Session: session,
    ChallengeResponses: { USERNAME: username, NEW_PASSWORD: newPassword },
  })

  if (!data.AuthenticationResult) throw new CognitoAuthError('Could not set the new password.')
  return {
    status: 'signed_in',
    accessToken: data.AuthenticationResult.AccessToken,
    username,
  }
}
