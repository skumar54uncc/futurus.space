"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

interface ToastProps {
  message: string;
  type?: "success" | "error" | "info";
  className?: string;
}

export function Toast({ message, type = "info", className }: ToastProps) {
  const colors = {
    success: "bg-green-50 text-green-800 border-green-200",
    error: "bg-red-50 text-red-800 border-red-200",
    info: "bg-blue-50 text-blue-800 border-blue-200",
  };

  return (
    <div className={cn("rounded-lg border px-4 py-3 text-sm", colors[type], className)}>
      {message}
    </div>
  );
}
