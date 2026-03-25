import { cn } from "@/lib/utils";

interface PageShellProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  /** Wider layout for dense pages (e.g. Clerk settings). */
  wide?: boolean;
}

export function PageShell({ title, description, actions, children, wide }: PageShellProps) {
  return (
    <div className={cn("mx-auto py-8 px-4", wide ? "max-w-6xl" : "max-w-5xl")}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between mb-8">
        <div className="min-w-0">
          <h1 className="text-h2 font-medium text-[--text-primary] tracking-tight">{title}</h1>
          {description && <p className="text-[--text-tertiary] mt-1 text-sm leading-relaxed max-w-xl">{description}</p>}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
      {children}
    </div>
  );
}
