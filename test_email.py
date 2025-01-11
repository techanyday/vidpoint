"""Test email functionality."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_test_email():
    """Send a test email."""
    # Email settings
    smtp_server = 'mail.tekstreetz.com'
    smtp_port = 465
    smtp_username = 'support@tekstreetz.com'
    smtp_password = 'Pkmensah100%'
    from_email = 'support@tekstreetz.com'
    to_email = 'support@tekstreetz.com'
    
    # Create message
    message = MIMEMultipart('alternative')
    message['Subject'] = 'VidPoint Test Email'
    message['From'] = from_email
    message['To'] = to_email
    
    html_content = '''
    <html>
    <body>
        <h1>Test Email</h1>
        <p>This is a test email from VidPoint.</p>
        <p>If you received this, the email system is working correctly!</p>
    </body>
    </html>
    '''
    
    html_part = MIMEText(html_content, 'html')
    message.attach(html_part)
    
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(message)
            print("Test email sent successfully!")
            return True
    except Exception as e:
        print(f"Failed to send test email: {str(e)}")
        return False

if __name__ == '__main__':
    send_test_email()
