"""
After simulation completes, this service:
1. Queries the simulation state from MiroFish
2. Runs a tool-using ReportAgent against the simulation world
3. Builds the structured Report object
4. Generates ensemble confidence intervals if multiple runs
"""
import json
import secrets
import statistics
import uuid
from collections import Counter

import structlog
from models.simulation import Simulation, SimulationEvent, Report
from sqlalchemy.ext.asyncio import AsyncSession
from services.llm_router import call_llm
from services.llm_text_json import coerce_llm_json_text
from services.web_search import fetch_industry_citations
from services.validation_orchestrator import build_comprehensive_validation

logger = structlog.get_logger()


def _heuristic_viability_summary(summary: dict) -> dict:
    """Fallback plain-English verdict from aggregate metrics (no LLM)."""
    ar = float(summary.get("adoption_rate", 0) or 0)
    cr = float(summary.get("churn_rate", 0) or 0)
    viral = float(summary.get("viral_coefficient", 0) or 0)
    adopters = int(summary.get("total_adopters", 0) or 0)

    if cr >= 60 and ar < 40:
        label = "struggling"
        headline = "As modeled, this idea would likely struggle to keep customers."
        will = (
            f"The simulation ended with about {ar:.0f}% adoption but very high churn relative to adopters "
            f"({cr:.0f}% churn rate). That pattern usually means retention or product–market fit needs work before scaling."
        )
        wrong = (
            "Word-of-mouth may not save the day if people try the product and leave quickly. "
            "Pricing, trust, logistics, or the core promise may be misaligned with what simulated customers expected."
        )
        help_ = (
            "Tighten the offer for one segment first, improve onboarding and support, and validate willingness to pay "
            "with real interviews. Consider the pivot ideas below."
        )
    elif ar >= 45 and cr <= 40 and viral >= 0.35:
        label = "promising"
        headline = "There are encouraging signals — but execution still decides the outcome."
        will = (
            f"Roughly {ar:.0f}% adoption with moderate churn ({cr:.0f}%) and referral activity (viral coefficient {viral:.2f}) "
            "suggests some people see value. That is not a guarantee in the real market, but it is a better baseline than a dead launch."
        )
        wrong = (
            "Scaling too fast, underpricing, or weak operations could still burn trust. "
            "Competitors and macro conditions are not fully captured in this sandbox."
        )
        help_ = (
            "Double down on the segments that adopted most, measure real churn reasons, and keep unit economics honest as you grow."
        )
    else:
        label = "mixed"
        headline = "Results are mixed — worth refining before you bet big."
        will = (
            f"About {ar:.0f}% of agents adopted and churn ran around {cr:.0f}% (relative to adoption events). "
            f"Roughly {adopters} adopters in the run. The simulation is not a crystal ball, but it is not a clean ‘green light’ either."
        )
        wrong = (
            "You may be attracting interest without durable retention, or winning some segments while losing others. "
            "Misread demand or weak differentiation often shows up as this kind of split result."
        )
        help_ = (
            "Clarify the primary customer, run a cheaper real-world test (landing + waitlist or pilot), and address the highest risks in the matrix below."
        )

    return {
        "verdict_label": label,
        "headline": headline,
        "will_it_work": will,
        "what_could_go_wrong": wrong,
        "what_would_help": help_,
    }


def _merge_viability_summary(llm_part: object, summary: dict) -> dict:
    base = _heuristic_viability_summary(summary)
    if not isinstance(llm_part, dict):
        return base
    for key in ("verdict_label", "headline", "will_it_work", "what_could_go_wrong", "what_would_help"):
        val = llm_part.get(key)
        if isinstance(val, str) and val.strip():
            base[key] = val.strip()
    return base


