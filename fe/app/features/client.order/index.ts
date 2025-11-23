/**
 * Client-side order management feature
 *
 * This feature provides React components and hooks for displaying
 * trader orders with infinite scrolling pagination.
 *
 * @example
 * ```tsx
 * import { OrderList } from "~/features/client.order";
 *
 * function TraderOrdersPage({ traderId }: { traderId: string }) {
 *   return (
 *     <div>
 *       <h1>Orders</h1>
 *       <OrderList filters={{ traderId }} />
 *     </div>
 *   );
 * }
 * ```
 */

// Hooks
export { useOrders, useLatestOrders, orderKeys } from "./hooks/use-orders";
export type { OrderFilters } from "./hooks/use-orders";

// Components
export { OrderCard } from "./components/OrderCard";
export { OrderList } from "./components/OrderList";
