import * as React from "react";

/**
 * Chat empty state icon - bold lines
 */
export const EmptyChat = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    width="64"
    height="64"
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    {...props}
  >
    {/* 聊天气泡 */}
    <path
      d="M16 20 C16 16, 20 12, 28 12 L36 12 C44 12, 48 16, 48 20 L48 36 C48 40, 44 44, 36 44 L20 44 L12 52 L12 36 C12 32, 12 20, 16 20 Z"
      stroke="currentColor"
      strokeWidth="3"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    {/* 对话线 */}
    <line
      x1="22"
      y1="28"
      x2="38"
      y2="28"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
    />
    <line
      x1="22"
      y1="36"
      x2="34"
      y2="36"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
    />
  </svg>
);

