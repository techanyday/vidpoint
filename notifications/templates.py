"""Email templates for VidPoint notifications."""

# Payment Templates
PAYMENT_SUCCESS_TEMPLATE = """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #2c3e50; margin-bottom: 10px;">Payment Successful!</h1>
            <p style="font-size: 16px;">Thank you for your payment. Your transaction was successful.</p>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #2c3e50;">Transaction Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #666;">Plan:</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold;">{{ plan_name }}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Amount:</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold;">GHS {{ "%.2f"|format(amount/100) }}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Date:</td>
                    <td style="padding: 8px 0; text-align: right;">{{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Transaction ID:</td>
                    <td style="padding: 8px 0; text-align: right; font-family: monospace;">{{ transaction_id }}</td>
                </tr>
            </table>
        </div>
        
        <div style="margin: 30px 0; text-align: center;">
            <a href="{{ dashboard_url }}" style="background: #3498db; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block;">
                View Dashboard
            </a>
        </div>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
            <p style="font-size: 14px; color: #666;">
                If you have any questions about this payment, please contact our support team at support@tekstreetz.com
            </p>
        </div>
    </div>
</body>
</html>
"""

SUBSCRIPTION_EXPIRING_TEMPLATE = """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #e74c3c; margin-bottom: 10px;">Subscription Expiring Soon</h1>
            <p style="font-size: 16px;">Your VidPoint {{ plan_name }} subscription will expire in {{ days_left }} days.</p>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #2c3e50;">Subscription Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #666;">Current Plan:</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold;">{{ plan_name }}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Expiry Date:</td>
                    <td style="padding: 8px 0; text-align: right;">{{ expiry_date.strftime('%B %d, %Y') }}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Days Remaining:</td>
                    <td style="padding: 8px 0; text-align: right; color: #e74c3c; font-weight: bold;">{{ days_left }} days</td>
                </tr>
            </table>
        </div>
        
        <div style="margin: 30px 0; text-align: center;">
            <p style="margin-bottom: 20px;">Renew now to ensure uninterrupted access to VidPoint features:</p>
            <a href="{{ renewal_url }}" style="background: #27ae60; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Renew Subscription
            </a>
        </div>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
            <p style="font-size: 14px; color: #666;">
                If you have any questions about your subscription, please contact our support team at support@tekstreetz.com
            </p>
        </div>
    </div>
</body>
</html>
"""

LOW_CREDITS_TEMPLATE = """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #f39c12; margin-bottom: 10px;">Low Credits Alert</h1>
            <p style="font-size: 16px;">You have {{ credits_left }} credits remaining in your VidPoint account.</p>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #2c3e50;">Available Credit Packages</h3>
            <table style="width: 100%; border-collapse: collapse;">
                {% for package in credit_packages %}
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #eee;">
                        <span style="font-weight: bold;">{{ package.credits }} Credits</span>
                    </td>
                    <td style="padding: 12px 0; text-align: right; border-bottom: 1px solid #eee;">
                        <span style="color: #27ae60;">GHS {{ "%.2f"|format(package.price/100) }}</span>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div style="margin: 30px 0; text-align: center;">
            <p style="margin-bottom: 20px;">Purchase additional credits to continue using VidPoint's features:</p>
            <a href="{{ credits_url }}" style="background: #f39c12; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Buy Credits
            </a>
        </div>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
            <p style="font-size: 14px; color: #666;">
                If you have any questions about credits, please contact our support team at support@tekstreetz.com
            </p>
        </div>
    </div>
</body>
</html>
"""

EXPORT_COMPLETE_TEMPLATE = """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #2c3e50; margin-bottom: 10px;">Video Export Complete!</h1>
            <p style="font-size: 16px;">Your video has been successfully processed and is ready for download.</p>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #2c3e50;">Export Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #666;">Video Title:</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold;">{{ video_title }}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Duration:</td>
                    <td style="padding: 8px 0; text-align: right;">{{ duration }}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Format:</td>
                    <td style="padding: 8px 0; text-align: right;">{{ format }}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Credits Used:</td>
                    <td style="padding: 8px 0; text-align: right;">{{ credits_used }}</td>
                </tr>
            </table>
        </div>
        
        <div style="margin: 30px 0; text-align: center;">
            <a href="{{ download_url }}" style="background: #3498db; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Download Video
            </a>
        </div>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
            <p style="font-size: 14px; color: #666;">
                Your video will be available for download for the next 7 days.
                <br>
                If you have any questions, please contact our support team at support@tekstreetz.com
            </p>
        </div>
    </div>
</body>
</html>
"""
