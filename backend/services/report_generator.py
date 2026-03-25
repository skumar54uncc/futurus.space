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
from openai import AsyncOpenAI
from core.config import settings
from models.simulation import Simulation, SimulationEvent, Report
from sqlalchemy.ext.asyncio import AsyncSession

client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


async def generate_report(
    simulation: Simulation, events: list[SimulationEvent], db: AsyncSession
) -> Report:
    metrics = _compute_metrics(events, simulation)
    qualitative = await _run_report_agent(simulation, metrics, events)

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
    simulation: Simulation, metrics: dict, events: list
) -> dict:
    sampled_events = events[:50]
    events_text = "\n".join([
        f"Turn {e.turn} | {e.agent_segment} | {e.event_type}: {e.event_description}"
        for e in sampled_events
    ])

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

Key events (sample):
{events_text}

Analyze this and return ONLY valid JSON with these fields:

{{
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
- Reference REAL industry statistics and benchmarks where possible (e.g., "average coffee shop failure rate is 60% in first year")
- Compare simulation results to real-world norms (e.g., "your 28% churn is above the industry average of 15-20%")
- Use the actual customer segment names from the simulation, not generic terms
- Be brutally honest about risks — don't sugarcoat
"""
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model_tier1,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "failure_timeline": [],
            "risk_matrix": [{"risk": "Analysis unavailable", "probability": "medium", "impact": "medium", "mitigation": "Retry report generation"}],
            "pivot_suggestions": [],
            "key_insights": [{"insight": "Report generation encountered an error", "supporting_evidence": "N/A", "actionability": "Re-run the simulation"}],
        }
