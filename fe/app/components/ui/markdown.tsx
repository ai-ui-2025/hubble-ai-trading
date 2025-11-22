import type { ComponentPropsWithoutRef } from "react"
import ReactMarkdown, { type MarkdownToJSX } from "markdown-to-jsx"

import { cn } from "~/lib/utils"

type MarkdownProps = ComponentPropsWithoutRef<typeof ReactMarkdown> & {
  className?: string
  variant?: "default" | "phase"
}

const PHASE_COMPONENTS: MarkdownToJSX.Overrides = {
  h1: ({ children, ...props }) => (
    <h1 {...props} className="mt-4 mb-2 text-sm font-black tracking-widest uppercase text-primary border-b border-primary/20 pb-1 font-mono flex items-center gap-2">
      <span className="w-1.5 h-1.5 bg-primary/50 rounded-full shadow-[0_0_5px_rgba(var(--primary),0.5)]" />
      {children}
    </h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 {...props} className="mt-3 mb-2 text-xs font-bold tracking-wider uppercase text-purple-400 font-mono flex items-center gap-2">
      <span className="text-purple-400/50 text-[10px]">›</span>
      {children}
    </h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 {...props} className="mt-2 mb-1 text-xs font-bold text-accent font-mono pl-2 border-l-2 border-accent/30">
      {children}
    </h3>
  ),
  h4: ({ children, ...props }) => (
    <h4 {...props} className="mt-2 mb-1 text-[11px] font-bold text-foreground/80 font-mono">
      {children}
    </h4>
  ),
  p: ({ children, ...props }) => (
    <p {...props} className="leading-relaxed mb-2 font-mono text-[11px] text-inherit">
      {children}
    </p>
  ),
  a: ({ children, ...props }) => (
    <a {...props} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-accent underline decoration-dotted underline-offset-2 transition-all duration-300 font-bold text-[11px] cursor-pointer">
      {children}
    </a>
  ),
  ul: ({ children, ...props }) => (
    <ul {...props} className="my-2 ml-2 list-none space-y-1">
      {children}
    </ul>
  ),
  ol: ({ children, ...props }) => (
    <ol {...props} className="my-2 ml-2 list-decimal space-y-1 text-primary/70 text-[10px] marker:text-primary/30 marker:font-mono">
      {children}
    </ol>
  ),
  li: ({ children, ...props }) => (
    <li {...props} className="relative pl-3 text-muted-foreground font-mono text-[11px] before:content-['·'] before:absolute before:left-0 before:text-primary/40 before:font-black">
      {children}
    </li>
  ),
  blockquote: ({ children, ...props }) => (
    <blockquote {...props} className="mt-2 border-l border-primary/30 bg-primary/5 py-1 pl-2 italic text-muted-foreground text-[11px]">
      {children}
    </blockquote>
  ),
  code: ({ children, className, ...props }) => {
    const isInline = !className?.includes("lang-") && !props.children?.toString().includes("\n");
    return (
      <code
        {...props}
        className={cn(
          "font-mono text-[10px]",
          isInline 
            ? "rounded bg-muted/50 px-1 py-0.5 text-accent border border-border/30"
            : "block w-full text-foreground bg-transparent p-0",
          className
        )}
      >
        {children}
      </code>
    )
  },
  pre: ({ children, ...props }) => (
    <div className="relative my-2 overflow-hidden rounded border border-primary/10 bg-card/30 group">
       <div className="absolute top-0 left-0 right-0 h-4 bg-muted/30 border-b border-primary/5 flex items-center px-2 space-x-1 pointer-events-none">
         <div className="w-1.5 h-1.5 rounded-full bg-primary/20" />
       </div>
      <pre {...props} className="overflow-x-auto p-2 pt-6 text-[10px] custom-scrollbar select-text">
        {children}
      </pre>
    </div>
  ),
  hr: ({ ...props }) => (
    <hr {...props} className="my-4 border-primary/10 border-dashed" />
  ),
  table: ({ children, ...props }) => (
    <div className="my-2 w-full overflow-y-auto rounded border border-border/50 bg-card/20">
      <table {...props} className="w-full">
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }) => (
    <thead {...props} className="bg-muted/30 border-b border-primary/10">
      {children}
    </thead>
  ),
  tr: ({ children, ...props }) => (
    <tr {...props} className="border-t border-border/30 hover:bg-primary/5 transition-colors">
      {children}
    </tr>
  ),
  th: ({ children, ...props }) => (
    <th {...props} className="px-2 py-1 text-left font-bold uppercase text-primary text-[10px] tracking-wider">
      {children}
    </th>
  ),
  td: ({ children, ...props }) => (
    <td {...props} className="px-2 py-1 text-left text-[10px] font-mono text-muted-foreground">
      {children}
    </td>
  ),
}

