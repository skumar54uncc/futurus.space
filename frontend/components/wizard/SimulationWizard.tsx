"use client";
import { useWizardStore } from "@/store/wizardStore";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { OPEN_ACCESS_AGENT_CAP, OPEN_ACCESS_TURN_CAP } from "@/lib/simulationLimits";
import { FreeTierLimitsNotice } from "@/components/landing/FreeTierLimitsNotice";
import {
  buildSimulationCreatePayload,
  competitorDisplayName,
  formatSimulationLaunchError,
  normalizeGeneratedFieldsFromApi,
  validateLaunchFields,
} from "@/lib/wizardPayload";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import toast from "react-hot-toast";
import { Sparkles, ArrowRight, Loader2, Rocket, Pencil, Check } from "lucide-react";

function PhaseIdea() {
  const { raw_idea, setRawIdea } = useWizardStore();

  return (
    <div className="space-y-6">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-primary/10 mb-2">
          <Sparkles className="h-7 w-7 text-primary" />
        </div>
        <h2 className="text-2xl font-semibold">What&apos;s your idea?</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          Describe any idea in your own words. No business jargon needed &mdash;
          our AI will figure out the rest.
        </p>
      </div>
      <Textarea
        value={raw_idea}
        onChange={(e) => setRawIdea(e.target.value)}
        placeholder="e.g. An app that helps people split grocery bills with roommates, maybe with a subscription for families..."
        rows={5}
        className="text-base"
        spellCheck={false}
      />
      <p className="text-xs text-muted-foreground text-center">
        The more detail you give, the better the simulation. But even a single sentence works!
      </p>
    </div>
  );
}

