import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  className?: string;
}

/**
 * Unified empty state component - minimal style with bold lines
 */
export function EmptyState({
  icon,
  title,
  description,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`flex h-full items-center justify-center bg-transparent ${className}`}
    >
      <div className="text-center">
        {icon && (
          <div className="mb-4 flex justify-center opacity-50">{icon}</div>
        )}
        <div className="border border-primary/20 bg-card/30 px-8 py-6 backdrop-blur-sm relative overflow-hidden group">
          {/* Scanline effect */}
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" style={{ backgroundSize: '100% 3px' }} />
          
          {/* Corner accents */}
          <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-primary/50" />
          <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-primary/50" />
          <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-primary/50" />
          <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-primary/50" />

          <p className="text-sm font-bold uppercase tracking-widest text-foreground">
            {title}
          </p>
          {description && (
            <p className="mt-2 text-xs font-medium text-muted-foreground font-mono">
              {description}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

