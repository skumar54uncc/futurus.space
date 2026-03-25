import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap transition-colors",
  {
    variants: {
      variant: {
        default: "bg-[--bg-elevated] text-[--text-secondary] border-[--border-default]",
        secondary: "bg-[--bg-elevated] text-[--text-secondary] border-[--border-default]",
        outline: "bg-transparent text-[--text-secondary] border-[--border-default]",
        success:
          "bg-[--accent-success-muted] text-[#34d399] border-[rgba(16,185,129,0.25)]",
        warning:
          "bg-[--accent-warning-muted] text-[#fbbf24] border-[rgba(245,158,11,0.25)]",
        destructive:
          "bg-[--accent-danger-muted] text-[#f87171] border-[rgba(239,68,68,0.25)]",
        danger: "bg-[--accent-danger-muted] text-[#f87171] border-[rgba(239,68,68,0.25)]",
        info: "bg-[rgba(6,182,212,0.10)] text-[#22d3ee] border-[rgba(6,182,212,0.25)]",
        accent: "bg-[--accent-primary-muted] text-[--text-accent] border-[--border-accent]",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>;

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
  animated?: boolean;
}

const dotColorMap: Record<string, string> = {
  success: "bg-[#34d399]",
  warning: "bg-[#fbbf24]",
  danger: "bg-[#f87171]",
  destructive: "bg-[#f87171]",
  info: "bg-[#22d3ee]",
  accent: "bg-[--accent-primary]",
  default: "bg-[--text-tertiary]",
  secondary: "bg-[--text-tertiary]",
  outline: "bg-[--text-tertiary]",
};

function Badge({ className, variant, dot, animated, children, ...props }: BadgeProps) {
  const dotColor = dotColorMap[variant ?? "default"] ?? "bg-[--text-tertiary]";

  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span
          className={cn("w-1.5 h-1.5 rounded-full shrink-0", dotColor, animated && "animate-pulse-dot")}
          aria-hidden
        />
      )}
      {children}
    </span>
  );
}

export const STATUS_VARIANT: Record<string, BadgeProps["variant"]> = {
  queued: "default",
  building_seed: "info",
  generating_personas: "info",
  running: "accent",
  generating_report: "warning",
  completed: "success",
  failed: "danger",
  revoked: "default",
};

export const STATUS_LABEL: Record<string, string> = {
  queued: "Queued",
  building_seed: "Building seed",
  generating_personas: "Generating personas",
  running: "Running",
  generating_report: "Building report",
  completed: "Completed",
  failed: "Failed",
  revoked: "Stopped",
};

const ANIMATED_STATUSES = new Set([
  "building_seed",
  "generating_personas",
  "running",
  "generating_report",
]);

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant={STATUS_VARIANT[status] ?? "default"} dot animated={ANIMATED_STATUSES.has(status)}>
      {STATUS_LABEL[status] ?? status}
    </Badge>
  );
}

export { Badge, badgeVariants };
