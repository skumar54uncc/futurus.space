import type { ReactNode } from "react";
import { type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: { label: string; onClick: () => void; icon?: ReactNode };
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      role="status"
      className={`flex flex-col items-center justify-center py-20 px-6 text-center ${className ?? ""}`}
    >
      <div
        className="w-14 h-14 rounded-[14px] flex items-center justify-center mb-5"
        style={{
          background: "var(--accent-primary-muted)",
          border: "1px solid var(--border-accent)",
        }}
        aria-hidden="true"
      >
        <Icon size={22} className="text-[--text-accent]" />
      </div>
      <h3 className="text-base font-medium text-[--text-primary] mb-2">{title}</h3>
      <p className="text-sm text-[--text-secondary] max-w-[280px] leading-relaxed mb-6">{description}</p>
      {action && (
        <Button variant="primary" size="md" onClick={action.onClick} icon={action.icon}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
