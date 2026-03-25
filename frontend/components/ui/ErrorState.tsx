import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  compact?: boolean;
}

export function ErrorState({
  title = "Something went wrong",
  message = "An unexpected error occurred. Please try again.",
  onRetry,
  compact = false,
}: ErrorStateProps) {
  if (compact) {
    return (
      <div
        role="alert"
        className="flex items-center gap-3 p-3 rounded-[10px] bg-[--accent-danger-muted] border border-[rgba(239,68,68,0.20)]"
      >
        <AlertTriangle size={15} className="text-[--accent-danger] shrink-0" aria-hidden />
        <p className="text-sm text-[--text-secondary] flex-1">{message}</p>
        {onRetry && (
          <Button variant="ghost" size="icon-sm" onClick={onRetry} aria-label="Retry">
            <RefreshCw size={13} />
          </Button>
        )}
      </div>
    );
  }

  return (
    <div role="alert" className="flex flex-col items-center justify-center py-16 text-center">
      <div
        className="w-12 h-12 rounded-full bg-[--accent-danger-muted] flex items-center justify-center mb-4"
        aria-hidden
      >
        <AlertTriangle size={20} className="text-[--accent-danger]" />
      </div>
      <h3 className="text-base font-medium text-[--text-primary] mb-2">{title}</h3>
      <p className="text-sm text-[--text-secondary] max-w-[300px] mb-6">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="md" onClick={onRetry} icon={<RefreshCw size={14} />}>
          Try again
        </Button>
      )}
    </div>
  );
}
