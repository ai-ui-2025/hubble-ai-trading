import type { FC } from "react";
import { useState } from "react";
import { useTraderPortfolios } from "../hooks/use-trader-portfolios";
import { PortfolioCard } from "./PortfolioCard";
import { EmptyState } from "~/components/ui/empty-state";
import { EmptyPortfolio } from "~/svg/empty-portfolio";

/**
 * Portfolio list component displaying all trader portfolios with pagination
 */
export const PortfolioList: FC = () => {
  const { data: portfolios, isLoading, error } = useTraderPortfolios();
  const [currentIndex, setCurrentIndex] = useState(0);

  if (isLoading) {
    return (
      <div className="mx-auto border-border bg-card text-foreground h-full flex flex-col">
        {/* Header skeleton */}
        <div className="border-b border-border bg-card px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="h-5 w-32 bg-muted rounded animate-pulse"></div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 border border-border bg-muted animate-pulse"></div>
              <div className="h-4 w-12 bg-muted rounded animate-pulse"></div>
              <div className="w-6 h-6 border border-border bg-muted animate-pulse"></div>
            </div>
          </div>
        </div>

        {/* Total Assets skeleton */}
        <div className="border-b border-border bg-card px-4 py-3">
          <div className="h-3 w-20 bg-muted rounded mb-2 animate-pulse"></div>
          <div className="h-6 w-24 bg-muted rounded animate-pulse" style={{ animationDelay: '0.1s' }}></div>
        </div>

        {/* Table skeleton */}
        <div className="overflow-x-auto flex-1">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-border bg-card">
                <th className="text-left py-2 px-3">
                  <div className="h-4 w-16 bg-muted rounded animate-pulse"></div>
                </th>
                <th className="text-right py-2 px-3">
                  <div className="h-4 w-20 bg-muted rounded animate-pulse"></div>
                </th>
                <th className="text-right py-2 px-3">
                  <div className="h-4 w-16 bg-muted rounded animate-pulse"></div>
                </th>
                <th className="text-right py-2 px-3">
                  <div className="h-4 w-16 bg-muted rounded animate-pulse"></div>
                </th>
              </tr>
            </thead>
            <tbody>
              {[...Array(5)].map((_, idx) => (
                <tr key={idx} className="border-border border-b">
                  <td className="py-3 px-3">
                    <div className="h-4 w-20 bg-muted rounded animate-pulse" style={{ animationDelay: `${idx * 0.1}s` }}></div>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <div className="h-4 w-24 bg-muted rounded animate-pulse ml-auto" style={{ animationDelay: `${idx * 0.1}s` }}></div>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <div className="h-4 w-16 bg-muted rounded animate-pulse ml-auto" style={{ animationDelay: `${idx * 0.1}s` }}></div>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <div className="h-4 w-20 bg-muted rounded animate-pulse ml-auto" style={{ animationDelay: `${idx * 0.1}s` }}></div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <div className="border border-destructive/50 bg-destructive/10 p-8 text-center backdrop-blur-sm">
          <div className="text-destructive text-2xl mb-3">⚠️</div>
          <p className="text-destructive font-black mb-2 text-sm">
            Failed to load portfolios
          </p>
          <p className="text-muted-foreground text-xs font-medium">
            {error instanceof Error ? error.message : "Unknown error"}
          </p>
        </div>
      </div>
    );
  }

  if (!portfolios || portfolios.length === 0) {
    return (
      <EmptyState
        icon={<EmptyPortfolio className="text-primary/50" />}
        title="No Portfolios"
        description="No trader portfolios available to display"
        className="h-full min-h-[400px]"
      />
    );
  }

  const currentPortfolio = portfolios[currentIndex];

  const handlePrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : portfolios.length - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < portfolios.length - 1 ? prev + 1 : 0));
  };

  return (
    <div className="mx-auto h-full flex flex-col">
      <PortfolioCard
        portfolio={currentPortfolio}
        currentIndex={currentIndex}
        totalCount={portfolios.length}
        onPrevious={handlePrevious}
        onNext={handleNext}
      />
    </div>
  );
};
