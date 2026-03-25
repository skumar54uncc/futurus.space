"""
AWS SES email service for Futurus.
Sends: simulation complete, welcome, share notifications.

Before this works you must:
1. Verify your sender domain (futurus.dev) in AWS SES Console
2. Request production access (exit sandbox) — takes 24hrs
3. While in sandbox: you can only send to verified email addresses
"""
import boto3
from botocore.exceptions import ClientError
from core.config import settings
import structlog

logger = structlog.get_logger()

ses_client = None


def _get_ses():
    global ses_client
    if ses_client is None and settings.aws_access_key_id:
        ses_client = boto3.client(
            "ses",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_ses_region,
        )
    return ses_client


FROM_ADDRESS = f"Futurus <noreply@{settings.app_domain}>"
REPLY_TO = f"hello@{settings.app_domain}"


async def send_simulation_complete(
    to_email: str,
    user_name: str,
    business_name: str,
    report_url: str,
    adoption_rate: float,
) -> bool:
    subject = f"Your Futurus simulation for {business_name} is ready"
    html_body = f"""<!DOCTYPE html>
<html>
<head><style>
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #020207; color: #f1f5f9; margin: 0; padding: 0; }}
  .container {{ max-width: 560px; margin: 0 auto; padding: 40px 24px; }}
  .logo {{ font-size: 22px; font-style: italic; color: #f1f5f9; margin-bottom: 32px; }}
  .logo span {{ font-style: normal; opacity: 0.4; font-size: 13px; display: block; margin-top: 2px; }}
  h1 {{ font-size: 24px; font-weight: 500; margin: 0 0 12px; }}
  p {{ font-size: 15px; color: #94a3b8; line-height: 1.6; margin: 0 0 20px; }}
  .metric {{ background: #0d0d1a; border: 1px solid rgba(99,102,241,0.3); border-radius: 12px; padding: 20px 24px; margin: 24px 0; }}
  .metric-label {{ font-size: 12px; color: #475569; text-transform: uppercase; letter-spacing: 0.06em; }}
  .metric-value {{ font-size: 36px; font-weight: 500; color: #818cf8; margin-top: 4px; }}
  .btn {{ display: inline-block; background: #6366f1; color: white; text-decoration: none; padding: 14px 28px; border-radius: 10px; font-size: 15px; font-weight: 500; margin: 8px 0; }}
  .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.06); font-size: 12px; color: #475569; }}
</style></head>
<body>
  <div class="container">
    <div class="logo">Futurus<span>See what is about to be</span></div>
    <h1>Your simulation is ready</h1>
    <p>Hi {user_name}, the simulation for <strong style="color:#f1f5f9">{business_name}</strong> has finished running through 1,000 AI minds.</p>
    <div class="metric">
      <div class="metric-label">Projected adoption rate</div>
      <div class="metric-value">{adoption_rate:.1f}%</div>
    </div>
    <p>Your full report includes the adoption curve, failure points, persona breakdown, risk matrix, and pivot suggestions.</p>
    <a href="{report_url}" class="btn">View your report &rarr;</a>
    <div class="footer">futurus.dev</div>
  </div>
</body>
</html>"""
    return await _send_email(to_email, subject, html_body)


async def send_welcome(to_email: str, user_name: str) -> bool:
    subject = "Welcome to Futurus"
    html_body = f"""<!DOCTYPE html>
<html>
<head><style>
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #020207; color: #f1f5f9; margin: 0; padding: 0; }}
  .container {{ max-width: 560px; margin: 0 auto; padding: 40px 24px; }}
  .logo {{ font-size: 22px; font-style: italic; color: #f1f5f9; margin-bottom: 32px; }}
  h1 {{ font-size: 24px; font-weight: 500; margin: 0 0 12px; }}
  p {{ font-size: 15px; color: #94a3b8; line-height: 1.6; margin: 0 0 20px; }}
  .btn {{ display: inline-block; background: #6366f1; color: white; text-decoration: none; padding: 14px 28px; border-radius: 10px; font-size: 15px; font-weight: 500; }}
  .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.06); font-size: 12px; color: #475569; }}
</style></head>
<body>
  <div class="container">
    <div class="logo">Futurus</div>
    <h1>Welcome, {user_name}</h1>
    <p>You now have access to the simulation layer every idea deserves.</p>
    <p>Describe any idea &mdash; a business, a project, a plan &mdash; and Futurus will run it through 1,000 AI minds.</p>
    <a href="https://{settings.app_domain}/new" class="btn">Run your first simulation &rarr;</a>
    <div class="footer">futurus.dev</div>
  </div>
</body>
</html>"""
    return await _send_email(to_email, subject, html_body)


async def send_report_shared(
    to_email: str,
    sharer_name: str,
    business_name: str,
    report_url: str,
) -> bool:
    subject = f"{sharer_name} shared a Futurus simulation with you"
    html_body = f"""<!DOCTYPE html>
<html>
<head><style>
  body {{ font-family: 'Inter', sans-serif; background: #020207; color: #f1f5f9; margin: 0; padding: 40px 24px; }}
  .container {{ max-width: 560px; margin: 0 auto; }}
  h1 {{ font-size: 22px; font-weight: 500; }}
  p {{ color: #94a3b8; line-height: 1.6; }}
  .btn {{ display: inline-block; background: #6366f1; color: white; text-decoration: none; padding: 13px 26px; border-radius: 10px; font-size: 14px; font-weight: 500; }}
</style></head>
<body>
  <div class="container">
    <h1>{sharer_name} wants you to see this</h1>
    <p>They ran <strong style="color:#f1f5f9">{business_name}</strong> through a Futurus simulation and shared the results with you.</p>
    <a href="{report_url}" class="btn">View the simulation report &rarr;</a>
  </div>
</body>
</html>"""
    return await _send_email(to_email, subject, html_body)


async def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    client = _get_ses()
    if not client:
        logger.warning("ses_not_configured", to=to_email, subject=subject)
        return False
    try:
        client.send_email(
            Source=FROM_ADDRESS,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
            ReplyToAddresses=[REPLY_TO],
        )
        logger.info("email_sent", to=to_email, subject=subject)
        return True
    except ClientError as e:
        logger.error("ses_send_failed", error=str(e), to=to_email)
        return False
