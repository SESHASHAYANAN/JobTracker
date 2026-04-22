"""Email Service — SMTP-based email sending for application confirmations."""
from __future__ import annotations
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional


class EmailService:
    """Sends application confirmation emails via SMTP."""

    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_pass = os.environ.get("SMTP_PASS", "")
        self.from_email = os.environ.get("SMTP_FROM", self.smtp_user)
        self.enabled = bool(self.smtp_user and self.smtp_pass)

    def is_configured(self) -> bool:
        return self.enabled

    def send_application_confirmation(
        self,
        to_email: str,
        candidate_name: str,
        company_name: str,
        role_title: str,
        apply_url: str = "",
        match_score: float = 0.0,
        method: str = "external",
    ) -> dict:
        """Send a job application confirmation email.

        Returns:
            A dict with keys: success, message, timestamp
        """
        if not self.enabled:
            return {
                "success": False,
                "message": "SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS env vars.",
                "timestamp": datetime.utcnow().isoformat(),
            }

        subject = f"✅ Application Submitted — {role_title} at {company_name}"

        html_body = f"""
        <html>
        <body style="font-family: 'Inter', -apple-system, sans-serif; max-width: 600px; margin: 0 auto; color: #1a1a2e;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px; border-radius: 16px 16px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">🚀 Application Confirmed</h1>
                <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0 0;">Your job application has been tracked</p>
            </div>
            <div style="background: #ffffff; padding: 32px; border: 1px solid #e0e0e0; border-top: none;">
                <p>Hi <strong>{candidate_name}</strong>,</p>
                <p>Your application for the following role has been recorded:</p>
                <div style="background: #f8f9ff; border-left: 4px solid #667eea; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
                    <p style="margin: 0; font-size: 18px; font-weight: 600;">{role_title}</p>
                    <p style="margin: 4px 0 0 0; color: #666;">at <strong>{company_name}</strong></p>
                </div>
                <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                    <tr>
                        <td style="padding: 8px 0; color: #888;">Method:</td>
                        <td style="padding: 8px 0; font-weight: 500;">{method.replace('_', ' ').title()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #888;">Match Score:</td>
                        <td style="padding: 8px 0; font-weight: 500;">{match_score:.0f}%</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #888;">Submitted:</td>
                        <td style="padding: 8px 0; font-weight: 500;">{datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}</td>
                    </tr>
                    {"<tr><td style='padding: 8px 0; color: #888;'>Apply Link:</td><td style='padding: 8px 0;'><a href='" + apply_url + "' style='color: #667eea;'>Open Application</a></td></tr>" if apply_url else ""}
                </table>
                <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 16px; border-radius: 8px; margin: 16px 0;">
                    <p style="margin: 0; color: #166534; font-size: 14px;">💡 <strong>Tip:</strong> Follow up on LinkedIn with the hiring manager or founders within 48 hours for best results.</p>
                </div>
                <p style="color: #888; font-size: 13px; margin-top: 24px;">— Sent by JobTracker Startup Platform</p>
            </div>
            <div style="background: #1a1a2e; padding: 16px; border-radius: 0 0 16px 16px; text-align: center;">
                <p style="color: rgba(255,255,255,0.5); font-size: 12px; margin: 0;">JobTracker • Startup Job Discovery & Application Assistant</p>
            </div>
        </body>
        </html>
        """

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Plain text fallback
            plain_text = (
                f"Application Confirmed\n\n"
                f"Hi {candidate_name},\n\n"
                f"Your application for {role_title} at {company_name} has been recorded.\n"
                f"Method: {method}\n"
                f"Match Score: {match_score:.0f}%\n"
                f"Submitted: {datetime.utcnow().isoformat()}\n"
                f"{f'Apply Link: {apply_url}' if apply_url else ''}\n\n"
                f"— JobTracker Startup Platform"
            )

            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.from_email, to_email, msg.as_string())

            return {
                "success": True,
                "message": f"Confirmation email sent to {to_email}",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }

    def send_batch_summary(
        self,
        to_email: str,
        candidate_name: str,
        applications: list[dict],
    ) -> dict:
        """Send a summary email for batch applications."""
        if not self.enabled:
            return {
                "success": False,
                "message": "SMTP not configured.",
                "timestamp": datetime.utcnow().isoformat(),
            }

        applied_count = len([a for a in applications if a.get("status") == "Applied"])
        failed_count = len([a for a in applications if a.get("status") == "Failed"])
        subject = f"📊 Batch Apply Summary — {applied_count} applications sent"

        rows = ""
        for app in applications[:50]:
            status_color = "#16a34a" if app.get("status") == "Applied" else "#dc2626"
            rows += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #f0f0f0;">{app.get('company_name', '')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #f0f0f0;">{app.get('role_title', '')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #f0f0f0; color: {status_color}; font-weight: 500;">{app.get('status', '')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #f0f0f0;">{app.get('match_score', 0):.0f}%</td>
            </tr>
            """

        html_body = f"""
        <html>
        <body style="font-family: 'Inter', -apple-system, sans-serif; max-width: 700px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #059669 0%, #0d9488 100%); padding: 32px; border-radius: 16px 16px 0 0;">
                <h1 style="color: white; margin: 0;">📊 Batch Apply Summary</h1>
                <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0 0;">{applied_count} applied • {failed_count} failed • {len(applications)} total</p>
            </div>
            <div style="background: white; padding: 24px; border: 1px solid #e0e0e0; border-top: none;">
                <p>Hi <strong>{candidate_name}</strong>,</p>
                <p>Here's a summary of your batch applications:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                    <thead>
                        <tr style="background: #f8f9ff;">
                            <th style="padding: 10px; text-align: left; font-size: 13px; color: #666;">Company</th>
                            <th style="padding: 10px; text-align: left; font-size: 13px; color: #666;">Role</th>
                            <th style="padding: 10px; text-align: left; font-size: 13px; color: #666;">Status</th>
                            <th style="padding: 10px; text-align: left; font-size: 13px; color: #666;">Match</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
            <div style="background: #1a1a2e; padding: 16px; border-radius: 0 0 16px 16px; text-align: center;">
                <p style="color: rgba(255,255,255,0.5); font-size: 12px; margin: 0;">JobTracker • Startup Job Discovery & Application Assistant</p>
            </div>
        </body>
        </html>
        """

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.from_email, to_email, msg.as_string())

            return {
                "success": True,
                "message": f"Batch summary sent to {to_email}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to send batch summary: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }


# Singleton
email_service = EmailService()
