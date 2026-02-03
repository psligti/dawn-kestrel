import { describe, it, expect, vi } from 'vitest'

// Mock fetch
global.fetch = vi.fn()

describe('useApiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchApi handles 200 OK responses', async () => {
    const mockData = { id: 'test-1', title: 'Test Session' }
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    })

    const result = await import('./useApiClient').then((m) => m.fetchApi('/sessions'))

    expect(result).toEqual(mockData)
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/sessions',
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      })
    )
  })

  it('fetchApi handles 404 errors', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ message: 'Not found' }),
    })

    await expect(
      import('./useApiClient').then((m) => m.fetchApi('/sessions/invalid'))
    ).rejects.toMatchObject({
      message: 'Not found',
      status: 404,
    })
  })

  it('fetchApi handles network errors', async () => {
    ;(global.fetch as vi.Mock).mockRejectedValueOnce(new Error('Network error'))

    await expect(
      import('./useApiClient').then((m) => m.fetchApi('/sessions'))
    ).rejects.toMatchObject({
      message: 'Network error',
      status: 0,
    })
  })

  it('postApi makes POST requests', async () => {
    const mockData = { agent_name: 'plan', user_message: 'test' }
    const mockResponse = { id: 'session-1' }
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    })

    const result = await import('./useApiClient').then((m) =>
      m.postApi('/sessions', mockData)
    )

    expect(result).toEqual(mockResponse)
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/sessions',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(mockData),
      })
    )
  })

  it('getApi makes GET requests', async () => {
    const mockData = [{ id: 'session-1', title: 'Test' }]
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    })

    const result = await import('./useApiClient').then((m) => m.getApi('/sessions'))

    expect(result).toEqual(mockData)
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/sessions',
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('deleteApi makes DELETE requests', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    })

    await import('./useApiClient').then((m) => m.deleteApi('/sessions/123'))

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/sessions/123',
      expect.objectContaining({ method: 'DELETE' })
    )
  })

  it('putApi makes PUT requests', async () => {
    const mockData = { title: 'Updated' }
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    })

    await import('./useApiClient').then((m) => m.putApi('/sessions/123', mockData))

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/sessions/123',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify(mockData),
      })
    )
  })
})
