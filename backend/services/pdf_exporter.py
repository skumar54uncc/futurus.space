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
    * { box-sizing: border-box; }
    body {
      font-family: Helvetica, Arial, sans-serif;
      padding: 0;
      margin: 0;
      color: #0f172a;
      font-size: 12.5px;
      line-height: 1.5;
      background: #ffffff;
    }

    /* ── Fixed page header (repeats on every page) ── */
    .page-header {
      position: fixed;
      top: 0; left: 0; right: 0;
      height: 52px;
      background: #1e1b4b;
      padding: 0 28px;
    }
    .page-header-inner {
      display: inline-block;
      width: 100%;
    }
    .page-header-logo {
      display: inline-block;
      vertical-align: middle;
      margin-top: 10px;
    }
    .logo-mark {
      display: inline-block;
      vertical-align: middle;
      width: 22px;
      height: 22px;
      border-radius: 50%;
      border: 2px solid rgba(129,140,248,0.7);
      margin-right: 8px;
      text-align: center;
      line-height: 18px;
    }
    .logo-mark-inner {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #818cf8;
      vertical-align: middle;
      margin-top: -2px;
    }
    .logo-wordmark {
      display: inline-block;
      vertical-align: middle;
      font-size: 18px;
      font-style: italic;
      font-weight: 400;
      color: #f8fafc;
      letter-spacing: -0.01em;
    }
    .page-header-tagline {
      display: inline-block;
      vertical-align: middle;
      float: right;
      margin-top: 17px;
      font-size: 10px;
      color: rgba(255,255,255,0.4);
      letter-spacing: 0.04em;
    }

    /* ── Fixed page footer (repeats on every page) ── */
    .page-footer {
      position: fixed;
      bottom: 0; left: 0; right: 0;
      height: 36px;
      background: #1e1b4b;
      padding: 9px 28px;
    }
    .page-footer-left {
      display: inline-block;
      font-size: 9px;
      color: rgba(255,255,255,0.35);
      letter-spacing: 0.05em;
    }
    .page-footer-right {
      display: inline-block;
      float: right;
      font-size: 9px;
      color: rgba(255,255,255,0.35);
      font-style: italic;
    }

    /* ── Main content area (accounts for fixed header/footer) ── */
    .content {
      margin-top: 68px;
      margin-bottom: 48px;
      padding: 0 28px;
    }

    /* ── Hero cover block ── */
    .cover-block {
      background: #1e1b4b;
      border-radius: 12px;
      padding: 28px 28px 24px;
      margin-bottom: 28px;
      color: #fff;
    }
    .cover-label {
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #818cf8;
      margin-bottom: 10px;
    }
    .cover-title {
      font-size: 22px;
      font-weight: 700;
      color: #f8fafc;
      margin: 0 0 8px 0;
      line-height: 1.25;
    }
    .cover-idea {
      font-size: 12px;
      color: rgba(255,255,255,0.55);
      margin: 0;
      line-height: 1.6;
    }
    .cover-badge {
      display: inline-block;
      margin-top: 14px;
      padding: 4px 12px;
      background: rgba(99,102,241,0.2);
      border: 1px solid rgba(99,102,241,0.4);
      border-radius: 100px;
      font-size: 10px;
      font-weight: 600;
      color: #a5b4fc;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    /* ── Section headings ── */
    h2 {
      font-size: 13px;
      font-weight: 700;
      color: #312e81;
      margin: 28px 0 12px 0;
      padding-bottom: 6px;
      border-bottom: 1.5px solid #e0e7ff;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    /* ── Metrics grid ── */
    .metric-row { margin-bottom: 8px; }
    .metric {
      display: inline-block;
      margin: 0 10px 10px 0;
      padding: 12px 16px;
      background: #f5f3ff;
      border: 1.5px solid #ddd6fe;
      border-radius: 10px;
      vertical-align: top;
      min-width: 95px;
    }
    .metric .value {
      font-size: 22px;
      font-weight: 700;
      color: #4338ca;
      line-height: 1;
      margin-bottom: 4px;
    }
    .metric .label {
      font-size: 9.5px;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-weight: 600;
    }
    .metric-highlight .value { color: #16a34a; }
    .metric-warn .value { color: #d97706; }

    /* ── Tables ── */
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 4px;
      font-size: 11.5px;
    }
    thead tr { background: #1e1b4b; }
    thead th {
      text-align: left;
      padding: 8px 10px;
      font-size: 9.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #a5b4fc;
      border: none;
    }
    tbody tr:nth-child(even) { background: #f8f7ff; }
    tbody tr:nth-child(odd) { background: #ffffff; }
    tbody td {
      padding: 8px 10px;
      border-bottom: 1px solid #ede9fe;
      color: #1e293b;
      vertical-align: top;
    }
    tbody td:first-child { font-weight: 600; color: #312e81; }
    .risk-high { color: #dc2626; font-weight: 700; }
    .risk-medium { color: #d97706; font-weight: 600; }
    .risk-low { color: #16a34a; font-weight: 600; }

    /* ── Insight / Pivot cards ── */
    .card {
      margin-bottom: 10px;
      padding: 14px 16px;
      background: #fafafa;
      border-radius: 8px;
      border: 1px solid #e2e8f0;
      border-left: 3px solid #6366f1;
    }
    .card-title {
      font-weight: 700;
      font-size: 13px;
      color: #1e293b;
      margin-bottom: 4px;
    }
    .card-sub {
      font-size: 11.5px;
      color: #64748b;
      margin-top: 3px;
      line-height: 1.5;
    }
    .card-action {
      font-size: 11.5px;
      color: #4f46e5;
      margin-top: 5px;
      font-weight: 600;
    }
    .card-pivot { border-left-color: #7c3aed; }
    .confidence-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 100px;
      font-size: 9px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-top: 5px;
    }
    .conf-high { background: #dcfce7; color: #166534; }
    .conf-medium { background: #fef9c3; color: #854d0e; }
    .conf-low { background: #fee2e2; color: #991b1b; }

    /* ── Disclaimer ── */
    .disclaimer {
      margin-top: 28px;
      padding: 12px 14px;
      background: #fffbeb;
      border: 1px solid #fde68a;
      border-radius: 8px;
      font-size: 10.5px;
      color: #78350f;
      line-height: 1.6;
    }

    /* ── Watermark ── */
    .watermark {
      position: fixed;
      top: 38%;
      left: 50%;
      width: 100%;
      margin-left: -50%;
      text-align: center;
      font-size: 80px;
      font-weight: 900;
      color: #6366f1;
      opacity: 0.03;
      letter-spacing: 0.2em;
    }
  </style>
</head>
<body>

  <!-- Repeated page header -->
  <div class="page-header">
    <div class="page-header-inner">
      <div class="page-header-logo">
        <span class="logo-mark"><span class="logo-mark-inner"></span></span>
        <span class="logo-wordmark">Futurus</span>
      </div>
      <span class="page-header-tagline">AI Market Simulation &nbsp;·&nbsp; Confidential</span>
    </div>
  </div>

  <!-- Repeated page footer -->
  <div class="page-footer">
    <span class="page-footer-left">Report ID: {{ simulation_id }} &nbsp;·&nbsp; futurus.dev</span>
    <span class="page-footer-right">&#169; Futurus &nbsp;·&nbsp; Proprietary Output</span>
  </div>

  <!-- Watermark -->
  <div class="watermark">FUTURUS</div>

  <!-- Main content -->
  <div class="content">

    <!-- Cover block -->
    <div class="cover-block">
      <div class="cover-label">Simulation Report</div>
      <h1 class="cover-title">{{ business_name }}</h1>
      <p class="cover-idea">{{ idea_description }}</p>
      <span class="cover-badge">AI-Powered Market Simulation</span>
    </div>

    <!-- Key Metrics -->
    <h2>Key Metrics</h2>
    <div class="metric-row">
      <div class="metric metric-highlight">
        <div class="value">{{ metrics.adoption_rate|default('—') }}%</div>
        <div class="label">Adoption Rate</div>
      </div>
      <div class="metric metric-warn">
        <div class="value">{{ metrics.churn_rate|default('—') }}%</div>
        <div class="label">Churn Rate</div>
      </div>
      <div class="metric">
        <div class="value">{{ metrics.total_adopters|default('—') }}</div>
        <div class="label">Total Adopters</div>
      </div>
      <div class="metric">
        <div class="value">{{ metrics.viral_coefficient|default('—') }}</div>
        <div class="label">Viral Coefficient</div>
      </div>
      <div class="metric">
        <div class="value">{{ metrics.confidence_score|default('—') }}%</div>
        <div class="label">Confidence Score</div>
      </div>
    </div>

    <!-- Segment Analysis -->
    <h2>Customer Segment Analysis</h2>
    <table>
      <thead>
        <tr>
          <th>Segment</th>
          <th>Adoption Rate</th>
          <th>Churn Rate</th>
          <th>Referrals Generated</th>
        </tr>
      </thead>
      <tbody>
        {% for p in personas %}
        <tr>
          <td>{{ p.segment|default('—') }}</td>
          <td>{{ p.adoption_rate|default('—') }}%</td>
          <td>{{ p.churn_rate|default('—') }}%</td>
          <td>{{ p.referrals_generated|default('—') }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>

    <!-- Risk Assessment -->
    <h2>Risk Assessment</h2>
    <table>
      <thead>
        <tr>
          <th>Risk Factor</th>
          <th>Probability</th>
          <th>Impact</th>
          <th>Mitigation Strategy</th>
        </tr>
      </thead>
      <tbody>
        {% for risk in risks %}
        <tr>
          <td style="font-weight:400;color:#1e293b;">{{ risk.risk|default('—') }}</td>
          <td class="risk-{{ risk.probability|default('low') }}">{{ risk.probability|default('—')|title }}</td>
          <td class="risk-{{ risk.impact|default('low') }}">{{ risk.impact|default('—')|title }}</td>
          <td style="font-weight:400;color:#475569;">{{ risk.mitigation|default('—') }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>

    <!-- Key Insights -->
    <h2>Key Insights</h2>
    {% for insight in insights %}
    <div class="card">
      <div class="card-title">{{ insight.insight|default('—') }}</div>
      <div class="card-sub">{{ insight.supporting_evidence|default('') }}</div>
      <div class="card-action">&#8594; {{ insight.actionability|default('—') }}</div>
    </div>
    {% endfor %}

    <!-- Pivot Suggestions -->
    <h2>Pivot Suggestions</h2>
    {% for pivot in pivots %}
    <div class="card card-pivot">
      <div class="card-title">{{ pivot.pivot|default('—') }}</div>
      <div class="card-sub">{{ pivot.rationale|default('') }}</div>
      <div class="card-sub" style="margin-top:4px;"><em>Evidence: {{ pivot.evidence_from_simulation|default('—') }}</em></div>
      <span class="confidence-badge conf-{{ pivot.confidence|default('low') }}">{{ pivot.confidence|default('—')|title }} Confidence</span>
    </div>
    {% endfor %}

    <!-- Disclaimer -->
    <div class="disclaimer">
      <strong>Important Notice:</strong> This report is generated by Futurus AI market simulation and is intended
      as a directional tool to inform decision-making. Results represent modeled behavior of AI agents and are not
      guarantees of real-world outcomes. The confidence score ({{ metrics.confidence_score|default('—') }}%) reflects
      internal simulation consistency. Always validate insights with real customer research before making major decisions.
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
