import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api-client";

/**
 * Global React Query configuration
 */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status === 401) {
            return false;
          }
          return failureCount < 3;
        },
        throwOnError: (error) => {
          if (error instanceof ApiError && error.status === 401) {
            console.warn("Authentication expired, redirecting to login");
            return true;
          }
          return true;
        },
      },
      mutations: {
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status === 401) {
            return false;
          }
          return failureCount < 1;
        },
      },
    },
  });
}

/**
 * Global error handling function
 */
export function handleGlobalError(error: Error) {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        console.warn("Authentication expired:", error.message);
        break;
      case 403:
        console.error("Permission denied:", error.message);
        break;
      case 404:
        console.error("Resource not found:", error.message);
        break;
      case 500:
        console.error("Server error:", error.message);
        break;
      default:
        console.error("API error:", error.message);
    }
  } else {
    console.error("Unknown error:", error.message);
  }
}
