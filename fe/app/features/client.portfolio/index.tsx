/**
 * Client Portfolio Feature
 *
 * This feature provides UI components and hooks for displaying trader portfolios.
 * It fetches current position data for all traders and displays them in a paginated view.
 */

// Hooks
export {
  useTraderPortfolios,
  traderPortfolioKeys,
  type ComputedPortfolio,
  type EnrichedInstrumentPosition,
  type PositionRecord,
  type TraderPortfolioData,
  type TraderPortfolioResponse,
} from "./hooks/use-trader-portfolios";

// Components
export { PortfolioCard } from "./components/PortfolioCard";
export { PortfolioList } from "./components/PortfolioList";

// Default export for convenience
export { PortfolioList as default } from "./components/PortfolioList";
