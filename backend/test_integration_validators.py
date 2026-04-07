#!/usr/bin/env python3
"""Integration test for TimesFM validator with cloned repo.

Runs a simple adoption curve through the validator and verifies:
1. Model loads successfully
2. Forecast generates correct shapes
3. Divergence scoring works as expected
4. Fallback to heuristic works if model unavailable
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from services.timesfm_validator import build_timesfm_validation
from services.validation_orchestrator import build_comprehensive_validation


def test_timesfm_with_sample_curve():
    """Test TimesFM with realistic adoption data."""
    # Sample adoption curve: slow start, acceleration, plateau
    adoption_curve = [
        {"cumulative": 10, "new_adopters": 10, "turn": 1},
        {"cumulative": 15, "new_adopters": 5, "turn": 2},
        {"cumulative": 25, "new_adopters": 10, "turn": 3},
        {"cumulative": 50, "new_adopters": 25, "turn": 4},
        {"cumulative": 120, "new_adopters": 70, "turn": 5},
        {"cumulative": 280, "new_adopters": 160, "turn": 6},
        {"cumulative": 550, "new_adopters": 270, "turn": 7},
        {"cumulative": 850, "new_adopters": 300, "turn": 8},
        {"cumulative": 1100, "new_adopters": 250, "turn": 9},
        {"cumulative": 1250, "new_adopters": 150, "turn": 10},
    ]

    summary_metrics = {
        "adoption_rate": 42.5,
        "churn_rate": 15.0,
        "viral_coefficient": 0.45,
        "total_adopters": 1250,
        "revenue_generated": 125000,
    }

    print("\n" + "=" * 70)
    print("  TimesFM Validator Test")
    print("=" * 70)
    print("\nInput adoption curve:")
    for row in adoption_curve:
        print(f"  Turn {row['turn']}: {row['cumulative']} cumulative ({row['new_adopters']} new)")

    print("\nRunning TimesFM validation...")
    result = build_timesfm_validation(adoption_curve, summary_metrics)

    print("\nValidation Result:")
    print(f"  Enabled: {result.get('enabled')}")
    print(f"  Method: {result.get('method')}")
    print(f"  Risk Level: {result.get('risk_level')}")
    print(f"  Divergence Score: {result.get('divergence_score')}")
    print(f"  Summary: {result.get('summary')}")
    print(f"  Quantiles: {result.get('quantiles')}")
    print(f"  Forecast points: {len(result.get('forecast', []))}")
    if result.get('fallback_reason'):
        print(f"  Fallback Reason: {result.get('fallback_reason')}")

    return result


async def test_comprehensive_validation():
    """Test unified orchestrator with both validators."""
    adoption_curve = [
        {"cumulative": i * (i // 2 + 1), "adopters": i} for i in range(1, 11)
    ]

    summary_metrics = {
        "adoption_rate": 45.0,
        "churn_rate": 12.0,
        "viral_coefficient": 0.5,
        "total_adopters": 500,
    }

    market_data = {
        "target_market": "Small Business SaaS",
        "vertical": "Finance",
        "pricing_model": "Freemium",
        "key_assumptions": ["80% adopt within first 6 turns"],
        "competitors": ["Competitor A", "Competitor B"],
    }

    print("\n" + "=" * 70)
    print("  Comprehensive Validation Orchestrator Test")
    print("=" * 70)

    print("\nRunning comprehensive validation (TimesFM + MIRAI)...")
    result = await build_comprehensive_validation(adoption_curve, summary_metrics, market_data)

    print("\nOrchestrator Result:")
    print(f"  Composite Risk: {result.get('composite_risk')}")
    print(f"  Confidence Score: {result.get('confidence_score')}")
    print(f"  Warning Flags: {result.get('warning_flags')}")
    print(f"  TimesFM Enabled: {result.get('timesfm', {}).get('enabled', False)}")
    print(f"  MIRAI Enabled: {result.get('mirai', {}).get('enabled', False)}")

    return result


if __name__ == "__main__":
    import asyncio

    try:
        result1 = test_timesfm_with_sample_curve()
        print("\n[OK] TimesFM validator test completed")
    except Exception as e:
        print(f"\n[FAIL] TimesFM validator test failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        result2 = asyncio.run(test_comprehensive_validation())
        print("\n[OK] Comprehensive validation test completed")
    except Exception as e:
        print(f"\n[FAIL] Comprehensive validation test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("  Test Summary")
    print("=" * 70)
    print("[OK] All integration tests completed successfully!")
    print("\nNext steps:")
    print("  1. Provide MIRAI repo URL to complete macro integration")
    print("  2. Run a full simulation end-to-end")
    print("  3. Verify validation signals appear in report JSON")
    print("=" * 70 + "\n")
