"""
Transactional email for Futurus: simulation complete, welcome, share.

Priority:
1. AWS SES (when AWS_ACCESS_KEY_ID is set and SES send succeeds)
2. SMTP (e.g. Gmail + app password) when SMTP_HOST, SMTP_USER, SMTP_PASS are set on the **backend** (DigitalOcean)

Vercel-only SMTP does not apply here — the worker runs on the API server.
"""
import asyncio
import smtplib
from email.mime.text import MIMEText

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
    subject = f"Your Futurus simulation for \"{business_name}\" is ready"
    score_label = "Strong" if adoption_rate >= 60 else ("Moderate" if adoption_rate >= 35 else "Low")
    score_color = "#22c55e" if adoption_rate >= 60 else ("#f59e0b" if adoption_rate >= 35 else "#ef4444")
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#010109;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<!--[if mso]><table width="100%"><tr><td><![endif]-->
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#010109;min-height:100vh;">
  <tr>
    <td align="center" style="padding:40px 16px;">
      <table width="560" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;width:100%;">

        <!-- Header / Logo -->
        <tr>
          <td style="padding:0 0 36px 0;">
            <table cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="padding-right:10px;vertical-align:middle;">
                  <!-- Futurus mark: concentric circles -->
                  <table cellpadding="0" cellspacing="0" border="0" style="width:28px;height:28px;">
                    <tr><td align="center" valign="middle">
                      <div style="width:28px;height:28px;border-radius:50%;border:1.5px solid rgba(99,102,241,0.7);display:inline-block;position:relative;">
                        &#8226;
                      </div>
                    </td></tr>
                  </table>
                </td>
                <td style="vertical-align:middle;">
                  <span style="font-family:Georgia,'Times New Roman',serif;font-size:22px;font-style:italic;color:#f8fafc;letter-spacing:-0.01em;">Futurus</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Hero section -->
        <tr>
          <td style="background:linear-gradient(135deg,#0d0d1a 0%,#0a0a1f 100%);border:1px solid rgba(99,102,241,0.2);border-radius:16px;padding:36px 32px 32px;">

            <!-- Status badge -->
            <table cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;">
              <tr>
                <td style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);border-radius:100px;padding:5px 14px;">
                  <span style="font-size:12px;font-weight:600;color:#4ade80;letter-spacing:0.05em;text-transform:uppercase;">&#10003; Simulation Complete</span>
                </td>
              </tr>
            </table>

            <h1 style="margin:0 0 8px;font-size:26px;font-weight:600;color:#f8fafc;line-height:1.3;">Your report is ready</h1>
            <p style="margin:0 0 28px;font-size:16px;color:#94a3b8;line-height:1.6;">Hi {user_name}, the simulation for <strong style="color:#e2e8f0;">{business_name}</strong> has finished.</p>

            <!-- Adoption metric -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:28px;">
              <tr>
                <td style="background:rgba(0,0,0,0.4);border:1px solid rgba(99,102,241,0.25);border-radius:12px;padding:20px 24px;">
                  <p style="margin:0 0 6px;font-size:11px;font-weight:600;color:#475569;letter-spacing:0.1em;text-transform:uppercase;">Projected Adoption Rate</p>
                  <table cellpadding="0" cellspacing="0" border="0">
                    <tr>
                      <td style="vertical-align:baseline;">
                        <span style="font-size:42px;font-weight:700;color:{score_color};line-height:1;">{adoption_rate:.1f}%</span>
                      </td>
                      <td style="vertical-align:baseline;padding-left:10px;padding-bottom:6px;">
                        <span style="font-size:14px;font-weight:500;color:{score_color};">&#8212; {score_label}</span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <!-- What's in the report -->
            <p style="margin:0 0 16px;font-size:14px;color:#64748b;line-height:1.5;">Your full report includes:</p>
            <table cellpadding="0" cellspacing="0" border="0" style="margin-bottom:28px;">
              {''.join(f'<tr><td style="padding:4px 0;font-size:14px;color:#94a3b8;"><span style="color:#6366f1;margin-right:8px;">&#x2192;</span>{item}</td></tr>' for item in ['Adoption curve over simulation turns', 'Persona segment breakdown', 'Failure points &amp; churn triggers', 'Risk matrix with probability scores', 'Pivot suggestions from AI analysis'])}
            </table>

            <!-- CTA Button -->
            <table cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:#6366f1;border-radius:10px;">
                  <a href="{report_url}" style="display:inline-block;padding:14px 28px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;letter-spacing:0.01em;">View Full Report &nbsp;&#8594;</a>
                </td>
              </tr>
            </table>

          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:28px 0 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid rgba(255,255,255,0.06);">
              <tr>
                <td style="padding-top:20px;">
                  <p style="margin:0;font-size:12px;color:#334155;line-height:1.6;">You received this because you opted in to email updates for this simulation.<br>
                  <a href="https://futurus.dev" style="color:#475569;text-decoration:none;">futurus.dev</a> &nbsp;&middot;&nbsp; <a href="https://futurus.dev/dashboard" style="color:#475569;text-decoration:none;">Go to dashboard</a></p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
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


