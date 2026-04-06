import type { GeneratedFields } from "@/lib/types";
import {
  DEFAULT_LAUNCH_AGENT_COUNT,
  DEFAULT_LAUNCH_TURN_COUNT,
} from "@/lib/simulationLimits";

const DEFAULT_ASSUMPTIONS: GeneratedFields["key_assumptions"] = [
  { variable: "churn_rate_monthly", value: "5%" },
  { variable: "word_of_mouth_rate", value: "10%" },
  { variable: "trial_to_paid_conversion", value: "15%" },
];

function coercePriceValue(v: unknown): number {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  const s = String(v)
    .replace(/,/g, "")
    .replace(/[$€£₹¥]/g, "")
    .trim();
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : 0;
}

/** Normalize API / persisted wizard data so UI and launch payload stay consistent. */
export function normalizeGeneratedFieldsFromApi(raw: Record<string, unknown>): GeneratedFields {
  const competitorsRaw = raw.competitors;
  const competitors: GeneratedFields["competitors"] = [];
  if (Array.isArray(competitorsRaw)) {
    for (const c of competitorsRaw) {
      if (typeof c === "string" && c.trim()) {
        competitors.push({ name: c.trim(), url: "", description: "" });
      } else if (c && typeof c === "object" && c !== null && "name" in c) {
        const o = c as Record<string, unknown>;
        competitors.push({
          name: String(o.name ?? "").trim(),
          url: String(o.url ?? ""),
          description: String(o.description ?? ""),
        });
      }
    }
  }

  const assumptionsRaw = raw.key_assumptions;
  let key_assumptions: GeneratedFields["key_assumptions"] = [];
  if (Array.isArray(assumptionsRaw)) {
    for (const a of assumptionsRaw) {
      if (a && typeof a === "object" && a !== null) {
        const o = a as Record<string, unknown>;
        key_assumptions.push({
          variable: String(o.variable ?? ""),
          value: o.value == null ? "" : String(o.value),
        });
      }
    }
  }
  if (key_assumptions.length === 0) key_assumptions = [...DEFAULT_ASSUMPTIONS];

  const price_points: Record<string, number> = {};
  const pp = raw.price_points;
  if (pp && typeof pp === "object" && !Array.isArray(pp)) {
    for (const [k, v] of Object.entries(pp as Record<string, unknown>)) {
      const key = k.trim() || "tier";
      price_points[key] = coercePriceValue(v);
    }
  }
  if (Object.keys(price_points).length === 0) {
    price_points.basic = 0;
  }

  let gtm_channels: string[] = [];
  const gtm = raw.gtm_channels;
  if (Array.isArray(gtm)) {
    gtm_channels = gtm.filter((x): x is string => typeof x === "string").map((s) => s.trim()).filter(Boolean);
  }
  if (gtm_channels.length === 0) gtm_channels = ["social_media"];

  return {
    business_name: String(raw.business_name ?? "").trim(),
    idea_description: String(raw.idea_description ?? "").trim(),
    target_market: String(raw.target_market ?? "").trim(),
    pricing_model: String(raw.pricing_model ?? "freemium"),
    currency: String(raw.currency ?? "$"),
    price_points,
    gtm_channels,
    competitors,
    key_assumptions,
    vertical: String(raw.vertical ?? "saas"),
  };
}

export function competitorDisplayName(c: GeneratedFields["competitors"][number] | string): string {
  if (typeof c === "string") return c;
  return c?.name ?? "";
}

/** Body for POST /api/simulations/ — only schema fields, no currency or LLM extras. */
export function buildSimulationCreatePayload(
  fields: GeneratedFields,
  scale?: { agent_count: number; max_turns: number }
) {
  return {
    business_name: fields.business_name.trim(),
    idea_description: fields.idea_description.trim(),
    target_market: fields.target_market.trim(),
    pricing_model: fields.pricing_model.trim(),
    price_points: Object.fromEntries(
      Object.entries(fields.price_points).map(([k, v]) => [k, typeof v === "number" ? v : coercePriceValue(v)])
    ),
    gtm_channels: fields.gtm_channels.map((s) => s.trim()).filter(Boolean),
    competitors: fields.competitors.map((c) => {
      const row = c as { name: string; url?: string; description?: string } | string;
      if (typeof row === "string") {
        return { name: row.trim(), url: "", description: "" };
      }
      return {
        name: (row.name ?? "").trim(),
        url: row.url ?? "",
        description: row.description ?? "",
      };
    }),
    key_assumptions: fields.key_assumptions.map((a) => ({
      variable: String(a.variable ?? ""),
      value: a.value == null ? "" : String(a.value),
    })),
    vertical: fields.vertical.trim(),
    personas: [],
    agent_count: scale?.agent_count ?? DEFAULT_LAUNCH_AGENT_COUNT,
    max_turns: scale?.max_turns ?? DEFAULT_LAUNCH_TURN_COUNT,
  };
}

export function validateLaunchFields(fields: GeneratedFields): string | null {
  if (fields.idea_description.trim().length < 10) {
    return "Idea description must be at least 10 characters. Add a bit more detail or edit the review card.";
  }
  if (fields.target_market.trim().length < 10) {
    return "Target audience must be at least 10 characters.";
  }
  if (!fields.business_name.trim()) {
    return "Please add a business name.";
  }
  if (Object.keys(fields.price_points).length === 0) {
    return "Add at least one pricing tier.";
  }
  if (!fields.gtm_channels.length) {
    return "Add at least one go-to-market channel.";
  }
  return null;
}

export { formatSimulationLaunchError, parseSimulationLaunchError } from "./apiErrors";
