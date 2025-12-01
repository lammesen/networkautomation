import { useCallback } from "react";

/**
 * Get CSRF token from cookies
 */
function getCsrfFromCookie(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

/**
 * Hook for CSRF token management
 * Provides the token and helper functions for making authenticated requests
 */
export function useCsrf() {
  const getToken = useCallback((): string => {
    // Try global webnet object first (set by base.html)
    const globalToken = (window as any).webnet?.getCsrfToken?.();
    if (globalToken) return globalToken;

    // Fall back to cookie
    return getCsrfFromCookie();
  }, []);

  const getHeaders = useCallback((): HeadersInit => {
    return {
      "X-CSRFToken": getToken(),
      "Content-Type": "application/json",
    };
  }, [getToken]);

  const fetchWithCsrf = useCallback(
    async (url: string, options: RequestInit = {}): Promise<Response> => {
      const headers = new Headers(options.headers);
      headers.set("X-CSRFToken", getToken());

      if (!headers.has("Content-Type") && options.body) {
        headers.set("Content-Type", "application/json");
      }

      return fetch(url, {
        ...options,
        headers,
        credentials: "same-origin",
      });
    },
    [getToken]
  );

  return {
    token: getToken(),
    getToken,
    getHeaders,
    fetchWithCsrf,
  };
}

export default useCsrf;
