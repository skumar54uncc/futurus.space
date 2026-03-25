import { Suspense } from "react";
import { NewSimulationClient } from "./NewSimulationClient";

export default function NewSimulationPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-2xl mx-auto py-12 px-4 text-slate-500 text-sm">Loading&hellip;</div>
      }
    >
      <NewSimulationClient />
    </Suspense>
  );
}
