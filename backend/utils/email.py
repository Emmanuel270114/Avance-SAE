import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from backend.core.config import settings

class EmailSendError(Exception):
    pass

def send_email(to_email: str, subject: str, html_body: str, from_email: Optional[str] = None):
    if not from_email:
        from_email = settings.effective_from
    if not from_email:
        raise EmailSendError("Remitente no configurado (SMTP_FROM o SMTP_USER vacío)")

    full_subject = f"{settings.SMTP_SUBJECT_PREFIX} - {subject}" if settings.SMTP_SUBJECT_PREFIX else subject

    msg = MIMEMultipart('alternative')
    msg['Subject'] = full_subject
    msg['From'] = from_email
    msg['To'] = to_email

    mime_text = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(mime_text)

    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USER and settings.SMTP_PASS:
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(from_email, [to_email], msg.as_string())
    except Exception as e:
        raise EmailSendError(f"Error enviando correo: {e}")
