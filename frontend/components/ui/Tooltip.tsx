"use client";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

interface TooltipProps {
  children: ReactNode;
  content: ReactNode;
  side?: "top" | "right" | "bottom" | "left";
  delayDuration?: number;
}

export function Tooltip({ children, content, side = "top", delayDuration = 300 }: TooltipProps) {
  return (
    <TooltipPrimitive.Provider delayDuration={delayDuration}>
      <TooltipPrimitive.Root>
        <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content
            side={side}
            sideOffset={6}
            className="z-50 max-w-[220px] px-2.5 py-1.5 text-xs font-medium text-[--text-primary] bg-[--bg-elevated] border border-[--border-default] rounded-[6px] shadow-xl animate-fade-in select-none"
          >
            {content}
            <TooltipPrimitive.Arrow className="fill-[--bg-elevated]" />
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  );
}