const COMPONENTS: MarkdownToJSX.Overrides = {
  h1: ({ children, ...props }) => (
    <h1 {...props} className="mt-3 mb-4 text-2xl font-bold tracking-widest uppercase text-primary border-b border-primary/30 pb-2 font-mono relative pl-8 before:content-['#'] before:absolute before:left-0 before:text-primary/50">
      {children}
    </h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 {...props} className="mt-8 mb-4 text-xl font-bold tracking-wider uppercase text-purple-400 border-b border-purple-400/30 pb-2 font-mono relative pl-10 before:content-['##'] before:absolute before:left-0 before:text-purple-400/50">
      {children}
    </h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 {...props} className="mt-6 mb-3 text-lg font-bold tracking-wide text-accent font-mono relative pl-12 before:content-['###'] before:absolute before:left-0 before:text-accent/50">
      {children}
    </h3>
  ),
  h4: ({ children, ...props }) => (
    <h4 {...props} className="mt-6 mb-3 text-base font-bold text-foreground font-mono">
      {children}
    </h4>
  ),
  p: ({ children, ...props }) => (
    <p {...props} className="leading-7 mb-4 text-foreground/90 font-mono text-sm">
      {children}
    </p>
  ),
  a: ({ children, ...props }) => (
    <a {...props} className="text-primary hover:text-accent underline decoration-dotted underline-offset-4 transition-all duration-300 font-bold hover:decoration-solid">
      {children}
    </a>
  ),
  ul: ({ children, ...props }) => (
    <ul {...props} className="my-4 ml-4 list-none space-y-2">
      {children}
    </ul>
  ),
  ol: ({ children, ...props }) => (
    <ol {...props} className="my-4 ml-4 list-decimal space-y-2 text-primary marker:text-primary/50 marker:font-mono">
      {children}
    </ol>
  ),
  li: ({ children, ...props }) => {
    return (
      <li {...props} className="relative pl-2 text-foreground/90 font-mono text-sm [&>ul]:my-2 [&>ol]:my-2">
        {children}
      </li>
    )
  },
  blockquote: ({ children, ...props }) => (
    <blockquote {...props} className="mt-6 border-l-2 border-primary bg-primary/5 py-2 pl-4 italic text-muted-foreground shadow-[inset_10px_0_20px_-10px_rgba(var(--primary),0.1)]">
      {children}
    </blockquote>
  ),
  code: ({ children, className, ...props }) => {
    const isInline = !className?.includes("lang-") && !props.children?.toString().includes("\n");
    return (
      <code
        {...props}
        className={cn(
          "font-mono text-sm",
          isInline 
            ? "rounded bg-muted px-[0.3rem] py-[0.1rem] text-accent border border-border/50"
            : "block w-full text-foreground bg-transparent p-0",
          className
        )}
      >
        {children}
      </code>
    )
  },
  pre: ({ children, ...props }) => (
    <div className="relative my-4 overflow-hidden rounded-lg border border-primary/20 bg-card/50 shadow-sm group">
      <div className="absolute top-0 left-0 right-0 h-6 bg-muted/50 border-b border-primary/10 flex items-center px-2 space-x-1 pointer-events-none">
        <div className="w-2 h-2 rounded-full bg-red-500/50" />
        <div className="w-2 h-2 rounded-full bg-yellow-500/50" />
        <div className="w-2 h-2 rounded-full bg-green-500/50" />
      </div>
      <pre {...props} className="overflow-x-auto p-4 pt-8 text-sm custom-scrollbar select-text">
        {children}
      </pre>
      <div className="absolute top-0 right-0 p-1 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
         <div className="text-[10px] text-muted-foreground font-mono px-2 bg-background/80 backdrop-blur border border-border rounded">TERMINAL</div>
      </div>
    </div>
  ),
  hr: ({ ...props }) => (
    <hr {...props} className="my-8 border-primary/20 border-dashed" />
  ),
  table: ({ children, ...props }) => (
    <div className="my-6 w-full overflow-y-auto rounded-lg border border-border bg-card/30">
      <table {...props} className="w-full">
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }) => (
    <thead {...props} className="bg-muted/50 border-b border-primary/20">
      {children}
    </thead>
  ),
  tr: ({ children, ...props }) => (
    <tr {...props} className="m-0 border-t border-border p-0 even:bg-muted/20 hover:bg-primary/5 transition-colors">
      {children}
    </tr>
  ),
  th: ({ children, ...props }) => (
    <th {...props} className="border border-primary/10 px-4 py-2 text-left font-bold uppercase tracking-wider text-primary [[align=center]]:text-center [[align=right]]:text-right text-xs">
      {children}
    </th>
  ),
  td: ({ children, ...props }) => (
    <td {...props} className="border border-primary/10 px-4 py-2 text-left [[align=center]]:text-center [[align=right]]:text-right text-xs font-mono text-muted-foreground">
      {children}
    </td>
  ),
}

/**
 * Cyberpunk-themed markdown renderer using markdown-to-jsx.
 * Features:
 * - Neon accents and monospaced fonts
 * - Terminal-like code blocks
 * - Glitch-inspired headers
 * - Data-grid style tables
 */
export function Markdown({ className, options, variant = "default", ...props }: MarkdownProps) {
  const components = variant === "phase" ? PHASE_COMPONENTS : COMPONENTS;
  return (
    <div
      className={cn(
        "prose prose-invert max-w-none select-text",
        variant === "default" && "[&_ul>li]:relative [&_ul>li]:pl-6 [&_ul>li]:before:content-['>'] [&_ul>li]:before:absolute [&_ul>li]:before:left-1 [&_ul>li]:before:text-primary",
        variant === "phase" && "text-[11px] leading-relaxed text-foreground [&_p]:text-inherit [&_div]:text-inherit", 
        className
      )}
    >
      <ReactMarkdown
        options={{
          overrides: components,
          ...options,
        }}
        {...props}
      />
    </div>
  )
}
