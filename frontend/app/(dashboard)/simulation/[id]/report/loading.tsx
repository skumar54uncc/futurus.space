import { ReportSkeleton } from "@/components/ui/skeleton";

export default function ReportLoading() {
  return (
    <div className="max-w-[900px] mx-auto px-6 py-10">
      <ReportSkeleton />
    </div>
  );
}
