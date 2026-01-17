/**
 * Custom hook for making authenticated API calls using Clerk.
 */

import { useAuth } from '@clerk/nextjs';
import { useCallback } from 'react';
import {
  authGet,
  authPost,
  authPostFormData,
  authPatch,
  authDelete,
  getApiUrl,
} from '@/lib/api';

/**
 * Hook that provides authenticated API methods using Clerk session tokens.
 * 
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { get, post, isLoaded, isSignedIn } = useApi();
 *   
 *   const fetchGoals = async () => {
 *     if (!isSignedIn) return;
 *     const goals = await get('/api/v1/goals');
 *     console.log(goals);
 *   };
 * }
 * ```
 */
export function useApi() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  
  const apiUrl = getApiUrl();
  
  /**
   * Make an authenticated GET request.
   */
  const get = useCallback(
    async <T>(endpoint: string): Promise<T> => {
      const url = `${apiUrl}${endpoint}`;
      return authGet<T>(url, getToken);
    },
    [apiUrl, getToken]
  );
  
  /**
   * Make an authenticated POST request with JSON body.
   */
  const post = useCallback(
    async <T>(endpoint: string, body: unknown): Promise<T> => {
      const url = `${apiUrl}${endpoint}`;
      return authPost<T>(url, body, getToken);
    },
    [apiUrl, getToken]
  );
  
  /**
   * Make an authenticated POST request with FormData (for file uploads).
   */
  const postFormData = useCallback(
    async <T>(endpoint: string, formData: FormData): Promise<T> => {
      const url = `${apiUrl}${endpoint}`;
      return authPostFormData<T>(url, formData, getToken);
    },
    [apiUrl, getToken]
  );
  
  /**
   * Make an authenticated PATCH request.
   */
  const patch = useCallback(
    async <T>(endpoint: string, body: unknown): Promise<T> => {
      const url = `${apiUrl}${endpoint}`;
      return authPatch<T>(url, body, getToken);
    },
    [apiUrl, getToken]
  );
  
  /**
   * Make an authenticated DELETE request.
   */
  const del = useCallback(
    async <T>(endpoint: string): Promise<T> => {
      const url = `${apiUrl}${endpoint}`;
      return authDelete<T>(url, getToken);
    },
    [apiUrl, getToken]
  );
  
  return {
    get,
    post,
    postFormData,
    patch,
    del,
    isLoaded,
    isSignedIn,
    apiUrl,
  };
}
