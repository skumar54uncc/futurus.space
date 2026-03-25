/** Normalize simulation id for keys and equality (API/axios may stringify UUIDs differently). */
export function simulationIdKey(id: unknown): string {
  if (typeof id === "string") return id.trim();
  return String(id ?? "").trim();
}
