import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.middleware.auth import get_current_user
from api.middleware.rate_limiter import LIMITS, limiter
from core.database import get_db
from models.simulation import Report, Simulation
from models.user import User
from schemas.report import ReportResponse
from services.pdf_exporter import is_pdf_url
from services.storage_service import presign_private_report_url

logger = structlog.get_logger()
router = APIRouter(prefix="/api/reports", tags=["reports"])

# Private S3 objects need signed GETs; share links get a longer TTL so tabs stay valid.
_PRESIGN_AUTH_SECONDS = 3600
_PRESIGN_SHARE_SECONDS = 86_400


async def _report_response_presigned(report: Report, *, ttl: int) -> ReportResponse:
    base = ReportResponse.model_validate(report)

    async def _sign(url: str | None) -> str | None:
        if not url:
            return url
        try:
            signed = await presign_private_report_url(url, expiry_seconds=ttl)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail="Could not sign download URL. Check AWS credentials.") from e

        if signed:
            return signed

        # If presigning didn't return a signed URL, only allow local/static URLs to be returned
        ru = url.strip()
        if ru.startswith("/") or ru.startswith("http://localhost"):
            return url
        raise HTTPException(status_code=500, detail="Could not sign download URL. Check AWS credentials.")

    signed_pdf = await _sign(base.pdf_url)
    signed_investor = await _sign(base.investor_pdf_url)

    return base.model_copy(
        update={
            "pdf_url": signed_pdf,
            "investor_pdf_url": signed_investor,
        }
    )


@router.get("/{simulation_id}", response_model=ReportResponse)
@limiter.limit(LIMITS["default_authenticated"])
async def get_report(
    request: Request,
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Report).where(Report.simulation_id == simulation_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    sim_result = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.user_id == current_user.id,
        )
    )
    if not sim_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    return await _report_response_presigned(report, ttl=_PRESIGN_AUTH_SECONDS)


@router.get("/{simulation_id}/export/pdf")
@limiter.limit(LIMITS["pdf_export"])
async def export_pdf(
    request: Request,
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Report).where(Report.simulation_id == simulation_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    sim_own = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.user_id == current_user.id,
        )
    )
    if not sim_own.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    if report.pdf_url and is_pdf_url(report.pdf_url):
        try:
            signed = await presign_private_report_url(
                report.pdf_url,
                expiry_seconds=_PRESIGN_AUTH_SECONDS,
            )
            if signed:
                path_low = signed.lower().split("?")[0]
                fmt: str = "pdf" if path_low.endswith(".pdf") else "html"
                return {"pdf_url": signed, "format": fmt}

            # None = not S3 / no key — only safe to return relative or localhost URLs as-is
            ru = report.pdf_url.strip()
            if ru.startswith("/") or ru.startswith("http://localhost"):
                raw_low = ru.lower().split("?")[0]
                fmt = "pdf" if raw_low.endswith(".pdf") else "html"
                return {"pdf_url": report.pdf_url, "format": fmt}

            # If we could not sign and it's not a local URL, fail loudly so frontend doesn't receive unsigned S3 URL
            raise HTTPException(
                status_code=500,
                detail="Could not sign download URL. Check AWS credentials.",
            )
        except RuntimeError as e:
            logger.exception(
                "presign_failed_will_regenerate",
                simulation_id=str(simulation_id),
                error=str(e),
            )
            raise HTTPException(
                status_code=500,
                detail="Could not sign download URL. Check AWS credentials.",
            ) from e

    if report.pdf_url and not is_pdf_url(report.pdf_url):
        report.pdf_url = None
        await db.commit()

    from services.pdf_exporter import generate_pdf

    try:
        pdf_url, fmt = await generate_pdf(report, simulation_id, db)
    except Exception:
        logger.exception("pdf_generation_failed", simulation_id=str(simulation_id))
        raise HTTPException(
            status_code=500,
            detail="Could not generate export file. Please try again.",
        )

    if not pdf_url:
        raise HTTPException(
            status_code=500,
            detail="Export produced no file. Please try again.",
        )

    report.pdf_url = pdf_url
    await db.commit()

    try:
        signed = await presign_private_report_url(
            pdf_url,
            expiry_seconds=_PRESIGN_AUTH_SECONDS,
        )
        if signed:
            return {"pdf_url": signed, "format": fmt}
        if pdf_url.startswith("/static/") or pdf_url.startswith("http://localhost"):
            return {"pdf_url": pdf_url, "format": fmt}
        raise HTTPException(
            status_code=500,
            detail="PDF generated but could not be signed for download. Check AWS credentials.",
        )
    except RuntimeError as e:
        logger.error("presign_failed_after_generation", error=str(e))
        if pdf_url.startswith("/static/") or pdf_url.startswith("http://localhost"):
            return {"pdf_url": pdf_url, "format": fmt}
        raise HTTPException(
            status_code=500,
            detail="PDF generated but could not be signed for download. Check AWS credentials.",
        )


@router.get("/share/{share_token}", response_model=ReportResponse)
@limiter.limit(LIMITS["public"])
async def get_shared_report(
    request: Request,
    share_token: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.simulation))
        .where(Report.share_token == share_token)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or link expired")
    base = await _report_response_presigned(report, ttl=_PRESIGN_SHARE_SECONDS)
    sim = report.simulation
    if sim is not None:
        return base.model_copy(
            update={
                "business_name": sim.business_name,
                "idea_description": sim.idea_description,
            }
        )
    return base
