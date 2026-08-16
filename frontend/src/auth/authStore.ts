// In-memory only, deliberately not persisted to localStorage/sessionStorage —
// a page refresh signs the teacher out and they log in again. Exposed as a
// plain module-scoped store (not just React state) so non-component code,
// like api/grade.ts, can read the current token without threading it through
// every call site.

type Listener = () => void

export interface AuthState {
  accessToken: string | null
  username: string | null
}

let state: AuthState = { accessToken: null, username: null }
const listeners = new Set<Listener>()

function emit(): void {
  listeners.forEach((listener) => listener())
}

export function getAuthState(): AuthState {
  return state
}

export function getAccessToken(): string | null {
  return state.accessToken
}

export function setAuthenticated(accessToken: string, username: string): void {
  state = { accessToken, username }
  emit()
}

export function clearAuth(): void {
  if (state.accessToken === null) return
  state = { accessToken: null, username: null }
  emit()
}

export function subscribeAuth(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
