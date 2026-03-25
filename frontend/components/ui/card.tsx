import * as React from "react";
import { cn } from "@/lib/utils";

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("rounded-lg border bg-card text-card-foreground shadow-sm", className)} {...props} />
  )
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />
  )
);
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("text-2xl font-semibold leading-none tracking-tight", className)} {...props} />
  )
);
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />
  )
);
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
  )
);
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center p-6 pt-0", className)} {...props} />
  )
);
CardFooter.displayName = "CardFooter";

export interface FuturusCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "glass" | "glow" | "flat" | "danger";
  padding?: "none" | "sm" | "md" | "lg";
  hoverable?: boolean;
  interactive?: boolean;
}

export const FCard = React.forwardRef<HTMLDivElement, FuturusCardProps>(
  (
    { className, variant = "default", padding = "md", hoverable, interactive, children, ...props },
    ref
  ) => {
    const padMap = { none: "", sm: "p-4", md: "p-5", lg: "p-6 md:p-8" };
    const varMap = {
      default: "bg-[--bg-surface] border border-[--border-subtle]",
      glass: "bg-[--bg-glass] border border-[--border-subtle] backdrop-blur-xl",
      glow: "bg-[--bg-surface] border border-[--border-accent] shadow-[0_0_32px_rgba(99,102,241,0.10)]",
      flat: "bg-[--bg-elevated]",
      danger: "bg-[--accent-danger-muted] border border-[rgba(239,68,68,0.20)]",
    };
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-[16px] overflow-hidden",
          varMap[variant],
          padMap[padding],
          (hoverable || interactive) &&
            "transition-all duration-200 hover:border-[--border-default] hover:-translate-y-0.5 hover:shadow-[0_4px_24px_rgba(0,0,0,0.3)]",
          interactive && "cursor-pointer",
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);
FCard.displayName = "FCard";

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
