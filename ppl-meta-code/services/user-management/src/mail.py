from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
import os
from dotenv import load_dotenv

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD"),
    MAIL_FROM = os.getenv("MAIL_FROM"),
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587")),
    MAIL_SERVER = os.getenv("MAIL_SERVER"),
    MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "ppl-node-meta"),
    MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "True") == "True",
    MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "False") == "True",
    USE_CREDENTIALS = os.getenv("USE_CREDENTIALS", "True") == "True",
    VALIDATE_CERTS = os.getenv("VALIDATE_CERTS", "True") == "True"
)


fast_mail = FastMail(conf)

async def send_email(subject: str, email_to: EmailStr, body: str):
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body,
        subtype="html"
    )
    await fast_mail.send_message(message)