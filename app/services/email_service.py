"""Email service — send transactional emails via SMTP.

Uses Python's stdlib smtplib + email.mime, so no extra dependencies are required.
Emails are dispatched in a background thread so they never block the API response.
"""
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from loguru import logger

from app.core.config import settings


# ── Low-level send ───────────────────────────────────────────────────────────


def _send_email(to_email: str, subject: str, html_body: str) -> None:
    """Send an email via SMTP. Runs synchronously — call from a thread."""
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, to_email, msg.as_string())

        logger.success("Email sent successfully", to=to_email, subject=subject)
    except Exception as e:
        logger.error("Failed to send email", to=to_email, subject=subject, error=str(e))


def _send_email_async(to_email: str, subject: str, html_body: str) -> None:
    """Fire-and-forget: dispatch _send_email in a daemon thread."""
    if not settings.smtp_host or not settings.smtp_username:
        logger.warning("SMTP not configured — skipping email", to=to_email)
        return
    thread = threading.Thread(
        target=_send_email,
        args=(to_email, subject, html_body),
        daemon=True,
    )
    thread.start()


# ── Welcome email ────────────────────────────────────────────────────────────


def send_welcome_email(to_email: str, user_name: str) -> None:
    """Send a welcome email to a newly registered user (non-blocking)."""
    subject = "Welcome to Creator Tools! 🎉"
    html_body = _build_welcome_html(user_name)
    _send_email_async(to_email, subject, html_body)


# ── Password reset email ─────────────────────────────────────────────────────


def send_password_reset_email(to_email: str, user_name: str, reset_link: str) -> None:
    """Send a password reset link to the user (non-blocking)."""
    subject = "Reset your Creator Tools password 🔒"
    html_body = _build_password_reset_html(user_name, reset_link)
    _send_email_async(to_email, subject, html_body)


def _build_password_reset_html(user_name: str, reset_link: str) -> str:
    """Return the HTML body for the password reset email."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Reset Your Password</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f7;font-family:'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f7;padding:40px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0"
               style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 50%,#a855f7 100%);padding:48px 40px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:700;letter-spacing:-0.5px;">
                🎬 Creator Tools
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <h2 style="margin:0 0 16px;color:#1e293b;font-size:22px;font-weight:600;">
                Password Reset Request
              </h2>
              <p style="margin:0 0 20px;color:#475569;font-size:15px;line-height:1.7;">
                Hi {user_name}, we received a request to reset your password for your Creator Tools account.
              </p>
              <p style="margin:0 0 24px;color:#475569;font-size:15px;line-height:1.7;">
                Click the button below to set a new password. This link will expire in 15 minutes.
              </p>

              <!-- CTA Button -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:8px 0 24px;">
                    <a href="{reset_link}"
                       style="display:inline-block;padding:14px 36px;background:linear-gradient(135deg,#6366f1,#8b5cf6);
                              color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;border-radius:8px;
                              box-shadow:0 4px 14px rgba(99,102,241,0.4);">
                      🔒 Reset Password
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin:20px 0 0;color:#94a3b8;font-size:13px;line-height:1.6;">
                If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f8fafc;padding:24px 40px;text-align:center;border-top:1px solid #e2e8f0;">
              <p style="margin:0;color:#94a3b8;font-size:12px;">
                &copy; 2026 Creator Tools. All rights reserved.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _build_welcome_html(user_name: str) -> str:
    """Return the HTML body for the welcome email."""
    frontend_url = settings.frontend_url if hasattr(settings, "frontend_url") else "http://localhost:5173"
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Welcome to Creator Tools</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f7;font-family:'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f7;padding:40px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0"
               style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 50%,#a855f7 100%);padding:48px 40px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:700;letter-spacing:-0.5px;">
                🎬 Creator Tools
              </h1>
              <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:15px;">
                Your creative journey starts here
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <h2 style="margin:0 0 16px;color:#1e293b;font-size:22px;font-weight:600;">
                Welcome aboard, {user_name}! 👋
              </h2>
              <p style="margin:0 0 20px;color:#475569;font-size:15px;line-height:1.7;">
                We're thrilled to have you join <strong>Creator Tools</strong> — the all-in-one
                platform built to supercharge your content creation workflow.
              </p>
              <p style="margin:0 0 24px;color:#475569;font-size:15px;line-height:1.7;">
                Here's what you can do right away:
              </p>

              <!-- Feature list -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
                <tr>
                  <td style="padding:12px 16px;background:#f8fafc;border-radius:8px;margin-bottom:8px;">
                    <span style="color:#6366f1;font-weight:600;">🎯 Video Idea Generator</span>
                    <span style="color:#64748b;font-size:14px;"> — Get AI-powered content ideas tailored to your niche</span>
                  </td>
                </tr>
                <tr><td style="height:8px;"></td></tr>
                <tr>
                  <td style="padding:12px 16px;background:#f8fafc;border-radius:8px;">
                    <span style="color:#8b5cf6;font-weight:600;">📝 Script Generator</span>
                    <span style="color:#64748b;font-size:14px;"> — Create engaging scripts in seconds</span>
                  </td>
                </tr>
                <tr><td style="height:8px;"></td></tr>
                <tr>
                  <td style="padding:12px 16px;background:#f8fafc;border-radius:8px;">
                    <span style="color:#a855f7;font-weight:600;">📊 SEO Optimization</span>
                    <span style="color:#64748b;font-size:14px;"> — Craft titles and descriptions that rank</span>
                  </td>
                </tr>
                <tr><td style="height:8px;"></td></tr>
                <tr>
                  <td style="padding:12px 16px;background:#f8fafc;border-radius:8px;">
                    <span style="color:#6366f1;font-weight:600;">🔥 Trending Topics</span>
                    <span style="color:#64748b;font-size:14px;"> — Stay ahead with real-time trend insights</span>
                  </td>
                </tr>
              </table>

              <!-- CTA Button -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:8px 0 24px;">
                    <a href="{frontend_url}/dashboard"
                       style="display:inline-block;padding:14px 36px;background:linear-gradient(135deg,#6366f1,#8b5cf6);
                              color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;border-radius:8px;
                              box-shadow:0 4px 14px rgba(99,102,241,0.4);">
                      🚀 Go to Dashboard
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;text-align:center;">
                If you have any questions, just reply to this email — we're happy to help!
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f8fafc;padding:24px 40px;text-align:center;border-top:1px solid #e2e8f0;">
              <p style="margin:0;color:#94a3b8;font-size:12px;">
                &copy; 2026 Creator Tools. All rights reserved.
              </p>
              <p style="margin:6px 0 0;color:#94a3b8;font-size:12px;">
                You received this email because you signed up at Creator Tools.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
