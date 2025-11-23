import { useQuery } from "@tanstack/react-query";
import type { Order } from "../database/types";

/**
 * Query keys for orders
 */
export const orderKeys = {
  all: ["orders"] as const,
  latest: () => [...orderKeys.all, "latest"] as const,
  latestByTrader: (traderId: string) => [...orderKeys.all, "latest", traderId] as const,
};

/**
 * API response structure for latest orders
 */
export interface LatestOrdersResponse {
  success: boolean;
  data?: Order[];
  error?: string;
  message?: string;
}

/**
 * Fetch latest orders from API
 */
async function fetchLatestOrders(params: {
  traderId?: string;
  limit?: number;
}): Promise<Order[]> {
  const { traderId, limit = 20 } = params;

  const searchParams = new URLSearchParams();
  if (traderId) searchParams.set("traderId", traderId);
  if (limit) searchParams.set("limit", limit.toString());

  const url = `/api/v1/orders/latest?${searchParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch latest orders: ${response.statusText}`);
  }

  const result: LatestOrdersResponse = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to fetch latest orders");
  }

  return result.data;
}

/**
 * Hook to fetch latest orders
 *
 * @param options - Query options
 * @returns Query result with latest orders
 */
export function useLatestOrders(options?: {
  traderId?: string;
  limit?: number;
  enabled?: boolean;
  refetchInterval?: number;
}) {
  const {
    traderId,
    limit = 20,
    enabled = true,
    refetchInterval = 1000 * 60, // Default: 1 minute
  } = options || {};

  return useQuery({
    queryKey: traderId ? orderKeys.latestByTrader(traderId) : orderKeys.latest(),
    queryFn: () => fetchLatestOrders({ traderId, limit }),
    enabled,
    staleTime: 1000 * 30, // 30 seconds
    refetchInterval,
  });
}
