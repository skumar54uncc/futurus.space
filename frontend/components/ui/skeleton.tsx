import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("skeleton", className)} aria-hidden="true" {...props} />;
}

export function SimulationCardSkeleton() {
  return (
    <div
      className="bg-[--bg-surface] border border-[--border-subtle] rounded-[16px] p-5 space-y-3"
      aria-hidden="true"
    >
      <div className="flex items-start justify-between">
        <Skeleton className="h-5 rounded-md w-[58%]" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <Skeleton className="h-3.5 rounded w-[38%]" />
      <div className="flex gap-2 pt-1">
        <Skeleton className="h-9 w-28 rounded-[10px]" />
        <Skeleton className="h-9 w-9 rounded-[10px]" />
      </div>
    </div>
  );
}

export function ReportMetricsSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3" aria-hidden="true">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="bg-[--bg-surface] border border-[--border-subtle] rounded-[16px] p-5">
          <Skeleton className="h-3 rounded mb-3 w-1/2" />
          <Skeleton className="h-8 rounded w-[65%]" />
        </div>
      ))}
    </div>
  );
}

export function ReportChartSkeleton() {
  return <Skeleton className="h-[280px] w-full" />;
}

export function ReportSkeleton() {
  return (
    <div className="space-y-6 animate-fade-in" aria-label="Loading report..." aria-busy="true">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="space-y-2 w-1/2 min-w-[200px]">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-4 w-[70%]" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-10 w-32 rounded-[10px]" />
          <Skeleton className="h-10 w-36 rounded-[10px]" />
        </div>
      </div>
      <ReportMetricsSkeleton />
      <ReportChartSkeleton />
      <Skeleton className="h-48" />
      <Skeleton className="h-56" />
    </div>
  );
}

export { Skeleton };
