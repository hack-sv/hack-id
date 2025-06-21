"""Email utilities using SendGrid."""

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from config import SENDGRID_API_KEY, EMAIL_SENDER, EMAIL_SENDER_NAME, DEBUG_MODE

def send_verification_email(to_email, verification_code):
    """Send verification email to user."""
    if not SENDGRID_API_KEY:
        print("WARNING: SendGrid API key not configured. Email not sent.")
        return False
    
    message = Mail(
        from_email=(EMAIL_SENDER, EMAIL_SENDER_NAME),
        to_emails=to_email,
        subject="Verify your email for hack.sv",
        html_content=f"""
        <h2>Verify your email</h2>
        <p>Your verification code is: <strong>{verification_code}</strong></p>
        <p>This code will expire in 10 minutes.</p>
        """
    )
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        if DEBUG_MODE:
            print(f"Email sent successfully. Status code: {response.status_code}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_admin_notification(subject, content):
    """Send notification email to admin."""
    if not SENDGRID_API_KEY:
        print("WARNING: SendGrid API key not configured. Admin notification not sent.")
        return False
    
    message = Mail(
        from_email=(EMAIL_SENDER, EMAIL_SENDER_NAME),
        to_emails=EMAIL_SENDER,  # Send to self
        subject=f"[hack.sv Admin] {subject}",
        html_content=content
    )
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        if DEBUG_MODE:
            print(f"Admin notification sent. Status code: {response.status_code}")
        return True
    except Exception as e:
        print(f"Error sending admin notification: {e}")
        return False
