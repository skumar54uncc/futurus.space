"""
Compute category-wise agent voting scores from simulation report data.

Categories:
  - Market Demand: derived from adoption_rate and total_adopters
  - Retention: derived from churn_rate (inverse — lower churn = higher score)
  - Virality: derived from viral_coefficient
  - Feasibility: derived from confidence_score

Each score is 0–100. The overall rating is the weighted average.
"""


def compute_idea_scores(summary_metrics: dict) -> dict:
    adoption_rate = summary_metrics.get("adoption_rate", 0)
    churn_rate = summary_metrics.get("churn_rate", 0)
    viral_coefficient = summary_metrics.get("viral_coefficient", 0)
    confidence_score = summary_metrics.get("confidence_score", 0)

    # Reports store adoption/churn as percentages (0-100) and confidence as score (0-100),
    # but some legacy rows may still have fractions (0-1). Normalize both shapes.
    adoption_pct = adoption_rate * 100 if adoption_rate <= 1 else adoption_rate
    churn_pct = churn_rate * 100 if churn_rate <= 1 else churn_rate
    confidence_pct = confidence_score * 100 if confidence_score <= 1 else confidence_score

    # Market demand directly tracks final adoption percentage.
    market_demand = min(100.0, round(adoption_pct, 1))

    # Retention is inverse churn (percentage form). Lower churn -> higher retention.
    retention = min(100.0, round(max(0.0, 100.0 - min(churn_pct, 100.0)), 1))

    # Virality: viral_coefficient typically 0–3+. Map to 0–100 (1.0 = viral threshold ≈ 50)
    virality = min(100.0, round(min(viral_coefficient / 2.0, 1.0) * 100, 1))

    # Feasibility mirrors confidence score percentage.
    feasibility = min(100.0, round(confidence_pct, 1))

    # Overall rating: weighted average
    weights = {
        "market_demand": 0.30,
        "retention": 0.25,
        "virality": 0.20,
        "feasibility": 0.25,
    }
    overall = round(
        market_demand * weights["market_demand"]
        + retention * weights["retention"]
        + virality * weights["virality"]
        + feasibility * weights["feasibility"],
        1,
    )

    return {
        "market_demand": market_demand,
        "retention": retention,
        "virality": virality,
        "feasibility": feasibility,
        "overall": overall,
        "breakdown": {
            "market_demand": {
                "score": market_demand,
                "weight": weights["market_demand"],
                "source": f"adoption_rate={adoption_pct:.1f}%",
            },
            "retention": {
                "score": retention,
                "weight": weights["retention"],
                "source": f"churn_rate={churn_pct:.1f}%",
            },
            "virality": {
                "score": virality,
                "weight": weights["virality"],
                "source": f"viral_coefficient={viral_coefficient:.2f}",
            },
            "feasibility": {
                "score": feasibility,
                "weight": weights["feasibility"],
                "source": f"confidence_score={confidence_pct:.1f}%",
            },
        },
    }


# Map simulation vertical to a display-friendly category name
VERTICAL_CATEGORY_MAP = {
    "saas": "SaaS",
    "consumer_app": "Consumer App",
    "marketplace": "Marketplace",
    "physical_product": "Physical Product",
    "service_business": "Service Business",
    "enterprise": "Enterprise",
}


def vertical_to_category(vertical: str) -> str:
    return VERTICAL_CATEGORY_MAP.get(vertical, vertical.replace("_", " ").title())
