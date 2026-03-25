"""PDF export for reports: WeasyPrint when available, xhtml2pdf fallback (Windows-friendly)."""
import uuid
from io import BytesIO
from pathlib import Path
from typing import Literal

from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.simulation import Report, Simulation
import structlog

logger = structlog.get_logger()

REPORTS_DIR = Path(__file__).resolve().parent.parent / "static" / "reports"

REPORT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    /* Note: no @page rules here — xhtml2pdf (Windows fallback) does not support them. */
    * { box-sizing: border-box; }
    body {
      font-family: Helvetica, Arial, sans-serif;
      padding: 0;
      margin: 0;
      color: #1a1a1a;
      font-size: 13px;
      line-height: 1.45;
      position: relative;
    }
    .watermark {
      position: fixed;
      top: 35%;
      left: 50%;
      width: 100%;
      margin-left: -50%;
      text-align: center;
      transform: rotate(-32deg);
      font-size: 72px;
      font-weight: 800;
      color: #6366f1;
      opacity: 0.06;
      z-index: 0;
      pointer-events: none;
      letter-spacing: 0.2em;
    }
    .content { position: relative; z-index: 1; }
    .brand-banner {
      background: linear-gradient(135deg, #312e81 0%, #4f46e5 45%, #6366f1 100%);
      color: #fff;
      padding: 20px 24px;
      margin: -8px -8px 28px -8px;
      border-radius: 0 0 12px 12px;
    }
    .brand-banner .wordmark {
      font-size: 22px;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    .brand-banner .tagline {
      font-size: 11px;
      opacity: 0.92;
      margin-top: 6px;
      letter-spacing: 0.04em;
    }
    .doc-title { font-size: 22px; margin: 0 0 8px 0; }
    .idea { color: #555; margin-bottom: 20px; font-size: 13px; }
    h2 {
      font-size: 16px;
      color: #312e81;
      margin-top: 28px;
      border-bottom: 2px solid #e0e7ff;
      padding-bottom: 8px;
    }
    .metric-row { margin-top: 8px; }
    .metric {
      display: inline-block;
      margin: 6px 12px 6px 0;
      padding: 10px 16px;
      background: #f5f5ff;
      border: 1px solid #e0e7ff;
      border-radius: 8px;
      vertical-align: top;
    }
    .metric .value { font-size: 24px; font-weight: 600; color: #312e81; }
    .metric .label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }
    th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid #eee; }
    th { font-size: 10px; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; }
    .risk-high { color: #dc2626; font-weight: 600; }
    .risk-medium { color: #f59e0b; }
    .risk-low { color: #16a34a; }
    .card {
      margin-bottom: 12px;
      padding: 14px;
      background: #f8fafc;
      border-radius: 8px;
      border: 1px solid #e2e8f0;
    }
    .card-title { font-weight: 600; font-size: 14px; }
    .card-sub { font-size: 12px; color: #64748b; margin-top: 4px; }
    .card-action { font-size: 12px; color: #4f46e5; margin-top: 4px; }
    .disclaimer {
      margin-top: 36px;
      padding: 14px;
      background: #fffbeb;
      border: 1px solid #fcd34d;
      border-radius: 8px;
      font-size: 11px;
      color: #92400e;
    }
    .brand-footer {
      margin-top: 28px;
      padding: 14px 16px;
      background: #1e1b4b;
      color: #e0e7ff;
      border-radius: 8px;
      font-size: 10px;
    }
    .brand-footer strong { color: #fff; }
  </style>
</head>
<body>
  <div class="watermark">FUTURUS</div>
  <div class="content">
    <div class="brand-banner">
      <div class="wordmark">Futurus</div>
      <div class="tagline">AI-powered market simulation report · Proprietary output</div>
    </div>
    <h1 class="doc-title">{{ business_name }} — Simulation Report</h1>
    <p class="idea">{{ idea_description }}</p>

    <h2>Key Metrics</h2>
    <div class="metric-row">
      <div class="metric"><div class="value">{{ metrics.adoption_rate|default('—') }}%</div><div class="label">Adoption Rate</div></div>
      <div class="metric"><div class="value">{{ metrics.churn_rate|default('—') }}%</div><div class="label">Churn Rate</div></div>
      <div class="metric"><div class="value">{{ metrics.total_adopters|default('—') }}</div><div class="label">Total Adopters</div></div>
      <div class="metric"><div class="value">{{ metrics.viral_coefficient|default('—') }}</div><div class="label">Viral Coefficient</div></div>
      <div class="metric"><div class="value">{{ metrics.confidence_score|default('—') }}%</div><div class="label">Confidence Score</div></div>
    </div>

    <h2>Customer Segment Analysis</h2>
    <table>
      <tr><th>Segment</th><th>Adoption</th><th>Churn</th><th>Referrals</th></tr>
      {% for p in personas %}
      <tr>
        <td><strong>{{ p.segment|default('—') }}</strong></td>
        <td>{{ p.adoption_rate|default('—') }}%</td>
        <td>{{ p.churn_rate|default('—') }}%</td>
        <td>{{ p.referrals_generated|default('—') }}</td>
      </tr>
      {% endfor %}
    </table>

    <h2>Risk Assessment</h2>
    <table>
      <tr><th>Risk</th><th>Probability</th><th>Impact</th><th>Mitigation</th></tr>
      {% for risk in risks %}
      <tr>
        <td>{{ risk.risk|default('—') }}</td>
        <td class="risk-{{ risk.probability|default('low') }}">{{ risk.probability|default('—') }}</td>
        <td class="risk-{{ risk.impact|default('low') }}">{{ risk.impact|default('—') }}</td>
        <td>{{ risk.mitigation|default('—') }}</td>
      </tr>
      {% endfor %}
    </table>

    <h2>Key Insights</h2>
    {% for insight in insights %}
    <div class="card">
      <div class="card-title">{{ insight.insight|default('—') }}</div>
      <div class="card-sub">{{ insight.supporting_evidence|default('') }}</div>
      <div class="card-action">Action: {{ insight.actionability|default('—') }}</div>
    </div>
    {% endfor %}

    <h2>Pivot Suggestions</h2>
    {% for pivot in pivots %}
    <div class="card">
      <div class="card-title">{{ pivot.pivot|default('—') }}</div>
      <div class="card-sub">{{ pivot.rationale|default('') }}</div>
      <div class="card-sub">Evidence: {{ pivot.evidence_from_simulation|default('—') }}</div>
      <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Confidence: {{ pivot.confidence|default('—') }}</div>
    </div>
    {% endfor %}

    <div class="disclaimer">
      <strong>About this report:</strong> This simulation uses AI agents to model potential customer behavior.
      Results are directional estimates, not guarantees. The confidence score ({{ metrics.confidence_score|default('—') }}%)
      reflects internal simulation consistency, not real-world prediction accuracy.
      Use these insights to inform your decisions alongside real customer research.
    </div>

    <div class="brand-footer">
      <strong>Futurus</strong> — Startup fate simulator. This document was generated by Futurus and is intended
      for the account holder. Redistribution or removal of Futurus branding is not permitted without permission.
      <br /><br />
      Report ID: {{ simulation_id }} · © Futurus
    </div>
  </div>
</body>
</html>
"""


def _html_to_pdf_weasyprint(html: str) -> bytes | None:
    try:
        from weasyprint import HTML

        return HTML(string=html).write_pdf()
    except Exception as e:
        logger.warning("weasyprint_pdf_failed", error=str(e))
        return None


def _html_to_pdf_xhtml2pdf(html: str) -> bytes | None:
    """Pure-Python HTML→PDF; works on Windows without GTK (WeasyPrint system deps)."""
    try:
        from xhtml2pdf import pisa
    except ImportError:
        logger.warning("xhtml2pdf_not_installed")
        return None

    buf = BytesIO()
    try:
        result = pisa.CreatePDF(src=html, dest=buf, encoding="utf-8")
        raw = buf.getvalue()
        # pisa often sets err for CSS quirks; still accept a non-trivial PDF payload.
        if len(raw) > 200:
            if result.err:
                logger.warning("xhtml2pdf_warnings_kept_output", err_count=result.err)
            return raw
        if result.err:
            logger.warning("xhtml2pdf_errors", err_count=result.err)
        return None
    except Exception as e:
        logger.warning("xhtml2pdf_failed", error=str(e))
        return None


def _build_html(report: Report, simulation_id: uuid.UUID, sim: Simulation | None) -> str:
    template = Template(REPORT_HTML_TEMPLATE)
    metrics = report.summary_metrics if isinstance(report.summary_metrics, dict) else {}
    personas = report.persona_breakdown or []
    risks = report.risk_matrix or []
    insights = report.key_insights or []
    pivots = report.pivot_suggestions or []
    try:
        return template.render(
            business_name=(sim.business_name if sim else "Simulation") or "Simulation",
            idea_description=(sim.idea_description if sim else "") or "",
            simulation_id=str(simulation_id),
            metrics=metrics,
            personas=personas,
            risks=risks,
            insights=insights,
            pivots=pivots,
        )
    except Exception as e:
        logger.exception("report_pdf_template_failed", error=str(e))
        return template.render(
            business_name="Simulation report",
            idea_description="",
            simulation_id=str(simulation_id),
            metrics={},
            personas=[],
            risks=[],
            insights=[
                {
                    "insight": "Full report could not be rendered to PDF",
                    "supporting_evidence": "Some report fields may be in an unexpected format.",
                    "actionability": "Try again or re-run the simulation",
                }
            ],
            pivots=[],
        )


async def generate_pdf(
    report: Report, simulation_id: uuid.UUID, db: AsyncSession
) -> tuple[str, Literal["pdf", "html"]]:
    result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    sim = result.scalar_one_or_none()
    html = _build_html(report, simulation_id, sim)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_filename = f"report_{simulation_id}.pdf"

    pdf_bytes: bytes | None = None
    engine = None
    # xhtml2pdf first (pure Python, Windows/Railway-friendly); WeasyPrint needs GTK/Cairo.
    b = _html_to_pdf_xhtml2pdf(html)
    if b:
        pdf_bytes, engine = b, "xhtml2pdf"
    if not pdf_bytes:
        b = _html_to_pdf_weasyprint(html)
        if b:
            pdf_bytes, engine = b, "weasyprint"

    if pdf_bytes:
        try:
            from services.storage_service import upload_report_pdf

            cdn_url = await upload_report_pdf(
                pdf_bytes=pdf_bytes,
                simulation_id=str(simulation_id),
                report_type="standard",
            )
            if cdn_url:
                report.pdf_url = cdn_url
                await db.commit()
                logger.info("pdf_uploaded", simulation_id=str(simulation_id), url=cdn_url, engine=engine)
                return cdn_url, "pdf"
        except Exception as e:
            logger.warning("pdf_s3_upload_skipped", error=str(e))

        pdf_path = REPORTS_DIR / pdf_filename
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        pdf_url = f"/static/reports/{pdf_filename}"
        report.pdf_url = pdf_url
        await db.commit()
        logger.info("pdf_saved_locally", simulation_id=str(simulation_id), path=str(pdf_path), engine=engine)
        return pdf_url, "pdf"

    logger.warning("pdf_engines_failed_using_html_fallback", simulation_id=str(simulation_id))
    html_filename = f"report_{simulation_id}.html"
    html_path = REPORTS_DIR / html_filename
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    html_url = f"/static/reports/{html_filename}"
    report.pdf_url = html_url
    await db.commit()
    return html_url, "html"


def is_pdf_url(url: str | None) -> bool:
    """
    True if URL points to a servable export (PDF or HTML fallback).
    Presigned URLs may include query strings; only the path is checked.
    """
    if not url:
        return False
    base = url.split("?", 1)[0].strip().lower()
    return base.endswith(".pdf") or base.endswith(".html")
