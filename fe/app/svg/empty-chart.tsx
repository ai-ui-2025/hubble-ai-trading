import * as React from "react";

/**
 * Chart empty state icon - bold lines
 */
export const EmptyChart = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    width="64"
    height="64"
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    {...props}
  >
    {/* 坐标轴 */}
    <line
      x1="8"
      y1="56"
      x2="56"
      y2="56"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
    />
    <line
      x1="8"
      y1="56"
      x2="8"
      y2="8"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
    />
    {/* 图表线 */}
    <polyline
      points="12,48 20,40 28,32 36,24 44,16 52,12"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

