import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { WizardState, GeneratedFields, FollowUpQA, Persona } from "@/lib/types";

/** Baseline when AI has not yet filled `generated_fields` (manual step edits). */
export const EMPTY_GENERATED_FIELDS: GeneratedFields = {
  business_name: "",
  idea_description: "",
  target_market: "",
  pricing_model: "freemium",
  currency: "USD",
  price_points: { basic: 0 },
  gtm_channels: [],
  competitors: [],
  key_assumptions: [],
  vertical: "saas",
};

function mergeGeneratedFields(current: GeneratedFields | null): GeneratedFields {
  return { ...EMPTY_GENERATED_FIELDS, ...(current ?? {}) };
}

interface WizardStore extends WizardState {
  setPhase: (phase: WizardState["phase"]) => void;
  setRawIdea: (idea: string) => void;
  setFollowUpQuestions: (questions: string[]) => void;
  setAnswers: (answers: FollowUpQA[]) => void;
  setGeneratedFields: (fields: GeneratedFields) => void;
  /** Patch a single key; initializes `generated_fields` from defaults when null. */
  updateGeneratedField: <K extends keyof GeneratedFields>(key: K, value: GeneratedFields[K]) => void;
  /** Alias for step components — same as `updateGeneratedField`. */
  updateField: <K extends keyof GeneratedFields>(key: K, value: GeneratedFields[K]) => void;
  setPersonas: (personas: Persona[]) => void;
  reset: () => void;
}

const defaultState: WizardState = {
  phase: "idea",
  raw_idea: "",
  follow_up_questions: [],
  answers: [],
  generated_fields: null,
  personas: [],
};

export const useWizardStore = create<WizardStore>()(
  persist(
    (set, get) => ({
      ...defaultState,
      setPhase: (phase) => set({ phase }),
      setRawIdea: (raw_idea) => set({ raw_idea }),
      setFollowUpQuestions: (follow_up_questions) => set({ follow_up_questions }),
      setAnswers: (answers) => set({ answers }),
      setGeneratedFields: (fields) => set({ generated_fields: mergeGeneratedFields(fields) }),
      updateGeneratedField: (key, value) =>
        set((state) => ({
          generated_fields: { ...mergeGeneratedFields(state.generated_fields), [key]: value },
        })),
      updateField: (key, value) => get().updateGeneratedField(key, value),
      setPersonas: (personas) => set({ personas }),
      reset: () => set(defaultState),
    }),
    {
      // SECURITY: Session-only storage; do not persist business ideas or generated fields to disk
      name: "futurus-wizard-ui",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        phase: state.phase,
      }),
    }
  )
);
