import { useSyncExternalStore } from 'react'
import { type AuthState, getAuthState, subscribeAuth } from './authStore'

export function useAuth(): AuthState {
  return useSyncExternalStore(subscribeAuth, getAuthState, getAuthState)
}
