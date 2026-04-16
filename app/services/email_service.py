import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@financeapi.com")


def is_email_configured() -> bool:
    return bool(SMTP_HOST)


def send_email(to: str, subject: str, html_body: str) -> bool:
    if not is_email_configured():
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to, msg.as_string())
        return True
    except Exception:
        return False


def send_password_reset_email(to: str, reset_url: str) -> bool:
    subject = "Reset your FinanceAPI password"
    body = f"""
    <div style="font-family:Inter,sans-serif;max-width:480px;margin:auto;padding:32px;background:#f9fafb;border-radius:12px;">
      <div style="background:#4338ca;border-radius:10px;padding:24px;text-align:center;margin-bottom:24px;">
        <h1 style="color:#fff;margin:0;font-size:22px;">FinanceAPI</h1>
      </div>
      <h2 style="color:#111827;font-size:18px;margin-bottom:8px;">Reset your password</h2>
      <p style="color:#6b7280;font-size:14px;margin-bottom:24px;">
        Click the button below to reset your password. This link expires in 1 hour.
      </p>
      <a href="{reset_url}" style="display:inline-block;background:#4338ca;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
        Reset Password
      </a>
      <p style="color:#9ca3af;font-size:12px;margin-top:24px;">
        If you didn't request this, you can safely ignore this email.
      </p>
    </div>
    """
    return send_email(to, subject, body)


def send_invite_email(to: str, invite_url: str, org_name: str, role: str) -> bool:
    subject = f"You've been invited to join {org_name} on FinanceAPI"
    body = f"""
    <div style="font-family:Inter,sans-serif;max-width:480px;margin:auto;padding:32px;background:#f9fafb;border-radius:12px;">
      <div style="background:#4338ca;border-radius:10px;padding:24px;text-align:center;margin-bottom:24px;">
        <h1 style="color:#fff;margin:0;font-size:22px;">FinanceAPI</h1>
      </div>
      <h2 style="color:#111827;font-size:18px;margin-bottom:8px;">You're invited!</h2>
      <p style="color:#6b7280;font-size:14px;margin-bottom:8px;">
        You've been invited to join <strong>{org_name}</strong> as a <strong>{role.capitalize()}</strong>.
      </p>
      <p style="color:#6b7280;font-size:14px;margin-bottom:24px;">Click the button below to accept and create your account.</p>
      <a href="{invite_url}" style="display:inline-block;background:#4338ca;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
        Accept Invitation
      </a>
    </div>
    """
    return send_email(to, subject, body)
