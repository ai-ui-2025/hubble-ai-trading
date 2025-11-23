import type { FC } from "react";
import type { ComputedPortfolio } from "../hooks/use-trader-portfolios";

interface PortfolioCardProps {
  portfolio: ComputedPortfolio;
  currentIndex: number;
  totalCount: number;
  onPrevious: () => void;
  onNext: () => void;
}

/**
 * Format number as currency (USD)
 */
function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format number with appropriate decimal places
 */
function formatNumber(value: number, decimals: number = 2): string {
  return value.toFixed(decimals);
}

/**
 * Portfolio card component displaying a single trader's portfolio
 */
export const PortfolioCard: FC<PortfolioCardProps> = ({
  portfolio,
  currentIndex,
  totalCount,
  onPrevious,
  onNext,
}) => {
  const { traderName, totalAssets, positions } = portfolio;

  return (
    <div className="cyber-border bg-card/30 text-foreground h-full flex flex-col overflow-hidden relative">
      {/* Scanline effect for this card */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/5 to-transparent opacity-0 hover:opacity-100 pointer-events-none transition-opacity duration-500" style={{ backgroundSize: '100% 3px' }} />
      
      {/* Header */}
      <div className="border-b border-primary/20 bg-muted/50 px-4 py-3 relative">
        <div className="absolute top-0 left-0 w-1 h-full bg-primary"></div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-bold tracking-widest text-primary uppercase drop-shadow-[0_0_2px_rgba(var(--primary),0.5)]">
              {traderName}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onPrevious}
              className="w-6 h-6 border border-primary/30 bg-background hover:bg-primary hover:text-primary-foreground flex items-center justify-center transition-all duration-200 group"
              aria-label="Previous"
            >
              <svg className="w-3 h-3 group-hover:scale-110 transition-transform" fill="currentColor" viewBox="0 0 20 20">
                <path d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" />
              </svg>
            </button>
            <span className="text-xs text-muted-foreground min-w-12 text-center font-medium font-mono">
              {currentIndex + 1} <span className="text-primary/50">/</span> {totalCount}
            </span>
            <button
              onClick={onNext}
              className="w-6 h-6 border border-primary/30 bg-background hover:bg-primary hover:text-primary-foreground flex items-center justify-center transition-all duration-200 group"
              aria-label="Next"
            >
              <svg className="w-3 h-3 group-hover:scale-110 transition-transform" fill="currentColor" viewBox="0 0 20 20">
                <path d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Total Assets */}
      <div className="border-b border-primary/20 bg-card/50 px-4 py-3 flex justify-between items-end relative overflow-hidden">
        <div className="absolute right-0 top-0 p-1 opacity-10">
           <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="text-primary"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground mb-1 font-bold uppercase tracking-[0.2em]">
            Total Assets
          </div>
          <div className="text-xl font-black text-foreground font-mono tracking-tighter">
            {formatCurrency(totalAssets)}
          </div>
        </div>
        <div className="text-[10px] text-primary animate-pulse font-mono">
          ● LIVE
        </div>
      </div>

      {/* Positions Table */}
      <div className="overflow-x-auto flex-1 custom-scrollbar">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 z-10 bg-background/90 backdrop-blur-sm border-b border-primary/20">
            <tr>
              <th className="text-left py-2 px-3 text-[10px] font-bold text-muted-foreground uppercase tracking-wider font-mono">
                Sym
              </th>
              <th className="text-right py-2 px-3 text-[10px] font-bold text-muted-foreground uppercase tracking-wider font-mono">
                Qty
              </th>
              <th className="text-right py-2 px-3 text-[10px] font-bold text-muted-foreground uppercase tracking-wider font-mono">
                Entry
              </th>
              <th className="text-right py-2 px-3 text-[10px] font-bold text-muted-foreground uppercase tracking-wider font-mono">
                Side
              </th>
              <th className="text-right py-2 px-3 text-[10px] font-bold text-muted-foreground uppercase tracking-wider font-mono">
                Lev
              </th>
            </tr>
          </thead>
          <tbody className="font-mono text-xs">
            {positions.map((position) => {
              const directionColor =
                position.direction === "long" ? "text-chart-1 drop-shadow-[0_0_3px_rgba(var(--color-chart-1),0.5)]" : "text-destructive drop-shadow-[0_0_3px_rgba(var(--color-destructive),0.5)]";

              return (
                <tr
                  key={position.symbol}
                  className="border-b border-primary/5 hover:bg-primary/5 transition-colors group"
                >
                  <td className="py-2 px-3">
                    <span className="font-bold text-foreground group-hover:text-primary transition-colors">
                      {position.symbol}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-right text-muted-foreground group-hover:text-foreground">
                    {formatNumber(position.quantity, 4)}
                  </td>
                  <td className="py-2 px-3 text-right text-muted-foreground group-hover:text-foreground">
                    {formatCurrency(position.entryPrice)}
                  </td>
                  <td className={`py-2 px-3 text-right font-bold uppercase ${directionColor}`}>
                    {position.direction === "long" ? "LONG" : "SHORT"}
                  </td>
                  <td className="py-2 px-3 text-right text-accent">
                    {formatNumber(position.leverage, 0)}x
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