async def generate_report(
    simulation: Simulation, events: list[SimulationEvent], db: AsyncSession
) -> Report:
    metrics = _compute_metrics(events, simulation)
    
    # Build market context for validators
    market_data = {
        "target_market": simulation.target_market,
        "vertical": simulation.vertical,
        "pricing_model": simulation.pricing_model,
        "key_assumptions": simulation.key_assumptions,
        "competitors": simulation.competitors,
    }
    
    # Run unified validation (TimesFM + MIRAI when available)
    validation = await build_comprehensive_validation(
        metrics["adoption_curve"],
        metrics["summary"],
        market_data
    )
    
    citations = await fetch_industry_citations(simulation, simulation_mode=True)
    qualitative = await _run_report_agent(simulation, metrics, validation, events, citations)
    viability = _merge_viability_summary(qualitative.get("viability_summary"), metrics["summary"])
    
    # Store comprehensive validation results
    viability["statistical_validation"] = validation.get("timesfm", {})
    viability["macro_validation"] = validation.get("mirai", {})
    viability["macro_context"] = validation.get("macro_context", {})
    viability["forecast_cache"] = validation.get("forecast_cache", {})
    viability["composite_validation_risk"] = validation.get("composite_risk", "low")
    
    # Add composite warnings to viability summary
    if validation.get("warning_flags"):
        existing_risks = viability.get("what_could_go_wrong", "")
        new_warnings = "; ".join(validation["warning_flags"])
        viability["what_could_go_wrong"] = (
            f"{existing_risks} Statistical/macro validation flagged: {new_warnings}."
        ).strip()

    report = Report(
        id=uuid.uuid4(),
        simulation_id=simulation.id,
        summary_metrics=metrics["summary"],
        adoption_curve=metrics["adoption_curve"],
        persona_breakdown=metrics["persona_breakdown"],
        failure_timeline=qualitative.get("failure_timeline", []),
        risk_matrix=qualitative.get("risk_matrix", []),
        pivot_suggestions=qualitative.get("pivot_suggestions", []),
        key_insights=qualitative.get("key_insights", []),
        viability_summary=viability,
        citations=citations,
        share_token=secrets.token_urlsafe(24),
    )

    db.add(report)
    await db.commit()
    return report