async def send_credit_reset_notification(
    to_email: str,
    user_name: str,
    daily_limit: int,
    reset_url: str,
) -> bool:
    subject = "Your Futurus credits have reset"
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#010109;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#010109;min-height:100vh;">
  <tr>
    <td align="center" style="padding:40px 16px;">
      <table width="560" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;width:100%;">
        <tr>
          <td style="padding:0 0 24px 0;">
            <span style="font-family:Georgia,'Times New Roman',serif;font-size:22px;font-style:italic;color:#f8fafc;letter-spacing:-0.01em;">Futurus</span>
          </td>
        </tr>

        <tr>
          <td style="background:linear-gradient(135deg,#0d0d1a 0%,#0a0a1f 100%);border:1px solid rgba(99,102,241,0.22);border-radius:18px;padding:36px 32px;">
            <table cellpadding="0" cellspacing="0" border="0" style="margin-bottom:18px;">
              <tr>
                <td style="background:rgba(96,165,250,0.10);border:1px solid rgba(96,165,250,0.24);border-radius:999px;padding:6px 14px;">
                  <span style="font-size:12px;font-weight:600;color:#93c5fd;letter-spacing:0.06em;text-transform:uppercase;">Daily credits refreshed</span>
                </td>
              </tr>
            </table>

            <h1 style="margin:0 0 10px;font-size:26px;font-weight:600;color:#f8fafc;line-height:1.25;">Your simulation credits are ready again</h1>
            <p style="margin:0 0 22px;font-size:16px;color:#94a3b8;line-height:1.7;">Hi {user_name}, your daily Futurus credits have reset. You can launch new simulations, test ideas, and review the next set of agent insights.</p>

            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:24px;">
              <tr>
                <td style="background:rgba(0,0,0,0.35);border:1px solid rgba(99,102,241,0.2);border-radius:14px;padding:18px 20px;">
                  <p style="margin:0 0 6px;font-size:11px;font-weight:600;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;">Available today</p>
                  <p style="margin:0;font-size:34px;font-weight:700;color:#22c55e;line-height:1;">{daily_limit}</p>
                  <p style="margin:8px 0 0;font-size:14px;color:#94a3b8;line-height:1.6;">Use them to run simulations, compare ideas, and publish the strongest ones to the public dashboard.</p>
                </td>
              </tr>
            </table>

            <table cellpadding="0" cellspacing="0" border="0" style="margin-bottom:22px;">
              <tr>
                <td style="background:#6366f1;border-radius:10px;">
                  <a href="{reset_url}" style="display:inline-block;padding:14px 28px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;letter-spacing:0.01em;">Start a new simulation &rarr;</a>
                </td>
              </tr>
            </table>

            <p style="margin:0;font-size:13px;color:#64748b;line-height:1.6;">If you were already in the app, refresh the page to see the new limit immediately. You can also visit <a href="https://{settings.app_domain}" style="color:#93c5fd;text-decoration:none;">{settings.app_domain}</a> at any time.</p>
          </td>
        </tr>

        <tr>
          <td style="padding:18px 0 0;">
            <p style="margin:0;font-size:12px;color:#334155;line-height:1.6;text-align:center;">Futurus · Predict ideas before you build them</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""
    return await _send_email(to_email, subject, html_body)


def _smtp_configured() -> bool:
    return bool(
        settings.smtp_host.strip()
        and settings.smtp_user.strip()
        and (settings.smtp_password or "").strip()
    )


def _smtp_send_sync(to_email: str, subject: str, html_body: str) -> None:
    """Send via Gmail-compatible SMTP (runs in thread pool)."""
    envelope_from = settings.smtp_user.strip()
    display_from = (settings.smtp_from or "").strip() or f"Futurus <{envelope_from}>"
    reply_to = REPLY_TO if "@" in REPLY_TO else envelope_from

    msg = MIMEText(html_body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = display_from
    msg["To"] = to_email
    msg["Reply-To"] = reply_to

    host = settings.smtp_host.strip()
    port = int(settings.smtp_port or 587)
    password = (settings.smtp_password or "").strip()

    if settings.smtp_secure or port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30) as server:
            server.login(envelope_from, password)
            server.sendmail(envelope_from, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls()
            server.login(envelope_from, password)
            server.sendmail(envelope_from, [to_email], msg.as_string())


async def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    client = _get_ses()
    if client:
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
            logger.info("email_sent_ses", to=to_email, subject=subject)
            return True
        except ClientError as e:
            logger.warning("ses_send_failed_will_try_smtp", error=str(e), to=to_email)

    if _smtp_configured():
        try:
            await asyncio.to_thread(_smtp_send_sync, to_email, subject, html_body)
            logger.info("email_sent_smtp", to=to_email, subject=subject)
            return True
        except Exception as e:
            logger.error("smtp_send_failed", error=str(e), to=to_email)
            return False

    if not client:
        logger.warning(
            "email_not_configured",
            to=to_email,
            subject=subject,
            hint="Set AWS SES keys and verify domain, or set SMTP_HOST, SMTP_USER, SMTP_PASS on the backend.",
        )
    else:
        logger.error("email_send_failed_no_smtp_fallback", to=to_email, subject=subject)
    return False
