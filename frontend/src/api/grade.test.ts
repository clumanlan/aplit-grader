import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearAuth, getAccessToken, setAuthenticated } from '../auth/authStore'
import { gradeEssay, GradeRequestError } from './grade'

const PAYLOAD = { essayText: 'Once upon a time.', assignmentPrompt: 'Analyze the symbol.' }

describe('gradeEssay', () => {
  beforeEach(() => {
    setAuthenticated('fake-access-token', 'teacher@example.com')
  })

  afterEach(() => {
    clearAuth()
    vi.restoreAllMocks()
  })

  it('rejects without calling fetch when there is no access token', async () => {
    clearAuth()
    const fetchSpy = vi.spyOn(globalThis, 'fetch')

    await expect(gradeEssay(PAYLOAD)).rejects.toThrow(GradeRequestError)
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('attaches the access token as a Bearer header', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ criteria: [], sentences: [], section_of: {}, citing_criteria: {} }), {
        status: 200,
      }),
    )

    await gradeEssay(PAYLOAD)

    const [, init] = vi.mocked(globalThis.fetch).mock.calls[0]
    const headers = new Headers(init?.headers)
    expect(headers.get('Authorization')).toBe('Bearer fake-access-token')
  })

  it('clears the stored token and rejects when the backend returns 401', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 401 }))

    await expect(gradeEssay(PAYLOAD)).rejects.toThrow(GradeRequestError)
    expect(getAccessToken()).toBeNull()
  })
})
