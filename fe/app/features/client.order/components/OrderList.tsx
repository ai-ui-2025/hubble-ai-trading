import { useEffect, useRef, useMemo } from "react";
import { useOrders, type OrderFilters } from "../hooks/use-orders";
import { OrderCard } from "./OrderCard";
import { EmptyState } from "~/components/ui/empty-state";
import { EmptyOrder } from "~/svg/empty-order";

interface OrderListProps {
  filters?: OrderFilters;
  emptyMessage?: string;
}

/**
 * Order list component with infinite scrolling
 *
 * Orders are displayed in reverse chronological order (newest first).
 * As the user scrolls down, more orders are automatically loaded.
 *
 * @example
 * ```tsx
 * <OrderList
 *   filters={{ traderId: "trader-123", status: "FILLED" }}
 * />
 * ```
 */
export function OrderList({
  filters = {},
  emptyMessage = "No orders found",
}: OrderListProps) {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
  } = useOrders(filters);

  // Ref for the sentinel element (intersection observer target)
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Set up intersection observer for infinite scroll
  useEffect(() => {
    if (!sentinelRef.current || !hasNextPage || isFetchingNextPage) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(sentinelRef.current);

    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Flatten all pages into a single array
  const allOrders = data?.pages.flatMap((page) => page.orders) ?? [];

  // Extract all unique traderIds for consistent color assignment
  const allTraderIds = useMemo(() => {
    const traderIds = new Set<string>();
    allOrders.forEach((order) => {
      if (order.traderId) {
        traderIds.add(order.traderId);
      }
    });
    return Array.from(traderIds).sort();
  }, [allOrders]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full flex-col bg-background">
        {/* Header skeleton */}
        <div className="shrink-0 border-b border-border bg-card px-3 py-2">
          <div className="h-4 w-24 bg-muted rounded animate-pulse"></div>
        </div>

        {/* Scrollable orders skeleton */}
        <div className="flex-1 overflow-y-auto bg-background custom-scrollbar">
          <div className="divide-y divide-border">
            {[...Array(5)].map((_, idx) => (
              <div key={idx} className="p-3 bg-card border-b border-border">
                <div className="space-y-2">
                  <div className="h-4 w-32 bg-muted rounded animate-pulse" style={{ animationDelay: `${idx * 0.1}s` }}></div>
                  <div className="h-3 w-48 bg-muted/80 rounded animate-pulse" style={{ animationDelay: `${idx * 0.1 + 0.05}s` }}></div>
                  <div className="h-3 w-40 bg-muted/60 rounded animate-pulse" style={{ animationDelay: `${idx * 0.1 + 0.1}s` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="text-center">
          <p className="mb-1 text-xs font-bold text-destructive">Failed to load</p>
          <p className="text-xs text-muted-foreground">
            {error instanceof Error ? error.message : "Unknown error"}
          </p>
        </div>
      </div>
    );
  }

  // Empty state
  if (allOrders.length === 0) {
    return (
      <EmptyState
        icon={<EmptyOrder className="text-primary/50" />}
        title={emptyMessage}
        description="No orders available to display"
      />
    );
  }

  // Order list with infinite scroll
  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <div className="shrink-0 border-b border-border bg-card px-3 py-2">
        <h2 className="text-xs font-bold text-foreground tracking-widest">ORDERS</h2>
      </div>

      {/* Scrollable orders */}
      <div className="flex-1 overflow-y-auto bg-background custom-scrollbar">
        <div className="divide-y divide-border">
          {allOrders.map((order) => (
            <OrderCard key={order.id} order={order} allTraderIds={allTraderIds} />
          ))}

          {/* Sentinel element for intersection observer */}
          {hasNextPage && (
            <div ref={sentinelRef} className="flex justify-center py-4 border-t border-border">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {isFetchingNextPage ? (
                  <>
                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-primary" />
                    <span>Loading more...</span>
                  </>
                ) : (
                  <span>Scroll for more</span>
                )}
              </div>
            </div>
          )}

          {/* End of list indicator */}
          {!hasNextPage && allOrders.length > 0 && (
            <div className="flex justify-center py-4 border-t border-border">
              <p className="text-xs text-muted-foreground">No more orders to load</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
