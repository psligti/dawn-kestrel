

/**
 * API base URL from environment variable or default to localhost
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

/**
 * API response wrapper for standard error handling
 */
export interface ApiError {
  message: string
  status?: number
  code?: string
}

/**
 * Generic fetch helper with automatic error wrapping
 * @param endpoint - API endpoint path (without base URL)
 * @param options - Fetch options
 * @returns Promise resolving to the API response data
 * @throws ApiError on HTTP errors or network failures
 */
export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    // Handle HTTP error responses
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        message: response.statusText || 'An error occurred',
      }))

      throw {
        message: errorData.message || errorData.detail || 'API request failed',
        status: response.status,
        code: response.statusText,
      } as ApiError
    }

    // Parse response JSON
    const data = await response.json()
    return data as T
  } catch (error) {
    // Re-throw API errors
    if ((error as ApiError).status !== undefined) {
      throw error
    }

    // Handle network errors and JSON parse errors
    throw {
      message: error instanceof Error
        ? error.message
        : 'Network error occurred',
      status: 0,
    } as ApiError
  }
}

/**
 * POST request helper
 */
export async function postApi<T>(endpoint: string, data?: unknown): Promise<T> {
  return fetchApi<T>(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  })
}

/**
 * GET request helper
 */
export async function getApi<T>(endpoint: string): Promise<T> {
  return fetchApi<T>(endpoint, {
    method: 'GET',
  })
}

/**
 * DELETE request helper
 */
export async function deleteApi<T>(endpoint: string): Promise<T> {
  return fetchApi<T>(endpoint, {
    method: 'DELETE',
  })
}

/**
 * PUT request helper
 */
export async function putApi<T>(endpoint: string, data?: unknown): Promise<T> {
  return fetchApi<T>(endpoint, {
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  })
}
