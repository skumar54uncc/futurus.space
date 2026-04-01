"""
AWS S3 storage service for Futurus.
Stores: simulation PDF reports, investor reports, shared report assets.
Bucket: futurus-reports (create this in AWS Console)
"""
import re
import uuid
from urllib.parse import unquote

import boto3
from botocore.exceptions import ClientError
from core.config import settings
import structlog

logger = structlog.get_logger()

_s3_client_singleton = None


def _get_s3_client():
    """Create (cached) boto3 S3 client from settings."""
    global _s3_client_singleton
    if _s3_client_singleton is None and (
        settings.aws_access_key_id or settings.aws_secret_access_key
    ):
        _s3_client_singleton = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            region_name=settings.aws_region or "us-east-1",
        )
    return _s3_client_singleton


BUCKET = settings.aws_s3_bucket
CDN_BASE = settings.aws_cloudfront_url


def _extract_s3_key(url: str) -> str | None:
    """
    Extract the S3 object key from any S3 URL format.

    Handles:
      https://bucket-name.s3.amazonaws.com/reports/file.pdf
      https://bucket-name.s3.us-east-1.amazonaws.com/reports/file.pdf
      https://s3.amazonaws.com/bucket-name/reports/file.pdf
      https://xxxxx.cloudfront.net/reports/file.pdf
      s3://bucket-name/reports/file.pdf
    """
    if not url:
        return None

    u = url.strip()

    # s3:// protocol
    if u.startswith("s3://"):
        parts = u[5:].split("/", 1)
        return parts[1] if len(parts) > 1 else None

    # CloudFront URL — key starts after the domain
    cloudfront_url = (settings.aws_cloudfront_url or "").rstrip("/")
    if cloudfront_url and u.startswith(cloudfront_url):
        return u[len(cloudfront_url) :].lstrip("/")

    # Path-style: https://s3.amazonaws.com/bucket/key
    path_style = re.match(
        r"https?://s3(?:\.[a-z0-9-]+)?\.amazonaws\.com/[^/]+/(.+?)(\?.*)?$",
        u,
    )
    if path_style:
        return unquote(path_style.group(1))

    # Virtual-hosted style: https://bucket.s3.amazonaws.com/key
    vhost_style = re.match(
        r"https?://[^.]+\.s3(?:\.[a-z0-9-]+)?\.amazonaws\.com/(.+?)(\?.*)?$",
        u,
    )
    if vhost_style:
        return unquote(vhost_style.group(1))

    # Local / static file path — not an S3 URL, return None (no presign needed)
    if u.startswith("/static/") or u.startswith("http://localhost"):
        return None

    logger.warning("s3_key_extraction_failed", url=u)
    return None


# Backwards compatibility for any code importing the old name
def extract_s3_key_from_report_url(url: str) -> str | None:
    """Prefer _extract_s3_key; kept for callers that expect the old name."""
    return _extract_s3_key(url)


async def upload_report_pdf(
    pdf_bytes: bytes,
    simulation_id: str,
    report_type: str = "standard",
) -> str:
    """Upload a PDF report to S3 and return the CloudFront CDN URL."""
    client = _get_s3_client()
    if not client:
        logger.warning("s3_not_configured")
        return ""

    key = f"reports/{simulation_id}/{report_type}_{uuid.uuid4().hex[:8]}.pdf"
    try:
        client.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=pdf_bytes,
            ContentType="application/pdf",
            CacheControl="max-age=86400",
            Metadata={
                "simulation-id": simulation_id,
                "report-type": report_type,
            },
        )
        cdn_url = f"{CDN_BASE}/{key}" if CDN_BASE else f"https://{BUCKET}.s3.amazonaws.com/{key}"
        logger.info("report_uploaded", key=key, url=cdn_url)
        return cdn_url
    except ClientError as e:
        # Do not raise — caller falls back to serving PDF from local static files.
        logger.warning("s3_upload_failed_fallback_local", error=str(e), key=key)
        return ""


