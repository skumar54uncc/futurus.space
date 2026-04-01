import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user
from api.middleware.rate_limiter import LIMITS, limiter
from core.config import settings
from core.database import get_db
from models.simulation import Report, Simulation
from models.user import User
from schemas.report import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])

client = AsyncOpenAI(
    api_key=settings.openai_compatible_llm_key(),
    base_url=settings.openai_compatible_llm_base(),
)


@router.post("/{simulation_id}", response_model=ChatResponse)
@limiter.limit(LIMITS["chat"])
async def chat_with_report(
    request: Request,
    simulation_id: uuid.UUID,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sim_result = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.user_id == current_user.id,
        )
    )
    sim = sim_result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    report_result = await db.execute(
        select(Report).where(Report.simulation_id == simulation_id)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not ready yet")

    system_prompt = f"""You are an expert business analyst and market research consultant. You just completed an in-depth market simulation for a business idea.

You have COMPLETE knowledge of:
1. The original business idea and all its details
2. The full simulation results with real customer behavior data
3. General market knowledge and industry trends
4. The specific location and demographics of the target market

=== BUSINESS DETAILS ===
Business Name: {sim.business_name}
Idea: {sim.idea_description}
Target Market: {sim.target_market}
Location/Context: {sim.target_market}
Pricing Model: {sim.pricing_model}
Price Points: {json.dumps(sim.price_points)}
Go-to-Market Channels: {json.dumps(sim.gtm_channels)}
Competitors: {json.dumps(sim.competitors)}
Key Assumptions: {json.dumps(sim.key_assumptions)}
Industry Vertical: {sim.vertical}

=== SIMULATION RESULTS ===
Summary Metrics: {json.dumps(report.summary_metrics)}
Customer Segment Breakdown: {json.dumps(report.persona_breakdown)}
Key Insights: {json.dumps(report.key_insights)}
Risk Assessment: {json.dumps(report.risk_matrix)}
Pivot Suggestions: {json.dumps(report.pivot_suggestions)}
Failure Points: {json.dumps(report.failure_timeline)}

=== YOUR GUIDELINES ===
- Answer ANY question about this business, the market, the simulation, strategy, or the idea itself
- When the user asks about specific customer groups (like "students" or "families"), relate it to the simulation's customer segments
- Use actual numbers and percentages from the simulation data
- If the user asks about real-world comparisons, draw on your general knowledge of similar businesses
- If you reference statistics or market data, mention the source or note it's a general industry estimate
- Be honest about what the simulation can and cannot tell us
- Give actionable, specific advice — not generic business platitudes
- Keep responses conversational and easy to understand; avoid jargon and walls of symbols
- You may use Markdown for structure (short headings, **bold** for emphasis, bullet lists). Keep sections brief and scannable
- You can discuss: marketing strategy, pricing, location, competition, customer behavior, growth, risks, hiring, funding, operations, or anything else"""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in body.history[-10:]:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": body.message})

    response = await client.chat.completions.create(
        model=settings.llm_model_tier1,
        messages=messages,
        max_tokens=1500,
        temperature=0.4,
    )

    msg = response.choices[0].message
    text = getattr(msg, "content", None)
    if isinstance(text, str) and text.strip():
        return ChatResponse(response=text.strip())
    raise HTTPException(
        status_code=502,
        detail="The AI returned an empty reply. Try again in a few seconds.",
    )
