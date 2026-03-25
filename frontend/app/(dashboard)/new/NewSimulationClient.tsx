"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { SimulationWizard } from "@/components/wizard/SimulationWizard";
import { PageShell } from "@/components/layout/PageShell";
import { useWizardStore } from "@/store/wizardStore";

export function NewSimulationClient() {
  const params = useSearchParams();
  const setRawIdea = useWizardStore((s) => s.setRawIdea);

  useEffect(() => {
    const idea = params.get("idea");
    if (idea?.trim()) {
      setRawIdea(idea.trim());
    }
  }, [params, setRawIdea]);

  return (
    <PageShell title="New simulation" description="Describe any idea and our AI will set up and run a full simulation for you.">
      <SimulationWizard />
    </PageShell>
  );
}
