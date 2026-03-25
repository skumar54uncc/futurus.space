import { Skeleton } from "@/components/ui/skeleton";

export default function SimulationLoading() {
  return (
    <div
      className="max-w-[680px] mx-auto px-6 py-10 space-y-6"
      aria-label="Loading simulation"
      aria-busy="true"
    >
      <Skeleton className="h-10 w-[55%]" />
      <Skeleton className="h-5 w-[30%]" />
      <div className="flex justify-center py-8">
        <Skeleton className="h-40 w-40 rounded-full" />
      </div>
      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-[16px]" />
        ))}
      </div>
      <Skeleton className="h-80 rounded-[16px]" />
    </div>
  );
}
