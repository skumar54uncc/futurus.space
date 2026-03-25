import { useMemo } from "react";
import { useWizardStore, EMPTY_GENERATED_FIELDS } from "@/store/wizardStore";
import type { GeneratedFields } from "@/lib/types";

/**
 * Flattened `generated_fields` with safe defaults + stable `updateField` for wizard steps.
 */
export function useWizardGeneratedForm(): GeneratedFields & {
  updateField: <K extends keyof GeneratedFields>(key: K, value: GeneratedFields[K]) => void;
} {
  const generated_fields = useWizardStore((s) => s.generated_fields);
  const updateField = useWizardStore((s) => s.updateField);

  return useMemo(
    () => ({
      ...EMPTY_GENERATED_FIELDS,
      ...(generated_fields ?? {}),
      updateField,
    }),
    [generated_fields, updateField]
  );
}
