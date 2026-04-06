# Production Deployment Checklist: TimesFM + MIRAI

## Pre-Deployment Verification

- [x] TimesFM repo cloned to `vendors/timesfm/`
- [x] MIRAI repo cloned to `vendors/mirai/`
- [x] All dependencies added to `requirements.txt`
- [x] Validator modules created and error-checked
- [x] Report generator updated
- [x] Integration tests passing
- [x] Fallback heuristics implemented

## Deployment Tasks

### 1. Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Verify PyTorch installation
python -c "import torch; print(f'PyTorch {torch.__version__} ready')"

# Verify TimesFM accessibility
python -c "from services.timesfm_validator import build_timesfm_validation; print('TimesFM accessible')"
```

### 2. Cache Directories
```bash
# Ensure cache directories are writable
mkdir -p backend/static

# Set permissions (if needed)
chmod 755 backend/static

# Optional: Pre-warm cache
python -c "from services.mirai_integration import build_mirai_macro_context; build_mirai_macro_context()"
```

### 3. Celery Beat Scheduling
```bash
# Verify beat is in docker-compose.yml
docker-compose ps beat

# Expected: Service should start with no errors
# Check logs: docker-compose logs beat

# Beat schedule (crontab):
# - refresh-daily-mirai-lite-context: 3 AM UTC daily
```

### 4. Environment Variables (Optional)
```bash
# For live Tavily macro data (MIRAI-lite):
export TAVILY_API_KEY="your_key"

# For HuggingFace model downloads:
export HF_HOME="${HOME}/.cache/huggingface"

# For AWS SES email (validation reset notifications):
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
```

### 5. Database & Migrations
```bash
# Ensure reports table has new JSON columns:
# viability_summary still uses same JSON schema
# (backwards compatible)

# No new migrations needed
# Existing columns accept validation data
```

### 6. Monitoring & Logging
```bash
# Set up alerts for these log patterns:
# - "timesfm_model_load_failed" (fallback triggered)
# - "mirai_repo_not_found" (MIRAI unavailable)
# - "celery_task_failed" (beat schedule issue)

# Example in your logging pipeline:
# Alert if 10+ errors in 1 hour
```

## Testing Checklist

### Unit Tests
```bash
# TimesFM validator
python -c "from backend.services.timesfm_validator import build_timesfm_validation; print('OK')"

# MIRAI integration
python -c "from backend.services.mirai_integration import build_mirai_macro_context; print('OK')"

# Orchestrator
python -c "from backend.services.validation_orchestrator import build_comprehensive_validation; print('OK')"
```

### Integration Test
```bash
cd backend
python test_integration_validators.py
# Expected: [OK] All integration tests completed successfully!
```

### End-to-End Simulation Test
```bash
# 1. Start backend:
uvicorn main:app --reload

# 2. Create a test simulation (via API)
POST /api/simulations
{
  "business_name": "Test Idea",
  "idea_description": "Test validation",
  "target_market": "B2B SaaS",
  "vertical": "Technology",
  ...
}

# 3. Wait for completion
GET /api/simulations/{id}

# 4. Check report includes validation:
GET /api/simulations/{id}/report
# Look for: viability_summary.statistical_validation
#           viability_summary.macro_validation
#           viability_summary.composite_validation_risk
```

## Performance Targets

| Metric | Target | Typical | Notes |
|---|---|---|---|
| **TimesFM First Load** | <40s | 15-30s | Model download + compile |
| **TimesFM Cached** | <1s | <500ms | Memory cache hit |
| **MIRAI Context** | <2s | <1s | JSON cache |
| **Report Generation** | <60s total | 20-40s | Includes all validations |
| **User Perception** | Non-blocking | Async | Validation runs async |

## Rollout Strategy

### Phase 1: Shadow Mode (Week 1)
- Deploy validators but don't surface in UI
- Log all validation results to analytics
- Monitor for errors/latency issues
- **User impact**: None

### Phase 2: Backend Integration (Week 2)
- Validators active in report generation
- Include warnings in report JSON
- **User impact**: Validation data available via API

### Phase 3: Frontend Display (Week 3)
- Show `composite_validation_risk` badge in report
- Add tooltips explaining warnings
- Link to validation details
- **User impact**: Visible warnings in UI

### Phase 4: Full Launch (Week 4)
- Feature complete
- Monitor adoption & feedback
- Iterate on UX based on usage

## Rollback Plan

If issues arise:

1. **Model Load Failures** → Automatic heuristic fallback (no user impact)
2. **Cache Issues** → Validators skip, reports still generate
3. **Beat Schedule Failures** → Macro context uses last valid cache
4. **API Errors** → Graceful degradation, warning flags omitted

**Manual rollback** (if needed):
```bash
# Disable validators (keep structure but return default):
# 1. Set environment variable:
export DISABLE_VALIDATORS=1

