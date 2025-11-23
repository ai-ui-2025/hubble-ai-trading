import { useEffect, useState } from "react";

/**
 * Hook to detect if the current viewport is mobile based on width threshold
 * 
 * @param threshold - Width threshold in pixels to determine mobile (default: 768)
 * @returns boolean indicating if the viewport is mobile
 * 
 * @example
 * ```tsx
 * // Use default threshold (768px)
 * const isMobile = useMobile();
 * 
 * // Use custom threshold
 * const isMobile = useMobile(1024);
 * 
 * if (isMobile) {
 *   return <MobileLayout />;
 * }
 * return <DesktopLayout />;
 * ```
 */
export function useMobile(threshold: number = 768): boolean {
  const [isMobile, setIsMobile] = useState(() => {
    // SSR-safe: check if window is available
    if (typeof window === "undefined") {
      return false;
    }
    return window.innerWidth < threshold;
  });

  useEffect(() => {
    // SSR-safe: check if window is available
    if (typeof window === "undefined") {
      return;
    }

    const handleResize = () => {
      setIsMobile(window.innerWidth < threshold);
    };

    // Set initial value
    handleResize();

    // Listen for resize events
    window.addEventListener("resize", handleResize);

    // Cleanup
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [threshold]);

  return isMobile;
}


