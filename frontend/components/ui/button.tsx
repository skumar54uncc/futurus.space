import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  [
    "relative inline-flex items-center justify-center gap-2 whitespace-nowrap",
    "font-medium select-none",
    "transition-all duration-200",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none",
    "active:scale-[0.97]",
  ].join(" "),
  {
    variants: {
      variant: {
        default:
          "bg-[--accent-primary] text-white rounded-[10px] shadow-[0_0_20px_rgba(99,102,241,0.25)] hover:bg-[--accent-primary-hover] hover:shadow-[0_0_32px_rgba(99,102,241,0.45)]",
        primary:
          "bg-[--accent-primary] text-white rounded-[10px] shadow-[0_0_20px_rgba(99,102,241,0.25)] hover:bg-[--accent-primary-hover] hover:shadow-[0_0_32px_rgba(99,102,241,0.45)]",
        secondary:
          "bg-[--bg-elevated] text-[--text-primary] rounded-[10px] border border-[--border-default] hover:border-[--border-strong] hover:bg-[--bg-glass-hover]",
        ghost:
          "bg-transparent text-[--text-secondary] rounded-[10px] hover:bg-[--bg-glass] hover:text-[--text-primary]",
        outline:
          "bg-transparent text-[--text-primary] rounded-[10px] border border-[--border-default] hover:border-[--accent-primary] hover:text-[--text-accent]",
        destructive:
          "bg-destructive text-destructive-foreground rounded-[10px] hover:bg-destructive/90",
        danger:
          "bg-transparent text-[--accent-danger] rounded-[10px] border border-[rgba(239,68,68,0.25)] hover:bg-[--accent-danger-muted] hover:border-[rgba(239,68,68,0.5)]",
        link: "bg-transparent text-[--text-accent] h-auto p-0 rounded-none underline-offset-4 hover:underline hover:text-[--accent-glow]",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        default: "h-10 px-4 text-sm",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-base",
        xl: "h-14 px-8 text-base tracking-[-0.01em]",
        icon: "h-11 w-11 min-h-[44px] min-w-[44px] p-0 rounded-[10px]",
        "icon-sm": "h-9 w-9 min-h-[44px] min-w-[44px] p-0 rounded-[8px]",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      loading,
      icon,
      iconRight,
      children,
      disabled,
      asChild = false,
      type = "button",
      ...props
    },
    ref
  ) => {
    if (asChild) {
      return (
        <Slot className={cn(buttonVariants({ variant, size }), className)} ref={ref} {...props}>
          {children}
        </Slot>
      );
    }

    return (
      <button
        type={type}
        className={cn(buttonVariants({ variant, size }), className)}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <span
            className="h-3.5 w-3.5 rounded-full border-2 border-current border-t-transparent animate-spin shrink-0"
            aria-hidden
          />
        ) : (
          icon
        )}
        {children}
        {!loading && iconRight}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
