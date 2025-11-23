import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import type {
  Order,
  OrderSide,
  OrderStatus,
  GetOrdersResponse,
} from "~/features/order";

/**
 * Query keys for orders
 */
export const orderKeys = {
  all: ["orders"] as const,
  lists: () => [...orderKeys.all, "list"] as const,
  list: (filters: OrderFilters) => [...orderKeys.lists(), filters] as const,
};

/**
 * Filters for order queries
 */
export interface OrderFilters {
  traderId?: string;
  symbol?: string;
  side?: OrderSide;
  status?: OrderStatus;
  startTime?: number;
  endTime?: number;
}

/**
 * API response structure
 */
interface OrdersApiResponse {
  success: boolean;
  data?: GetOrdersResponse;
  error?: string;
}

/**
 * Fetch orders from API with pagination
 */
async function fetchOrders(
  filters: OrderFilters,
  pageParam: number
): Promise<GetOrdersResponse> {
  const searchParams = new URLSearchParams();

  // Add filters
  if (filters.traderId) searchParams.set("traderId", filters.traderId);
  if (filters.symbol) searchParams.set("symbol", filters.symbol);
  if (filters.side) searchParams.set("side", filters.side);
  if (filters.status) searchParams.set("status", filters.status);
  if (filters.startTime)
    searchParams.set("startTime", filters.startTime.toString());
  if (filters.endTime) searchParams.set("endTime", filters.endTime.toString());

  // Pagination
  searchParams.set("limit", "50");
  searchParams.set("offset", pageParam.toString());

  const url = `/api/v1/orders?${searchParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch orders: ${response.statusText}`);
  }

  const result: OrdersApiResponse = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to fetch orders");
  }

  return result.data;
}

/**
 * Hook to fetch orders with infinite scrolling
 *
 * Orders are displayed in reverse chronological order (newest first)
 * and can be filtered by trader, symbol, status, etc.
 *
 * @param filters - Filter criteria for orders
 * @returns Infinite query result with paginated orders
 *
 * @example
 * ```tsx
 * const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useOrders({
 *   traderId: "trader-123",
 *   status: "FILLED"
 * });
 *
 * // Flatten all pages
 * const allOrders = data?.pages.flatMap(page => page.orders) ?? [];
 * ```
 */
export function useOrders(filters: OrderFilters = {}) {
  return useInfiniteQuery({
    queryKey: orderKeys.list(filters),
    queryFn: ({ pageParam }) => fetchOrders(filters, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const { offset, limit, total } = lastPage;
      const nextOffset = offset + limit;
      return nextOffset < total ? nextOffset : undefined;
    },
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}

/**
 * Fetch latest orders
 */
async function fetchLatestOrders(
  traderId?: string,
  limit: number = 20
): Promise<Order[]> {
  const searchParams = new URLSearchParams();
  if (traderId) searchParams.set("traderId", traderId);
  searchParams.set("limit", limit.toString());

  const url = `/api/v1/orders/latest?${searchParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch latest orders: ${response.statusText}`);
  }

  const result = await response.json() as
    | { success: true; data: Order[] }
    | { success: false; error: string };

  if (!result.success || !("data" in result)) {
    throw new Error("error" in result ? result.error : "Failed to fetch latest orders");
  }

  return result.data;
}

/**
 * Hook to fetch the latest orders
 *
 * @param traderId - Optional trader ID to filter orders
 * @param limit - Number of orders to fetch (default: 20, max: 100)
 * @returns Query result with latest orders
 *
 * @example
 * ```tsx
 * // Get latest 20 orders across all traders
 * const { data: latestOrders } = useLatestOrders();
 *
 * // Get latest 50 orders for a specific trader
 * const { data: traderOrders } = useLatestOrders("trader-123", 50);
 * ```
 */
export function useLatestOrders(traderId?: string, limit: number = 20) {
  return useQuery({
    queryKey: [...orderKeys.all, "latest", traderId, limit],
    queryFn: () => fetchLatestOrders(traderId, limit),
    staleTime: 1000 * 30, // 30 seconds
    refetchInterval: 1000 * 60, // Refetch every minute
  });
}