def _safe_stdev(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def _compute_internal_confidence_score(
    simulation: Simulation,
    persona_breakdown: list,
    adoption_curve: list,
    adoption_event_count: int,
) -> int:
    """
    Internal consistency of this single run (not real-world forecast accuracy).

    Uses persona-weighted segment adoption/churn (see _compute_metrics), so segments
    can disagree meaningfully — otherwise scores clustered ~85–90.

    Signals:
    - Cross-segment agreement on adoption % and churn %
    - Smooth cumulative adoption (big backward steps → lower)
    - Turn-to-turn stability of net new adopters
    - Enough adoption events vs. agent count
    """
    rates = [float(p.get("adoption_rate", 0)) for p in persona_breakdown]
    churns = [float(p.get("churn_rate", 0)) for p in persona_breakdown]

    if len(rates) >= 2:
        spread_a = _safe_stdev(rates)
        spread_c = _safe_stdev(churns)
        # Adoption spread: typical 0–80+ pts across segments; churn often 0–120+
        norm_a = min(1.0, spread_a / 28.0)
        norm_c = min(1.0, spread_c / 45.0)
        disagreement = (norm_a + norm_c) / 2.0
        seg_component = max(0.0, 1.0 - disagreement)
    else:
        seg_component = 0.55

    nets = [float(r.get("net", 0)) for r in adoption_curve]
    if len(nets) >= 4:
        mean_abs = statistics.mean(abs(n) for n in nets) + 1e-6
        std_n = statistics.stdev(nets)
        cv = std_n / mean_abs
        turn_component = max(0.0, 1.0 - min(1.0, cv / 2.85))
    elif len(nets) >= 2:
        turn_component = 0.52
    else:
        turn_component = 0.45

    denom = max(40.0, float(simulation.agent_count) * 0.1)
    depth_component = min(1.0, float(adoption_event_count) / denom)

    cumulative = [float(r.get("cumulative", 0)) for r in adoption_curve]
    if len(cumulative) >= 3:
        drops = sum(
            1
            for i in range(1, len(cumulative))
            if cumulative[i] < cumulative[i - 1] - 1e-6
        )
        mono_component = max(0.0, 1.0 - min(1.0, drops / max(1, len(cumulative) - 1)))
    else:
        mono_component = 0.5

    blended = (
        0.34 * seg_component
        + 0.28 * turn_component
        + 0.18 * depth_component
        + 0.20 * mono_component
    )
    # Wider, more responsive mapping (still capped; avoids "everything is 87")
    score = int(round(34 + blended * 58))
    return max(38, min(96, score))


def _compute_metrics(events: list, simulation: Simulation) -> dict:
    total_agents = simulation.agent_count
    adoption_events = [e for e in events if e.event_type == "adopted"]
    churn_events = [e for e in events if e.event_type == "churned"]
    referral_events = [e for e in events if e.event_type == "referred"]

    by_turn: dict[int, dict] = {}
    for e in events:
        t = e.turn
        if t not in by_turn:
            by_turn[t] = {"adopted": 0, "churned": 0, "referred": 0, "rejected": 0}
        by_turn[t][e.event_type] = by_turn[t].get(e.event_type, 0) + 1

    adoption_curve = []
    cumulative = 0
    for turn in sorted(by_turn.keys()):
        adopted = by_turn[turn].get("adopted", 0)
        churned = by_turn[turn].get("churned", 0)
        cumulative = cumulative + adopted - churned
        adoption_curve.append({
            "turn": turn,
            "month_equivalent": round(turn / 4, 1),
            "adopters": adopted,
            "churned": churned,
            "net": adopted - churned,
            "cumulative": max(0, cumulative),
        })

    final_adopters = max(0, cumulative)
    adoption_rate = round((final_adopters / total_agents) * 100, 1) if total_agents > 0 else 0
    churn_rate = round((len(churn_events) / max(1, len(adoption_events))) * 100, 1)
    viral_coefficient = round(len(referral_events) / max(1, len(adoption_events)), 2)

    segments: dict[str, dict] = {}
    for e in events:
        seg = e.agent_segment
        if seg not in segments:
            segments[seg] = {"adopted": 0, "churned": 0, "referred": 0, "rejected": 0}
        segments[seg][e.event_type] = segments[seg].get(e.event_type, 0) + 1

    # Agents per segment from stored personas (correct denominator for adoption %).
    pop_by_segment = Counter(
        str(p.get("segment") or p.get("segment_name") or "unknown")
        for p in (simulation.personas or [])
        if isinstance(p, dict)
    )
    if sum(pop_by_segment.values()) == 0 and segments and total_agents > 0:
        seg_list = sorted(segments.keys())
        n = len(seg_list)
        base = total_agents // n
        rem = total_agents - base * n
        for i, seg in enumerate(seg_list):
            pop_by_segment[seg] = base + (1 if i < rem else 0)

    persona_breakdown = []
    for seg, counts in segments.items():
        seg_adopted = counts.get("adopted", 0)
        seg_churned = counts.get("churned", 0)
        pop = int(pop_by_segment.get(seg, 0))
        if pop < 1:
            # Fallback when personas lack segment keys: at least everyone who produced events.
            pop = max(1, seg_adopted + seg_churned)
        adoption_pct = min(100.0, (seg_adopted / float(pop)) * 100.0)
        churn_pct = min(100.0, (seg_churned / max(1, seg_adopted)) * 100.0) if seg_adopted else 0.0
        persona_breakdown.append({
            "segment": seg,
            "adoption_rate": round(adoption_pct, 1),
            "churn_rate": round(churn_pct, 1),
            "referrals_generated": counts.get("referred", 0),
        })

    confidence_score = _compute_internal_confidence_score(
        simulation=simulation,
        persona_breakdown=persona_breakdown,
        adoption_curve=adoption_curve,
        adoption_event_count=len(adoption_events),
    )

    return {
        "summary": {
            "adoption_rate": adoption_rate,
            "churn_rate": churn_rate,
            "viral_coefficient": viral_coefficient,
            "total_adopters": final_adopters,
            "total_churned": len(churn_events),
            "simulation_turns": simulation.max_turns,
            "agent_count": total_agents,
            "confidence_score": confidence_score,
        },
        "adoption_curve": adoption_curve,
        "persona_breakdown": persona_breakdown,
    }


async def _run_report_agent(
    simulation: Simulation, metrics: dict, validation: dict, events: list, citations: list
) -> dict:
    sampled_events = events[:50]
    events_text = "\n".join([
        f"Turn {e.turn} | {e.agent_segment} | {e.event_type}: {e.event_description}"
        for e in sampled_events
    ])

    # Build verified sources block from Tavily results
    if citations:
        source_lines = ["=== VERIFIED INDUSTRY SOURCES ===",
                        "Ground your factual claims in these real sources. Reference them as [1], [2], etc.",
                        ""]
        for c in citations:
            year_str = f" ({c['year']})" if c.get("year") else ""
            source_lines.append(f"[{c['id']}] {c['source']}{year_str}: {c['text']}")
            source_lines.append(f"    URL: {c['url']}")
            source_lines.append("")
        citations_block = "\n".join(source_lines)
        citation_instruction = (
            "- Reference the verified sources above using [1], [2], etc. where relevant\n"
            "- Do NOT invent statistics not present in the provided sources or simulation data"
        )
    else:
        citations_block = ""
        citation_instruction = (
            "- Reference real industry statistics where you are confident in the data\n"
            "- Clearly distinguish simulation findings from general industry knowledge"
        )

    prompt = f"""You are an expert market analyst creating a real-world feasibility report based on a customer simulation.
Your analysis should blend simulation data with real-world market knowledge.

=== BUSINESS ===
Name: {simulation.business_name}
Idea: {simulation.idea_description}
Target Market: {simulation.target_market}
Pricing: {simulation.pricing_model} — {json.dumps(simulation.price_points)}
GTM channels: {", ".join(simulation.gtm_channels)}
Competitors: {json.dumps(simulation.competitors)}

=== SIMULATION DATA ===
Metrics: {json.dumps(metrics["summary"], indent=2)}
Customer Segments: {json.dumps(metrics["persona_breakdown"], indent=2)}
TimesFM Validation: {json.dumps(validation, indent=2)}

Key events (sample):
{events_text}

{citations_block}
Analyze this and return ONLY valid JSON with these fields:

{{
  "viability_summary": {{
    "verdict_label": "struggling|mixed|promising",
    "headline": "<one short punchy line — will this idea work as simulated?>",
    "will_it_work": "<3-5 sentences in plain English: yes / no / maybe and WHY, citing adoption %, churn %, and referrals from the metrics>",
    "what_could_go_wrong": "<3-5 sentences: concrete failure modes tied to the simulation and real markets>",
    "what_would_help": "<3-5 sentences: practical improvements, not generic advice>"
  }},
  "failure_timeline": [
    {{"turn": <int>, "month_equivalent": <float>, "event": "<describe what happened and WHY in real-world terms>", "impact_level": "low|medium|high|critical", "affected_segment": "<segment name>"}},
    ...at least 4 failure points...
  ],
  "risk_matrix": [
    {{"risk": "<real-world risk name>", "probability": "low|medium|high", "impact": "low|medium|high", "mitigation": "<specific, actionable step>"}},
    ...at least 5 risks, grounded in real industry data...
  ],
  "pivot_suggestions": [
    {{"pivot": "<specific pivot>", "rationale": "<why, with real-world examples of similar pivots>", "confidence": "low|medium|high", "evidence_from_simulation": "<specific data from the sim>"}},
    ...3-5 pivots...
  ],
  "key_insights": [
    {{"insight": "<specific insight>", "supporting_evidence": "<data from simulation AND real-world comparison if available>", "actionability": "<exactly what to do>"}},
    ...5-7 insights, include at least 1 that references real industry statistics...
  ]
}}

IMPORTANT:
- viability_summary must be readable by a non-expert founder — no jargon, no markdown asterisks
{citation_instruction}
- Compare simulation results to real-world norms (e.g., "your 28% churn is above the industry average of 15-20%")
- If TimesFM Validation shows a medium/high divergence, explicitly explain that the agents are optimistic but the statistical trajectory is flatter or riskier.
- Use the actual customer segment names from the simulation, not generic terms
- Be brutally honest about risks — don't sugarcoat
"""
    try:
        content = await call_llm(
            messages=[{"role": "user", "content": prompt}],
            agent_tier=1,
            max_tokens=4000,
            temperature=0.2,
            json_mode=True,
            read_timeout=75.0,
            max_provider_attempts=4,
        )
        coerced = coerce_llm_json_text(content)
        return json.loads(coerced)
    except Exception as exc:
        logger.exception(
            "report_agent_qualitative_failed",
            simulation_id=str(simulation.id),
            error=str(exc),
        )
        return {
            "viability_summary": {
                "verdict_label": "unclear",
                "headline": "We could not finish the written analysis for this run.",
                "will_it_work": (
                    "The numbers below still reflect your simulation. The AI step that writes the narrative did not complete — "
                    "often a temporary API or quota issue."
                ),
                "what_could_go_wrong": "Without the full narrative, rely on the metrics and charts, or run a new simulation.",
                "what_would_help": "Try again later or ensure backup LLM keys (e.g. Groq) are configured on the server.",
            },
            "failure_timeline": [],
            "risk_matrix": [{"risk": "Analysis unavailable", "probability": "medium", "impact": "medium", "mitigation": "Retry report generation"}],
            "pivot_suggestions": [],
            "key_insights": [{"insight": "Report generation encountered an error", "supporting_evidence": "N/A", "actionability": "Re-run the simulation"}],
        }
