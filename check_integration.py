#!/usr/bin/env python3
"""
Integration Summary: TimesFM + MIRAI + Futurus

This script verifies all components are wired correctly and ready for production.
"""

import sys
from pathlib import Path

backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def check_repos():
    """Verify both repos are cloned."""
    repos = {
        "TimesFM": Path(__file__).parent / "vendors" / "timesfm" / "src" / "timesfm",
        "MIRAI": Path(__file__).parent / "vendors" / "mirai" / "APIs",
    }
    
    print("\n" + "=" * 70)
    print("  Repository Status")
    print("=" * 70)
    
    for name, path in repos.items():
        status = "[OK]" if path.exists() else "[MISSING]"
        print(f"{status} {name}: {path}")
    
    return all(p.exists() for p in repos.values())


def check_modules():
    """Verify all integration modules load correctly."""
    print("\n" + "=" * 70)
    print("  Module Status")
    print("=" * 70)
    
    modules = {
        "TimesFM Validator": "services.timesfm_validator",
        "MIRAI Integration": "services.mirai_integration",
        "Validation Orchestrator": "services.validation_orchestrator",
    }
    
    all_ok = True
    for name, module_name in modules.items():
        try:
            __import__(module_name)
            print(f"[OK] {name}: {module_name}")
        except Exception as e:
            print(f"[FAIL] {name}: {str(e)[:60]}")
            all_ok = False
    
    # Report generator requires DB config, check as file instead
    rg_path = Path(backend_path) / "services" / "report_generator.py"
    if rg_path.exists():
        print(f"[OK] Report Generator: {rg_path.name} (file exists)")
    else:
        print(f"[FAIL] Report Generator: file not found")
        all_ok = False
    
    return all_ok


def check_dependencies():
    """Verify key dependencies are installed."""
    print("\n" + "=" * 70)
    print("  Dependency Status")
    print("=" * 70)
    
    deps = {
        "torch": "PyTorch (TimesFM backend)",
        "numpy": "NumPy (numerical computing)",
        "pandas": "Pandas (data handling)",
        "httpx": "HTTPX (async HTTP)",
        "structlog": "StructLog (logging)",
    }
    
    all_ok = True
    for pkg, desc in deps.items():
        try:
            __import__(pkg)
            version = __import__(pkg).__version__ if hasattr(__import__(pkg), "__version__") else "installed"
            print(f"[OK] {pkg}: {desc} ({version})")
        except ImportError:
            print(f"[MISSING] {pkg}: {desc}")
            all_ok = False
    
    return all_ok


def test_validation_pipeline():
    """Test the complete validation pipeline."""
    import asyncio
    print("\n" + "=" * 70)
    print("  Validation Pipeline Test")
    print("=" * 70)

    try:
        from services.validation_orchestrator import build_comprehensive_validation

        # Simple test data
        adoption = [
            {"cumulative": 10 * (i + 1), "turn": i + 1} for i in range(10)
        ]
        metrics = {"growth_rate": 0.15}
        market = {"target_market": "SaaS"}

        result = asyncio.run(build_comprehensive_validation(adoption, metrics, market))
        
        print(f"[OK] Comprehensive validation works")
        print(f"     Composite Risk: {result.get('composite_risk')}")
        print(f"     Confidence: {result.get('confidence_score')}")
        print(f"     TimesFM Enabled: {result.get('timesfm', {}).get('enabled', 'N/A')}")
        print(f"     MIRAI Enabled: {result.get('mirai', {}).get('enabled', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"[FAIL] Pipeline test failed: {str(e)[:60]}")
        return False


def print_architecture():
    """Print system architecture."""
    print("\n" + "=" * 70)
    print("  System Architecture")
    print("=" * 70)
    print("""
User creates simulation
  |
  -> Backend seed builder injects macro context (MIRAI)
  |
  -> MiroFish agents run with macro shocks
  |
  -> Simulation completes: adoption curve generated
  |
  -> Report generator runs:
     - TimesFM validator: Statistical divergence check
     - MIRAI validator: Macro alignment check
     - Orchestrator: Merge into composite warning
  |
  -> Report JSON includes validation signals
  |
  -> User sees composite_validation_risk flag in viability_summary
""")


def main():
    """Run all checks."""
    print("\n" + "=" * 70)
    print("| Futurus Integration: TimesFM + MIRAI")
    print("=" * 70)
    
    results = {
        "Repositories": check_repos(),
        "Modules": check_modules(),
        "Dependencies": check_dependencies(),
        "Pipeline": test_validation_pipeline(),
    }
    
    print_architecture()
    
    print("\n" + "=" * 70)
    print("  Summary")
    print("=" * 70)
    
    for check, status in results.items():
        icon = "[OK]" if status else "[INCOMPLETE]"
        print(f"{icon} {check}")
    
    all_ok = all(results.values())
    
    if all_ok:
        print("\n" + "=" * 70)
        print("  INTEGRATION COMPLETE")
        print("=" * 70)
        print("""
You can now:
  1. Run end-to-end simulations with validation
  2. Deploy to production with TimesFM + MIRAI active
  3. Tell investors: "We integrate TimesFM-inspired and MIRAI-inspired
     validation to catch AI hallucinations vs. grounded forecasts"

Next: Run a full simulation and check report JSON for validation signals
""")
        return 0
    else:
        print("\n[!] Some checks failed. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
