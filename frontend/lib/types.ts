export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  plan_tier: string;
  credit_balance: number;
  simulations_this_month: number;
  daily_limit: number;
  billing_period_start: string;
  subscription_status: string;
  onboarding_completed: boolean;
  created_at: string;
}

export type SimulationStatus =
  | "queued"
  | "building_seed"
  | "generating_personas"
  | "running"
  | "generating_report"
  | "completed"
  | "failed"
  /** Reserved for APIs that surface stop/revoke as its own state; Futurus API uses failed + error_message today. */
  | "revoked";

export interface Persona {
  name: string;
  segment: string;
  personality: string[];
  budget_sensitivity: number;
  influence_score: number;
  decision_speed: string;
  main_motivation: string;
  main_objection: string;
  trigger_to_adopt: string;
  trigger_to_churn: string;
}

export interface Simulation {
  id: string;
  business_name: string;
  idea_description: string;
  target_market: string;
  pricing_model: string;
  price_points: Record<string, number>;
  gtm_channels: string[];
  competitors: Array<{ name: string; url?: string; description: string }>;
  key_assumptions: Array<{ variable: string; value: string }>;
  vertical: string;
  personas: Persona[];
  agent_count: number;
  max_turns: number;
  status: SimulationStatus;
  current_turn: number;
  agents_active: number;
  actual_cost_usd: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
  celery_task_id?: string | null;
  ensemble_runs?: number;
  estimated_cost_usd?: number;
  notify_on_complete?: boolean;
}

export interface SummaryMetrics {
  adoption_rate: number;
  churn_rate: number;
  viral_coefficient: number;
  total_adopters: number;
  total_churned: number;
  confidence_score: number;
}

export interface AdoptionPoint {
  turn: number;
  month_equivalent: number;
  adopters: number;
  churned: number;
  net: number;
  cumulative: number;
}

export interface PersonaResult {
  segment: string;
  adoption_rate: number;
  churn_rate: number;
  referrals_generated: number;
}

export interface FailureEvent {
  turn: number;
  month_equivalent: number;
  event: string;
  impact_level: "low" | "medium" | "high" | "critical";
  affected_segment: string;
}

export interface Risk {
  risk: string;
  probability: "low" | "medium" | "high";
  impact: "low" | "medium" | "high";
  mitigation: string;
}

export interface PivotSuggestion {
  pivot: string;
  rationale: string;
  confidence: "low" | "medium" | "high";
  evidence_from_simulation: string;
}

export interface KeyInsight {
  insight: string;
  supporting_evidence: string;
  actionability: string;
}

/** Plain-English hero verdict (from API or derived from metrics for older reports). */
export interface ViabilitySummary {
  verdict_label: string;
  headline: string;
  will_it_work: string;
  what_could_go_wrong: string;
  what_would_help: string;
}

export interface Citation {
  id: number;
  title: string;
  text: string;
  source: string;
  url: string;
  year?: number | null;
}

export interface Report {
  id: string;
  simulation_id: string;
  summary_metrics: SummaryMetrics;
  adoption_curve: AdoptionPoint[];
  persona_breakdown: PersonaResult[];
  failure_timeline: FailureEvent[];
  risk_matrix: Risk[];
  pivot_suggestions: PivotSuggestion[];
  key_insights: KeyInsight[];
  viability_summary?: ViabilitySummary | null;
  citations?: Citation[];
  share_token?: string;
  pdf_url?: string;
  created_at: string;
  /** Present on `GET /api/reports/share/{token}` */
  business_name?: string | null;
  idea_description?: string | null;
}

export interface GeneratedFields {
  business_name: string;
  idea_description: string;
  target_market: string;
  pricing_model: string;
  currency: string;
  price_points: Record<string, number>;
  gtm_channels: string[];
  competitors: Array<{ name: string; url: string; description: string }>;
  key_assumptions: Array<{ variable: string; value: string }>;
  vertical: string;
}

export interface FollowUpQA {
  question: string;
  answer: string;
}

export interface WizardState {
  phase: "idea" | "questions" | "review";
  raw_idea: string;
  follow_up_questions: string[];
  answers: FollowUpQA[];
  generated_fields: GeneratedFields | null;
  personas: Persona[];
}

export interface LiveEvent {
  id?: number;
  agent_name: string;
  segment: string;
  event_type: "adopted" | "churned" | "referred" | "rejected";
  description: string;
  turn?: number;
}

export interface WebSocketMessage {
  type: "progress" | "turn";
  message?: string;
  progress: number;
  turn?: number;
  agents_active?: number;
  max_turns?: number;
  agent_count?: number;
  events?: LiveEvent[];
  report_id?: string;
}
