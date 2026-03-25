import { SimulationCardSkeleton } from "@/components/ui/skeleton";

export default function DashboardLoading() {
  return (
    <div className="space-y-3 p-6" aria-label="Loading" aria-busy="true">
      {Array.from({ length: 3 }).map((_, i) => (
        <SimulationCardSkeleton key={i} />
      ))}
    </div>
  );
}
