import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { SimulationStatus as Status } from "@/lib/types";

const STATUS_CONFIG: Record<Status, { label: string; variant: BadgeVariant }> = {
  queued: { label: "Queued", variant: "secondary" },
  building_seed: { label: "Building context", variant: "warning" },
  generating_personas: { label: "Creating agents", variant: "warning" },
  running: { label: "Running", variant: "default" },
  generating_report: { label: "Generating report", variant: "warning" },
  completed: { label: "Completed", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
  revoked: { label: "Stopped", variant: "secondary" },
};

export function SimulationStatusBadge({ status }: { status: Status }) {
  const config = STATUS_CONFIG[status] ?? { label: status, variant: "secondary" as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
