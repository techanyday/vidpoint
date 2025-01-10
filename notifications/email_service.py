"""Email service for sending notifications."""
from typing import Optional, List, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import os
from datetime import datetime, timedelta
from flask import current_app, render_template_string, url_for

class EmailService:
    """Email service for sending notifications."""
    
    def __init__(self):
        """Initialize email service with configuration."""
        self.smtp_server = os.getenv('SMTP_SERVER', 'mail.tekstreetz.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '465'))
        self.smtp_username = os.getenv('SMTP_USERNAME', 'support@tekstreetz.com')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', 'support@tekstreetz.com')
        self.use_ssl = os.getenv('SMTP_USE_SSL', 'true').lower() == 'true'
    
    def _create_message(self, to_email: str, subject: str, html_content: str) -> MIMEMultipart:
        """Create email message with HTML content."""
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = self.from_email
        message['To'] = to_email
        
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)
        
        return message
    
    def send_email(self, to_email: str, subject: str, template: str, context: Dict) -> bool:
        """Send email using template and context."""
        try:
            html_content = render_template_string(template, **context)
            message = self._create_message(to_email, subject, html_content)
            
            if self.use_ssl:
                smtp_class = smtplib.SMTP_SSL
            else:
                smtp_class = smtplib.SMTP
            
            with smtp_class(self.smtp_server, self.smtp_port) as server:
                if not self.use_ssl:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            current_app.logger.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_payment_success(self, to_email: str, plan_name: str, amount: float) -> bool:
        """Send payment success notification."""
        template = """
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Payment Successful!</h2>
                <p>Thank you for your payment. Your transaction was successful.</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Transaction Details</h3>
                    <p><strong>Plan:</strong> {{ plan_name }}</p>
                    <p><strong>Amount:</strong> GHS {{ "%.2f"|format(amount/100) }}</p>
                    <p><strong>Date:</strong> {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}</p>
                </div>
                
                <p>Your account has been updated with the new features.</p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p style="font-size: 0.9em; color: #666;">
                        If you have any questions, please don't hesitate to contact our support team.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        context = {
            'plan_name': plan_name,
            'amount': amount,
            'datetime': datetime
        }
        
        return self.send_email(
            to_email,
            "Payment Successful - VidPoint",
            template,
            context
        )
    
    def send_subscription_expiring(self, to_email: str, days_left: int, plan_name: str) -> bool:
        """Send subscription expiring notification."""
        template = """
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Subscription Expiring Soon</h2>
                
                <p>Your VidPoint {{ plan_name }} subscription will expire in {{ days_left }} days.</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Subscription Details</h3>
                    <p><strong>Plan:</strong> {{ plan_name }}</p>
                    <p><strong>Expires:</strong> {{ (datetime.now().date() + timedelta(days=days_left)).strftime('%Y-%m-%d') }}</p>
                </div>
                
                <p>To ensure uninterrupted access to VidPoint features, please renew your subscription before it expires.</p>
                
                <div style="margin: 30px 0;">
                    <a href="{{ renewal_url }}" style="background: #3498db; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px;">
                        Renew Subscription
                    </a>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p style="font-size: 0.9em; color: #666;">
                        If you have any questions, please don't hesitate to contact our support team.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        context = {
            'plan_name': plan_name,
            'days_left': days_left,
            'datetime': datetime,
            'timedelta': timedelta,
            'renewal_url': url_for('payments.checkout', plan=plan_name.lower(), _external=True)
        }
        
        return self.send_email(
            to_email,
            "Your VidPoint Subscription is Expiring Soon",
            template,
            context
        )
    
    def send_low_credits_notification(self, to_email: str, credits_left: int) -> bool:
        """Send low credits notification."""
        template = """
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Low Credits Alert</h2>
                
                <p>You have {{ credits_left }} credits remaining in your VidPoint account.</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Available Credit Packages</h3>
                    <p>• 500 Credits - GHS 5.00</p>
                    <p>• 1000 Credits - GHS 10.00</p>
                </div>
                
                <p>To continue using VidPoint's features without interruption, please purchase additional credits.</p>
                
                <div style="margin: 30px 0;">
                    <a href="{{ credits_url }}" style="background: #3498db; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px;">
                        Buy Credits
                    </a>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p style="font-size: 0.9em; color: #666;">
                        If you have any questions, please don't hesitate to contact our support team.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        context = {
            'credits_left': credits_left,
            'credits_url': url_for('payments.checkout', plan='credits-500', _external=True)
        }
        
        return self.send_email(
            to_email,
            "Low Credits Alert - VidPoint",
            template,
            context
        )