function PhaseQuestions() {
  const { follow_up_questions, answers, setAnswers } = useWizardStore();

  const handleAnswerChange = (index: number, value: string) => {
    const updated = [...answers];
    updated[index] = { question: follow_up_questions[index], answer: value };
    setAnswers(updated);
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-3">
        <h2 className="text-2xl font-semibold">A few quick questions</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          Help our AI understand your idea better. Answer in your own words &mdash; there are no wrong answers.
        </p>
      </div>
      <div className="space-y-5">
        {follow_up_questions.map((q, i) => (
          <div key={i} className="space-y-2">
            <label className="text-sm font-medium">{q}</label>
            <Input
              value={answers[i]?.answer || ""}
              onChange={(e) => handleAnswerChange(i, e.target.value)}
              placeholder="Type your answer here..."
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function EditableList({ label, items, onUpdate }: { label: string; items: string[]; onUpdate: (items: string[]) => void }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(items.join(", "));

  const save = () => {
    onUpdate(draft.split(",").map((s) => s.trim()).filter(Boolean));
    setEditing(false);
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
            {editing ? (
              <div className="mt-1.5 flex gap-2">
                <Input value={draft} onChange={(e) => setDraft(e.target.value)} className="text-sm" placeholder="Comma-separated values" />
                <Button size="sm" variant="ghost" onClick={save} aria-label="Save list">
                  <Check className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2 mt-1.5">
                {items.map((item, i) => (
                  <Badge key={i} variant="secondary">{item.replace(/_/g, " ")}</Badge>
                ))}
              </div>
            )}
          </div>
          {!editing && (
            <Button size="sm" variant="ghost" onClick={() => { setDraft(items.join(", ")); setEditing(true); }} className="shrink-0">
              <Pencil className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function PhaseReview() {
  const { generated_fields, updateGeneratedField } = useWizardStore();
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editingPricing, setEditingPricing] = useState(false);
  const [priceDraft, setPriceDraft] = useState("");

  if (!generated_fields) return null;

  const currency = generated_fields.currency || "$";

  const fields = [
    { key: "business_name" as const, label: "Business Name", type: "text" },
    { key: "idea_description" as const, label: "What it does", type: "textarea" },
    { key: "vertical" as const, label: "Category", type: "text" },
    { key: "target_market" as const, label: "Target Audience", type: "textarea" },
    { key: "pricing_model" as const, label: "Pricing Model", type: "text" },
  ];

  const savePricing = () => {
    try {
      const pairs = priceDraft.split(",").map((s) => s.trim());
      const newPoints: Record<string, number> = {};
      for (const pair of pairs) {
        const [name, val] = pair.split(":").map((s) => s.trim());
        if (name && val) newPoints[name] = parseFloat(val) || 0;
      }
      if (Object.keys(newPoints).length > 0) updateGeneratedField("price_points", newPoints);
    } catch { /* ignore parse errors */ }
    setEditingPricing(false);
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-3">
        <h2 className="text-2xl font-semibold">Here&apos;s what we got</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          Review what our AI filled in. Click the pencil to edit anything, then launch your simulation.
        </p>
      </div>

      <div className="space-y-3">
        {fields.map(({ key, label, type }) => (
          <Card key={key}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
                  {editingField === key ? (
                    <div className="mt-1 flex gap-2">
                      {type === "textarea" ? (
                        <Textarea
                          value={generated_fields[key] as string}
                          onChange={(e) => updateGeneratedField(key, e.target.value)}
                          rows={2}
                          className="text-sm"
                        />
                      ) : (
                        <Input
                          value={generated_fields[key] as string}
                          onChange={(e) => updateGeneratedField(key, e.target.value)}
                          className="text-sm"
                        />
                      )}
                      <Button size="sm" variant="ghost" onClick={() => setEditingField(null)} aria-label="Done editing">
                        <Check className="h-4 w-4" />
                      </Button>
                    </div>
                  ) : (
                    <p className="text-sm mt-0.5">{generated_fields[key] as string}</p>
                  )}
                </div>
                {editingField !== key && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setEditingField(key)}
                    className="shrink-0"
                    aria-label={`Edit ${label}`}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}

        <Card>
          <CardContent className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Pricing Tiers</p>
                {editingPricing ? (
                  <div className="mt-1.5 flex gap-2">
                    <Input value={priceDraft} onChange={(e) => setPriceDraft(e.target.value)} className="text-sm" placeholder="e.g. basic: 150, premium: 300" />
                    <Button size="sm" variant="ghost" onClick={savePricing} aria-label="Save pricing">
                      <Check className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2 mt-1.5">
                    {Object.entries(generated_fields.price_points).map(([tier, price]) => (
                      <Badge key={tier} variant="secondary">
                        {tier}: {currency}{price}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              {!editingPricing && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setPriceDraft(
                      Object.entries(generated_fields.price_points)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(", ")
                    );
                    setEditingPricing(true);
                  }}
                  className="shrink-0"
                  aria-label="Edit pricing tiers"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <EditableList
          label="Go-to-Market Channels"
          items={generated_fields.gtm_channels}
          onUpdate={(items) => updateGeneratedField("gtm_channels", items)}
        />

        <EditableList
          label="Competitors"
          items={generated_fields.competitors.map((c) => competitorDisplayName(c))}
          onUpdate={(items) => updateGeneratedField("competitors", items.map((name) => ({ name, url: "", description: "" })))}
        />
      </div>

      <div className="space-y-4">
        <div className="rounded-xl border border-[--border-accent] bg-[--accent-primary-muted] px-4 py-4 text-center text-sm text-[--text-primary]">
          Ready to launch! We&apos;ll run up to {OPEN_ACCESS_AGENT_CAP.toLocaleString()} AI customer agents across{" "}
          {OPEN_ACCESS_TURN_CAP} simulation turns (capped for cost and speed).
        </div>
        <FreeTierLimitsNotice variant="dark" />
      </div>
    </div>
  );
}

const TOAST_ID_ANALYZE = "wizard-analyze";
const TOAST_ID_REFINE = "wizard-refine";
const TOAST_ID_LAUNCH = "wizard-launch";

export function SimulationWizard() {
  const store = useWizardStore();
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const requestLock = useRef(false);

  const handleAnalyze = async () => {
    if (requestLock.current || loading) return;
    if (!store.raw_idea || store.raw_idea.trim().length < 10) {
      toast.error("Please describe your idea in at least 10 characters.", { id: `${TOAST_ID_ANALYZE}-validation` });
      return;
    }
    requestLock.current = true;
    setLoading(true);
    try {
      const { data } = await api.post(
        "/api/simulations/analyze-idea",
        { raw_idea: store.raw_idea },
        { timeout: 120_000 }
      );

      const { confidence, follow_up_questions, ...raw } = data;

      if (confidence === "low" && follow_up_questions?.length > 0) {
        store.setFollowUpQuestions(follow_up_questions);
        store.setAnswers(follow_up_questions.map((q: string) => ({ question: q, answer: "" })));
        store.setPhase("questions");
      } else {
        store.setGeneratedFields(normalizeGeneratedFieldsFromApi(raw as Record<string, unknown>));
        store.setPhase("review");
      }
    } catch {
      toast.error("Failed to analyze your idea. Please try again.", { id: TOAST_ID_ANALYZE });
    } finally {
      setLoading(false);
      requestLock.current = false;
    }
  };

  const handleRefine = async () => {
    if (requestLock.current || loading) return;
    const unanswered = store.answers.some((a) => !a.answer.trim());
    if (unanswered) {
      toast.error("Please answer all the questions before continuing.", { id: `${TOAST_ID_REFINE}-validation` });
      return;
    }
    requestLock.current = true;
    setLoading(true);
    try {
      const { data } = await api.post(
        "/api/simulations/refine-idea",
        { raw_idea: store.raw_idea, answers: store.answers },
        { timeout: 120_000 }
      );
      store.setGeneratedFields(normalizeGeneratedFieldsFromApi(data as Record<string, unknown>));
      store.setPhase("review");
    } catch {
      toast.error("Failed to process your answers. Please try again.", { id: TOAST_ID_REFINE });
    } finally {
      setLoading(false);
      requestLock.current = false;
    }
  };

  const handleLaunch = async () => {
    if (requestLock.current || loading) return;
    if (!store.generated_fields) return;
    const preflight = validateLaunchFields(store.generated_fields);
    if (preflight) {
      toast.error(preflight, { id: `${TOAST_ID_LAUNCH}-preflight` });
      return;
    }
    requestLock.current = true;
    setLoading(true);
    try {
      const payload = buildSimulationCreatePayload(store.generated_fields);
      const { data } = await api.post("/api/simulations/", payload);
      router.push(`/simulation/${data.id}`);
      // Reset after navigation starts so the phase change doesn't flash the idea screen
      setTimeout(() => store.reset(), 500);
    } catch (err: unknown) {
      toast.error(formatSimulationLaunchError(err), { id: TOAST_ID_LAUNCH });
    } finally {
      setLoading(false);
      requestLock.current = false;
    }
  };

  const phaseIndicators = [
    { label: "Describe", active: store.phase === "idea" },
    { label: "Clarify", active: store.phase === "questions" },
    { label: "Review", active: store.phase === "review" },
  ];
  const activeIndex = phaseIndicators.findIndex((p) => p.active);

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-center gap-2 mb-8">
        {phaseIndicators.map((p, i) => (
          <div key={p.label} className="flex items-center gap-2">
            <div
              className={`flex items-center justify-center w-8 h-8 rounded-full text-xs font-medium transition-colors ${
                i <= activeIndex
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {i + 1}
            </div>
            <span className={`text-sm ${i <= activeIndex ? "font-medium" : "text-muted-foreground"}`}>
              {p.label}
            </span>
            {i < phaseIndicators.length - 1 && (
              <div className={`w-12 h-px ${i < activeIndex ? "bg-primary" : "bg-muted"}`} />
            )}
          </div>
        ))}
      </div>

      {store.phase === "idea" && <PhaseIdea />}
      {store.phase === "questions" && <PhaseQuestions />}
      {store.phase === "review" && <PhaseReview />}

      <div
        className={`flex mt-8 gap-3 items-center ${store.phase === "idea" ? "justify-end" : "justify-between flex-wrap"}`}
      >
        {store.phase !== "idea" && (
          <Button
            variant="outline"
            onClick={() => {
              if (store.phase === "questions") store.setPhase("idea");
              if (store.phase === "review") {
                if (store.follow_up_questions.length > 0) store.setPhase("questions");
                else store.setPhase("idea");
              }
            }}
          >
            Back
          </Button>
        )}

        {store.phase === "idea" && (
          <Button onClick={handleAnalyze} disabled={loading || !store.raw_idea.trim()}>
            {loading ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Analyzing...</>
            ) : (
              <>Analyze my idea <ArrowRight className="ml-2 h-4 w-4" /></>
            )}
          </Button>
        )}

        {store.phase === "questions" && (
          <Button onClick={handleRefine} disabled={loading}>
            {loading ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Processing...</>
            ) : (
              <>Continue <ArrowRight className="ml-2 h-4 w-4" /></>
            )}
          </Button>
        )}

        {store.phase === "review" && (
          <Button
            onClick={handleLaunch}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            {loading ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Launching...</>
            ) : (
              <><Rocket className="mr-2 h-4 w-4" /> Launch simulation</>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}
