import { useCallback, useState } from "react";
import { toast } from "sonner";
import { useCsrf } from "./use-csrf";

type ToastVariant = "success" | "error" | "info" | "warning";

/**
 * Hook for showing toast notifications using Sonner
 * Integrates with the global webnet toast system
 */
export function useToast() {
  const showToast = useCallback(
    (message: string, variant: ToastVariant = "success", options?: { duration?: number }) => {
      const duration = options?.duration ?? 4000;

      switch (variant) {
        case "success":
          toast.success(message, { duration });
          break;
        case "error":
          toast.error(message, { duration });
          break;
        case "warning":
          toast.warning(message, { duration });
          break;
        case "info":
          toast.info(message, { duration });
          break;
        default:
          toast(message, { duration });
      }

      // Also dispatch global event for non-React listeners
      window.dispatchEvent(
        new CustomEvent("webnet:toast", {
          detail: { message, variant },
        })
      );
    },
    []
  );

  return { showToast, toast };
}

type MutationState<T> = {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
};

type MutationOptions<T> = {
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
  successMessage?: string;
  errorMessage?: string;
};

/**
 * Hook for API mutations with loading state and toast notifications
 */
export function useApiMutation<T = unknown>(
  url: string,
  method: "POST" | "PUT" | "PATCH" | "DELETE" = "POST"
) {
  const { fetchWithCsrf } = useCsrf();
  const { showToast } = useToast();
  const [state, setState] = useState<MutationState<T>>({
    data: null,
    error: null,
    isLoading: false,
  });

  const mutate = useCallback(
    async (body?: unknown, options?: MutationOptions<T>) => {
      setState({ data: null, error: null, isLoading: true });

      try {
        const response = await fetchWithCsrf(url, {
          method,
          body: body ? JSON.stringify(body) : undefined,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = method === "DELETE" ? null : await response.json();
        setState({ data: data as T, error: null, isLoading: false });

        if (options?.successMessage) {
          showToast(options.successMessage, "success");
        }

        options?.onSuccess?.(data as T);
        return data as T;
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));
        setState({ data: null, error: err, isLoading: false });

        showToast(options?.errorMessage ?? err.message, "error");
        options?.onError?.(err);
        throw err;
      }
    },
    [url, method, fetchWithCsrf, showToast]
  );

  return {
    ...state,
    mutate,
    reset: () => setState({ data: null, error: null, isLoading: false }),
  };
}

export default useToast;
