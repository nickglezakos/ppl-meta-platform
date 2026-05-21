from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthorityMailSettings:
    server: str
    port: int
    username: str
    password: str
    from_email: str
    from_name: str
    starttls: bool
    ssl_tls: bool
    use_credentials: bool
    public_base_url: str


@dataclass(frozen=True)
class InvitationEmailDeliveryResult:
    attempted: bool
    delivered: bool
    message: str


def _truthy(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_mail_settings() -> AuthorityMailSettings | None:
    server = os.getenv("MAIL_SERVER", "").strip()
    from_email = os.getenv("MAIL_FROM", "").strip()
    public_base_url = os.getenv("AUTHORITY_PUBLIC_BASE_URL", "").strip() or os.getenv("AUTHORITY_BASE_URL", "").strip()
    if not server or not from_email or not public_base_url:
        return None

    return AuthorityMailSettings(
        server=server,
        port=int(os.getenv("MAIL_PORT", "587").strip() or "587"),
        username=os.getenv("MAIL_USERNAME", "").strip(),
        password=os.getenv("MAIL_PASSWORD", "").strip(),
        from_email=from_email,
        from_name=os.getenv("MAIL_FROM_NAME", "PPL Meta Authority").strip() or "PPL Meta Authority",
        starttls=_truthy(os.getenv("MAIL_STARTTLS", "true"), default=True),
        ssl_tls=_truthy(os.getenv("MAIL_SSL_TLS", "false"), default=False),
        use_credentials=_truthy(os.getenv("USE_CREDENTIALS", "true"), default=True),
        public_base_url=public_base_url.rstrip("/"),
    )


def send_invitation_email(invitation: dict[str, object], issuer_email: str | None = None) -> InvitationEmailDeliveryResult:
    settings = get_mail_settings()
    if settings is None:
        logger.info("Authority mail settings are incomplete; skipping invitation email delivery")
        return InvitationEmailDeliveryResult(
            attempted=False,
            delivered=False,
            message="Email delivery skipped because MAIL_* settings or authority base URL are not configured.",
        )

    invitee_email = str(invitation.get("email") or "").strip()
    invitation_token = str(invitation.get("invitation_token") or "").strip()
    role_name = str(invitation.get("role_name") or "user").strip()
    if not invitee_email or not invitation_token:
        logger.warning("Invitation email skipped because invitation payload is incomplete")
        return InvitationEmailDeliveryResult(
            attempted=False,
            delivered=False,
            message="Email delivery skipped because the invitation payload is incomplete.",
        )

    accept_url = f"{settings.public_base_url}/admin?view=session&invitation_token={invitation_token}"
    issuer_line = f"This invitation was issued by {issuer_email}.\n\n" if issuer_email else ""
    subject = f"PPL Meta Authority invitation for {role_name} access"
    text_body = (
        f"You have been invited to PPL Meta Authority as a {role_name}.\n\n"
        f"{issuer_line}"
        f"Open this link to accept the invitation:\n{accept_url}\n\n"
        f"If the form does not prefill automatically, use this invitation token:\n{invitation_token}\n"
    )
    html_body = (
        f"<p>You have been invited to <strong>PPL Meta Authority</strong> as a <strong>{role_name}</strong>.</p>"
        f"<p>{issuer_line.strip()}</p>" if issuer_line else "<p></p>"
    ) + (
        f"<p><a href=\"{accept_url}\">Open the invitation page</a></p>"
        f"<p>If the form does not prefill automatically, use this token:</p>"
        f"<p><code>{invitation_token}</code></p>"
    )

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{settings.from_name} <{settings.from_email}>"
    message["To"] = invitee_email
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        if settings.ssl_tls:
            with smtplib.SMTP_SSL(settings.server, settings.port) as server:
                if settings.use_credentials:
                    server.login(settings.username, settings.password)
                server.sendmail(settings.from_email, [invitee_email], message.as_string())
        else:
            with smtplib.SMTP(settings.server, settings.port) as server:
                if settings.starttls:
                    server.starttls()
                if settings.use_credentials:
                    server.login(settings.username, settings.password)
                server.sendmail(settings.from_email, [invitee_email], message.as_string())
        logger.info("Invitation email sent to %s", invitee_email)
        return InvitationEmailDeliveryResult(
            attempted=True,
            delivered=True,
            message=f"Invitation email sent to {invitee_email}.",
        )
    except (OSError, ValueError, smtplib.SMTPException):
        logger.exception("Failed to send authority invitation email to %s", invitee_email)
        return InvitationEmailDeliveryResult(
            attempted=True,
            delivered=False,
            message=f"Failed to send invitation email to {invitee_email}.",
        )