async def upload_report_bytes(
    data: bytes,
    filename: str,
    content_type: str = "application/pdf",
) -> str:
    """Upload raw bytes under reports/{filename}. Returns CDN/S3 URL or "" if S3 unavailable."""
    client = _get_s3_client()
    if not client:
        logger.warning("s3_not_configured")
        return ""
    key = f"reports/{filename}"
    try:
        client.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="max-age=86400",
        )
        cdn_url = f"{CDN_BASE}/{key}" if CDN_BASE else f"https://{BUCKET}.s3.amazonaws.com/{key}"
        logger.info("report_bytes_uploaded", key=key, url=cdn_url)
        return cdn_url
    except ClientError as e:
        logger.warning("s3_bytes_upload_failed", error=str(e), key=key)
        return ""


async def upload_report_html(
    html_content: str,
    simulation_id: str,
    report_type: str = "standard",
) -> str:
    """Upload HTML fallback report to S3; returns CDN or S3 URL, or "" if S3 unavailable."""
    client = _get_s3_client()
    if not client:
        logger.warning("s3_not_configured")
        return ""

    body = html_content.encode("utf-8")
    key = f"reports/{simulation_id}/{report_type}_{uuid.uuid4().hex[:8]}.html"
    try:
        client.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=body,
            ContentType="text/html; charset=utf-8",
            CacheControl="max-age=86400",
            Metadata={
                "simulation-id": simulation_id,
                "report-type": report_type,
            },
        )
        cdn_url = f"{CDN_BASE}/{key}" if CDN_BASE else f"https://{BUCKET}.s3.amazonaws.com/{key}"
        logger.info("report_html_uploaded", key=key, url=cdn_url)
        return cdn_url
    except ClientError as e:
        logger.warning("s3_html_upload_failed", error=str(e), key=key)
        return ""


async def presign_private_report_url(
    url: str | None,
    *,
    expiry_seconds: int = 3600,
) -> str | None:
    """
    Generate a presigned GET URL for a private S3 object.
    Returns None if url is empty/None (not an error).
    Returns None for relative /static paths (caller should use the path as-is).
    Returns the same URL if it is already presigned.
    Raises RuntimeError if signing fails for a recognized S3 object (so callers know it broke).
    """
    if not url:
        return None

    u = url.strip()
    if u.startswith("/"):
        return None
    if "X-Amz-Signature=" in u or "x-amz-signature" in u.lower() or "X-Amz-Algorithm=" in u:
        return u

    key = _extract_s3_key(u)
    if not key:
        logger.warning("presign_could_not_extract_key", url=u)
        return None

    bucket = settings.aws_s3_bucket
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET is not configured — cannot presign URL")

    client = _get_s3_client()
    if not client:
        raise RuntimeError("AWS credentials are not configured — cannot presign URL")

    try:
        signed = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry_seconds,
        )
        return signed
    except Exception as e:
        logger.exception("presign_failed", url=u, error=str(e))
        raise RuntimeError(f"Could not generate presigned URL: {e}") from e


async def get_presigned_url(key: str, expiry_seconds: int = 3600) -> str:
    """Generate a presigned URL for private report access."""
    client = _get_s3_client()
    if not client:
        return ""
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=expiry_seconds,
        )
        return url
    except ClientError as e:
        logger.error("presigned_url_failed", error=str(e))
        raise


async def delete_report(key: str) -> bool:
    """Delete a report from S3."""
    client = _get_s3_client()
    if not client:
        return False
    try:
        client.delete_object(Bucket=BUCKET, Key=key)
        return True
    except ClientError:
        return False


def get_cdn_url(s3_key: str) -> str:
    """Convert an S3 key to its CloudFront CDN URL."""
    if CDN_BASE:
        return f"{CDN_BASE}/{s3_key}"
    return f"https://{BUCKET}.s3.amazonaws.com/{s3_key}"
