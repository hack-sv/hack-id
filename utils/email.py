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


def send_magic_link_email(to_email, magic_link):
    """Send magic link email to user for passwordless authentication."""
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("WARNING: AWS SES credentials not configured. Magic link email not sent.")
        if DEBUG_MODE:
            print(f"\n==== DEBUG: Magic Link (Email not sent) ====")
            print(f"To: {to_email}")
            print(f"Magic Link: {magic_link}")
            print(f"============================================\n")
        return False

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Sign-In Link for hack.sv"
    msg["From"] = f"{EMAIL_SENDER_NAME} <{EMAIL_SENDER}>"
    msg["To"] = to_email

    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            a {{ color: #00ccff; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #00ccff; color: #fff !important; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Sign in to hack.sv</h2>
            <p>Hi there! Just click the button below to sign in to your hack.sv account.</p>
            <a href="{magic_link}" class="button">Sign In</a>
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #00ccff !important; font-size: 14px;">{magic_link}</p>
            <p><strong>This link will expire in 10 minutes.</strong></p>
            <p>If you have any questions, feel free to email <a href="mailto:team@hack.sv">team@hack.sv</a>.</p>
            <div class="footer">
                <p>If you didn't request this email, you can safely ignore it.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Create plain text version
    text_content = f"""
Sign in to hack.sv

Click this link to sign in to your hack.sv account:
{magic_link}

This link will expire in 10 minutes.

If you didn't request this email, you can safely ignore it.
    """

    # Attach both plain text and HTML versions
    text_part = MIMEText(text_content, "plain")
    html_part = MIMEText(html_content, "html")
    msg.attach(text_part)
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
            print(f"Magic link email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending magic link email: {e}")
        if DEBUG_MODE:
            print(f"\n==== DEBUG: Magic Link (Email failed) ====")
            print(f"To: {to_email}")
            print(f"Magic Link: {magic_link}")
            print(f"Error: {e}")
            print(f"==========================================\n")
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
