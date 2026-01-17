/**
 * API utilities for making authenticated requests to the backend.
 * Uses Clerk session tokens for authentication.
 */

/**
 * Creates an authenticated fetch function that includes the Clerk session token.
 * 
 * @param getToken - Function to get the Clerk session token (from useAuth hook)
 * @returns A fetch function that automatically includes the Authorization header
 */
export function createAuthenticatedFetch(getToken: () => Promise<string | null>) {
  return async (url: string, options: RequestInit = {}): Promise<Response> => {
    const token = await getToken();
    
    const headers = new Headers(options.headers);
    
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    
    return fetch(url, {
      ...options,
      headers,
    });
  };
}

/**
 * Get the base API URL from environment variables.
 */
export function getApiUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (envUrl) return envUrl;

  if (process.env.NODE_ENV === 'development') return 'http://localhost:8000';

  return '';
}

/**
 * Helper to make authenticated GET requests.
 */
export async function authGet<T>(
  url: string,
  getToken: () => Promise<string | null>
): Promise<T> {
  const authFetch = createAuthenticatedFetch(getToken);
  const response = await authFetch(url);
  
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }
  
  return response.json();
}

/**
 * Helper to make authenticated POST requests.
 */
export async function authPost<T>(
  url: string,
  body: unknown,
  getToken: () => Promise<string | null>
): Promise<T> {
  const authFetch = createAuthenticatedFetch(getToken);
  const response = await authFetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }
  
  return response.json();
}

/**
 * Helper to make authenticated POST requests with FormData (for file uploads).
 */
export async function authPostFormData<T>(
  url: string,
  formData: FormData,
  getToken: () => Promise<string | null>
): Promise<T> {
  const authFetch = createAuthenticatedFetch(getToken);
  const response = await authFetch(url, {
    method: 'POST',
    body: formData,
    // Don't set Content-Type header - browser will set it with boundary for FormData
  });
  
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }
  
  return response.json();
}

/**
 * Helper to make authenticated PATCH requests.
 */
export async function authPatch<T>(
  url: string,
  body: unknown,
  getToken: () => Promise<string | null>
): Promise<T> {
  const authFetch = createAuthenticatedFetch(getToken);
  const response = await authFetch(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }
  
  return response.json();
}

/**
 * Helper to make authenticated DELETE requests.
 */
export async function authDelete<T>(
  url: string,
  getToken: () => Promise<string | null>
): Promise<T> {
  const authFetch = createAuthenticatedFetch(getToken);
  const response = await authFetch(url, {
    method: 'DELETE',
  });
  
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }
  
  return response.json();
}
