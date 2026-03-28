"""PDF export for reports: WeasyPrint when available, xhtml2pdf fallback (Windows-friendly)."""
import base64
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
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: Helvetica, Arial, sans-serif;
      color: #1e293b;
      font-size: 11px;
      line-height: 1.55;
      background: #ffffff;
    }

    /* ── xhtml2pdf page frames (proper repeating header/footer) ── */
    @page {
      size: A4;
      margin-top: 62px;
      margin-bottom: 46px;
      margin-left: 36px;
      margin-right: 36px;

      @frame header_frame {
        -pdf-frame-content: pdf-page-header;
        top: 0px; left: 0px; right: 0px;
        height: 46px;
      }
      @frame footer_frame {
        -pdf-frame-content: pdf-page-footer;
        bottom: 0px; left: 0px; right: 0px;
        height: 30px;
      }
    }

    /* ── Header bar ── */
    #pdf-page-header {
      background: #1e1b4b;
      height: 46px;
      padding: 0 36px;
    }
    #pdf-page-header table { width: 100%; height: 46px; border-collapse: collapse; }
    #pdf-page-header td { vertical-align: middle; border: none; padding: 0; background: transparent; }
    .hdr-logo-img { height: 24px; width: auto; }
    .hdr-logo-text {
      font-size: 16px; font-style: italic; font-weight: 400;
      color: #f8fafc; letter-spacing: -0.01em;
    }
    .hdr-tagline {
      font-size: 9px; color: rgba(255,255,255,0.45);
      letter-spacing: 0.05em; text-align: right;
    }

    /* ── Footer bar ── */
    #pdf-page-footer {
      background: #1e1b4b;
      height: 30px;
      padding: 0 36px;
    }
    #pdf-page-footer table { width: 100%; height: 30px; border-collapse: collapse; }
    #pdf-page-footer td { vertical-align: middle; border: none; padding: 0; background: transparent; }
    .ftr-left { font-size: 8px; color: rgba(255,255,255,0.4); letter-spacing: 0.04em; }
    .ftr-right { font-size: 8px; color: rgba(255,255,255,0.4); font-style: italic; text-align: right; }

    /* ── Cover block ── */
    .cover {
      background: #1e1b4b;
      border-radius: 10px;
      padding: 22px 24px 18px;
      margin-bottom: 22px;
    }
    .cover-label {
      font-size: 9px; font-weight: 700; letter-spacing: 0.14em;
      text-transform: uppercase; color: #818cf8; margin-bottom: 8px;
    }
    .cover-title {
      font-size: 22px; font-weight: 800; color: #f8fafc;
      line-height: 1.2; margin-bottom: 8px;
    }
    .cover-desc {
      font-size: 11px; color: rgba(255,255,255,0.58); line-height: 1.6; margin-bottom: 14px;
    }
    .cover-badge {
      display: inline-block;
      padding: 3px 10px;
      background: rgba(99,102,241,0.22);
      border: 1px solid rgba(99,102,241,0.45);
      border-radius: 100px;
      font-size: 8.5px; font-weight: 700; color: #a5b4fc;
      letter-spacing: 0.08em; text-transform: uppercase;
    }

    /* ── Section headings ── */
    h2 {
      font-size: 9.5px; font-weight: 800; color: #312e81;
      text-transform: uppercase; letter-spacing: 0.1em;
      padding-bottom: 5px; border-bottom: 1.5px solid #e0e7ff;
      margin: 20px 0 10px 0;
    }

    /* ── Metrics — use table so xhtml2pdf renders columns correctly ── */
    .metrics-tbl { width: 100%; border-collapse: separate; border-spacing: 5px; margin-bottom: 4px; }
    .metrics-tbl td {
      background: #f5f3ff; border: 1.5px solid #ddd6fe;
      border-radius: 8px; padding: 10px 12px;
      vertical-align: top; width: 20%; text-align: left;
    }
    .mv { font-size: 20px; font-weight: 800; color: #4338ca; line-height: 1; margin-bottom: 3px; }
    .ml { font-size: 8px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.07em; font-weight: 600; }
    .mv-green { color: #16a34a; }
    .mv-orange { color: #d97706; }

    /* ── Data tables ── */
    .data-tbl { width: 100%; border-collapse: collapse; font-size: 10.5px; margin-top: 2px; }
    .data-tbl thead tr { background: #1e1b4b; }
    .data-tbl thead th {
      text-align: left; padding: 7px 9px;
      font-size: 8.5px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.08em;
      color: #a5b4fc; border: none;
    }
    .data-tbl tbody tr:nth-child(even) { background: #f8f7ff; }
    .data-tbl tbody tr:nth-child(odd) { background: #ffffff; }
    .data-tbl tbody td {
      padding: 7px 9px; border-bottom: 1px solid #ede9fe;
      color: #1e293b; vertical-align: top;
    }
    .data-tbl tbody td.seg { font-weight: 600; color: #312e81; }
    .risk-critical { color: #b91c1c; font-weight: 700; }
    .risk-high { color: #dc2626; font-weight: 700; }
    .risk-medium { color: #d97706; font-weight: 600; }
    .risk-low { color: #16a34a; font-weight: 600; }
    .risk-name { font-weight: 500; color: #1e293b; }
    .mit { font-weight: 400; color: #475569; }

    /* ── Cards (insights / pivots) ── */
    .card {
      margin-bottom: 8px; padding: 11px 13px;
      background: #fafafa; border-radius: 7px;
      border: 1px solid #e2e8f0; border-left: 3px solid #6366f1;
    }
    .card-pivot { border-left-color: #7c3aed; }
    .card-title { font-weight: 700; font-size: 11.5px; color: #1e293b; margin-bottom: 3px; }
    .card-body { font-size: 10px; color: #64748b; line-height: 1.5; margin-top: 2px; }
    .card-evidence { font-size: 9.5px; color: #94a3b8; font-style: italic; margin-top: 3px; }
    .card-action { font-size: 10px; color: #4f46e5; margin-top: 4px; font-weight: 600; }
    .conf-badge {
      display: inline-block; padding: 1px 7px; border-radius: 100px;
      font-size: 8px; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.06em; margin-top: 4px;
    }
    .conf-high { background: #dcfce7; color: #166534; }
    .conf-medium { background: #fef9c3; color: #854d0e; }
    .conf-low { background: #fee2e2; color: #991b1b; }

    /* ── Disclaimer ── */
    .disclaimer {
      margin-top: 22px; padding: 10px 12px;
      background: #fffbeb; border: 1px solid #fde68a;
      border-radius: 7px; font-size: 9.5px; color: #78350f; line-height: 1.6;
    }
  </style>
</head>
<body>

  <!-- Page header (referenced by @frame header_frame) -->
  <div id="pdf-page-header">
    <table><tr>
      <td>
        {% if logo_b64 %}
        <img class="hdr-logo-img" src="data:image/png;base64,{{ logo_b64 }}" alt="Futurus" />
        {% else %}
        <span class="hdr-logo-text">Futurus</span>
        {% endif %}
      </td>
      <td class="hdr-tagline">AI Market Simulation &nbsp;&middot;&nbsp; Confidential</td>
    </tr></table>
  </div>

  <!-- Page footer (referenced by @frame footer_frame) -->
  <div id="pdf-page-footer">
    <table><tr>
      <td class="ftr-left">Report ID: {{ simulation_id }} &nbsp;&middot;&nbsp; futurus.dev</td>
      <td class="ftr-right">&#169; Futurus &nbsp;&middot;&nbsp; Proprietary Output</td>
    </tr></table>
  </div>

  <!-- Cover -->
  <div class="cover">
    <div class="cover-label">Simulation Report</div>
    <div class="cover-title">{{ business_name }}</div>
    <div class="cover-desc">{{ idea_description }}</div>
    <span class="cover-badge">AI-Powered Market Simulation</span>
  </div>

  <!-- Key Metrics -->
  <h2>Key Metrics</h2>
  <table class="metrics-tbl"><tr>
    <td><div class="mv mv-green">{{ metrics.adoption_rate|default('&mdash;') }}%</div><div class="ml">Adoption Rate</div></td>
    <td><div class="mv mv-orange">{{ metrics.churn_rate|default('&mdash;') }}%</div><div class="ml">Churn Rate</div></td>
    <td><div class="mv">{{ metrics.total_adopters|default('&mdash;') }}</div><div class="ml">Total Adopters</div></td>
    <td><div class="mv">{{ metrics.viral_coefficient|default('&mdash;') }}</div><div class="ml">Viral Coefficient</div></td>
    <td><div class="mv">{{ metrics.confidence_score|default('&mdash;') }}%</div><div class="ml">Confidence Score</div></td>
  </tr></table>

  <!-- Customer Segments -->
  <h2>Customer Segment Analysis</h2>
  <table class="data-tbl">
    <thead><tr>
      <th>Segment</th><th>Adoption Rate</th><th>Churn Rate</th><th>Referrals</th>
    </tr></thead>
    <tbody>
      {% for p in personas %}
      <tr>
        <td class="seg">{{ p.segment|default('&mdash;') }}</td>
        <td>{{ p.adoption_rate|default('&mdash;') }}%</td>
        <td>{{ p.churn_rate|default('&mdash;') }}%</td>
        <td>{{ p.referrals_generated|default('&mdash;') }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <!-- Risk Assessment -->
  <h2>Risk Assessment</h2>
  <table class="data-tbl">
    <thead><tr>
      <th style="width:28%">Risk Factor</th>
      <th style="width:11%">Probability</th>
      <th style="width:11%">Impact</th>
      <th>Mitigation Strategy</th>
    </tr></thead>
    <tbody>
      {% for risk in risks %}
      <tr>
        <td class="risk-name">{{ risk.risk|default('&mdash;') }}</td>
        <td class="risk-{{ risk.probability|default('low') }}">{{ risk.probability|default('&mdash;')|title }}</td>
        <td class="risk-{{ risk.impact|default('low') }}">{{ risk.impact|default('&mdash;')|title }}</td>
        <td class="mit">{{ risk.mitigation|default('&mdash;') }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <!-- Key Insights -->
  <h2>Key Insights</h2>
  {% for insight in insights %}
  <div class="card">
    <div class="card-title">{{ insight.insight|default('&mdash;') }}</div>
    <div class="card-body">{{ insight.supporting_evidence|default('') }}</div>
    <div class="card-action">&#8594; {{ insight.actionability|default('&mdash;') }}</div>
  </div>
  {% endfor %}

  <!-- Pivot Suggestions -->
  <h2>Strategic Pivots</h2>
  {% for pivot in pivots %}
  <div class="card card-pivot">
    <div class="card-title">{{ pivot.pivot|default('&mdash;') }}</div>
    <div class="card-body">{{ pivot.rationale|default('') }}</div>
    <div class="card-evidence">Evidence: {{ pivot.evidence_from_simulation|default('&mdash;') }}</div>
    <span class="conf-badge conf-{{ pivot.confidence|default('low') }}">{{ pivot.confidence|default('&mdash;')|title }} Confidence</span>
  </div>
  {% endfor %}

  <!-- Disclaimer -->
  <div class="disclaimer">
    <strong>Important Notice:</strong> This report is generated by Futurus AI market simulation and is intended
    as a directional tool to inform decision-making. Results represent modeled behavior of AI agents and are not
    guarantees of real-world outcomes. The confidence score ({{ metrics.confidence_score|default('&mdash;') }}%)
    reflects internal simulation consistency. Always validate insights with real customer research before making
    major decisions.
  </div>

</body>
</html>
"""


def _load_logo_b64() -> str:
    """Load the Futurus logo PNG and return as base64 string, or empty string if unavailable."""
    try:
        logo_path = (
            Path(__file__).resolve().parent.parent.parent
            / "frontend" / "public" / "brand" / "futurus-logo-dark.png"
        )
        if logo_path.exists():
            return base64.b64encode(logo_path.read_bytes()).decode()
    except Exception:
        pass
    return ""


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
    logo_b64 = _load_logo_b64()
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
            logo_b64=logo_b64,
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
            logo_b64=logo_b64,
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
