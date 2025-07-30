"""Email utilities using AWS SES SMTP."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import (
    MAIL_HOST,
    MAIL_PORT,
    MAIL_USERNAME,
    MAIL_PASSWORD,
    EMAIL_SENDER,
    EMAIL_SENDER_NAME,
    DEBUG_MODE,
)


def send_verification_email(to_email, verification_code):
    """Send verification email to user."""
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("WARNING: AWS SES credentials not configured. Email not sent.")
        return False

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your email for hack.sv"
    msg["From"] = f"{EMAIL_SENDER_NAME} <{EMAIL_SENDER}>"
    msg["To"] = to_email

    # Create HTML content
    html_content = f"""
    <h2>Verify your email</h2>
    <p>Your verification code is: <strong>{verification_code}</strong></p>
    <p>This code will expire in 10 minutes.</p>
    """

    # Attach HTML content
    html_part = MIMEText(html_content, "html")
    msg.attach(html_part)

    try:
        # Connect to AWS SES SMTP server
        server = smtplib.SMTP(MAIL_HOST, MAIL_PORT)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)

        # Send email
        server.send_message(msg)
        server.quit()

        if DEBUG_MODE:
            print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_admin_notification(subject, content):
    """Send notification email to admin."""
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print(
            "WARNING: AWS SES credentials not configured. Admin notification not sent."
        )
        return False

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[hack.sv Admin] {subject}"
    msg["From"] = f"{EMAIL_SENDER_NAME} <{EMAIL_SENDER}>"
    msg["To"] = EMAIL_SENDER  # Send to self

    # Attach HTML content
    html_part = MIMEText(content, "html")
    msg.attach(html_part)

    try:
        # Connect to AWS SES SMTP server
        server = smtplib.SMTP(MAIL_HOST, MAIL_PORT)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)

        # Send email
        server.send_message(msg)
        server.quit()

        if DEBUG_MODE:
            print(f"Admin notification sent to {EMAIL_SENDER}")
        return True
    except Exception as e:
        print(f"Error sending admin notification: {e}")
        return False
