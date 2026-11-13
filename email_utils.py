import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# Global memory storage for latest verification links (useful for testing/dev review)
LATEST_VERIFICATION_LINKS = {}

def get_serializer(secret_key):
    salt = os.environ.get('SECURITY_PASSWORD_SALT', 'ogun-lis-verification-salt')
    return URLSafeTimedSerializer(secret_key), salt

def generate_verification_token(email, secret_key):
    serializer, salt = get_serializer(secret_key)
    return serializer.dumps(email, salt=salt)

def confirm_verification_token(token, secret_key, expiration=86400):
    serializer, salt = get_serializer(secret_key)
    try:
        email = serializer.loads(token, salt=salt, max_age=expiration)
        return email
    except (SignatureExpired, BadSignature):
        return None

def send_verification_email(to_email, full_name, verification_url):
    """
    Sends an account verification email via SMTP if configured,
    or logs the activation link to the console/test logger for development.
    """
    LATEST_VERIFICATION_LINKS[to_email] = verification_url

    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    smtp_sender = os.environ.get('MAIL_DEFAULT_SENDER', smtp_user or 'noreply@ogunland.gov.ng')

    subject = "Verify Your Account | Ogun Land Administration System"

    # Plain text version
    text_content = f"""Hello {full_name},

Thank you for registering on the Ogun Land Administration System (OLAS).

Please click or copy the link below to verify your email and activate your account:
{verification_url}

This link will expire in 24 hours.

If you did not request this registration, please ignore this email.

Best regards,
Ogun State Land Administration Bureau
"""

    # HTML version
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 30px auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; }}
        .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: #ffffff; padding: 24px; text-align: center; }}
        .content {{ padding: 30px 24px; color: #334155; line-height: 1.6; }}
        .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
        .footer {{ padding: 16px 24px; background: #f1f5f9; font-size: 12px; color: #64748b; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0; font-size: 20px;">Ogun Land Administration System</h2>
            <p style="margin: 4px 0 0; font-size: 13px; opacity: 0.9;">Account Email Verification</p>
        </div>
        <div class="content">
            <p>Hello <strong>{full_name}</strong>,</p>
            <p>Welcome to the <strong>Ogun Land Administration System (OLAS)</strong>. To activate your account and gain access to the cadastral map and search portal, please verify your email address:</p>
            <div style="text-align: center;">
                <a href="{verification_url}" class="btn" target="_blank">Verify Email Address</a>
            </div>
            <p style="font-size: 13px; color: #64748b;">Or copy and paste this URL into your browser:<br>
            <a href="{verification_url}" style="color: #2563eb; word-break: break-all;">{verification_url}</a></p>
            <p style="font-size: 12px; color: #94a3b8; margin-top: 24px;">Note: This link will expire in 24 hours.</p>
        </div>
        <div class="footer">
            &copy; Ogun State Land Administration Bureau &middot; Bureau of Lands & Survey
        </div>
    </div>
</body>
</html>"""

    # If SMTP is configured, attempt sending live email
    if smtp_server and smtp_user and smtp_password:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"Ogun Land Administration <{smtp_sender}>"
            msg['To'] = to_email

            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_sender, [to_email], msg.as_string())

            print(f"[SMTP SUCCESS] Verification email sent to {to_email}")
            return {"success": True, "method": "smtp", "url": verification_url}
        except Exception as e:
            print(f"[SMTP ERROR] Failed to send email via SMTP ({e}). Falling back to dev logger.")

    # Development fallback
    print(f"\n[DEV MAIL DISPATCHER] To: {to_email}")
    print(f"[DEV MAIL DISPATCHER] Verification URL: {verification_url}\n")
    return {"success": True, "method": "console", "url": verification_url}