# 2. Or comment out in report_generator.py:
# validation = build_comprehensive_validation(...)
# validation = {"timesfm": {}, "mirai": {}, "composite_risk": "low"}
```

## Production Runbook

### Daily Checks
```bash
# Check beat ran macro refresh:
tail -100 logs/celery-beat.log | grep "mirai_macro_context"

# Check model cache exists:
ls -la backend/static/mirai_macro_signals.json

# Check validation errors:
tail -50 logs/app.log | grep -i "validation_failed"
```

### Weekly Reviews
- Analyze validation signal distribution (should see some "high" risk flags)
- Check model performance (divergence scores reasonable?)
- Review user reports with flags vs. actual outcomes

### Monthly Maintenance
- Clear old cache files (>30 days)
- Update MIRAI data if available
- Review and tune event→shock mappings
- Analyze divergence score calibration

## Capacity Planning

### Storage
- TimesFM model weights: ~925 MB (one-time download, cached)
- MIRAI cache: <1 MB (daily, 24h TTL)
- Reports with validation: +2-5 KB per report (JSON overhead)

### Compute
- TimesFM inference: 10-30s per report (CPU or GPU)
- MIRAI analysis: <1s per report (cache-based)
- Beat scheduler: <100ms per day (no resources)

### Network
- TimesFM model download: ~3-5 MB (first run only, cached)
- Tavily API calls: Optional, ~0.5 KB per call

## Security Considerations

- [x] No credentials embedded in code (use env vars)
- [x] HuggingFace token optional (uses public access by default)
- [x] Cache files read/write permissions verified
- [x] No data exfiltration (validation stays local)
- [x] Third-party repos verified (Google Research & UCLA)

## Compliance Notes

- ✅ TimesFM: Apache 2.0 license (compatible with most commercial use)
- ✅ MIRAI: Research code (check repo for specific license)
- ✅ Dependencies: MIT, Apache, BSD-compatible
- ⚠️ Recommendation: Have legal review vendor licensing before major launch

## Success Metrics

### Technical KPIs
- Validator availability: >99.5%
- Average report generation time: <45s
- Model cache hit rate: >80%
- Zero critical errors post-deployment

### User KPIs
- Reports with validation signals: 100%
- User awareness of risk flags: Measure via surveys
- Simulation shelving due to flags: Monitor trends
- User trust in forecasts: NPS survey

## Support & Troubleshooting

### Common Issues

**Q: Report takes 40+ seconds**
- Expected if first run of day (model load)
- Subsequent reports should be <5s
- Check if CPU constrained

**Q: Validation flags never appear**
- Check if validators enabled: `grep DISABLE_VALIDATORS .env`
- Verify Celery beat running: `docker-compose logs beat`
- Check logs for errors: `tail -100 logs/app.log`

**Q: HuggingFace download fails**
- Check internet connectivity
- Verify HF_HOME directory exists and is writable
- Try manual download: `huggingface-cli download google/timesfm-2.5-200m-pytorch`

### Getting Help
1. Check `INTEGRATION_GUIDE.md` for detailed docs
2. Review logs with pattern: `timesfm_*`, `mirai_*`, `validation_*`
3. Run `python check_integration.py` for diagnostics
4. Contact: [Your support process]

---

## Sign-Off

- [ ] DevOps: Infrastructure ready (beat scheduler, cache dirs)
- [ ] QA: Integration tests passing
- [ ] Security: License review complete
- [ ] Product: UI/UX ready for Phase 2
- [ ] Leadership: Approved for launch

**Deployment Date**: _____________  
**Prepared By**: _____________  
**Reviewed By**: _____________  

