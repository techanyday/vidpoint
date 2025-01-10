"""Dashboard routes for VidPoint."""
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models.database import get_db
import json

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/')
@login_required
def index():
    """Display user dashboard."""
    db = get_db()
    
    # Get user's recent transactions
    transactions = db.get_user_transactions(current_user.id, limit=5)
    
    # Get notification preferences
    notification_preferences = db.get_notification_preferences(current_user.id)
    
    # Get recent notifications
    notifications = db.get_notification_history(current_user.id, limit=5)
    
    # Calculate subscription status
    subscription = current_user.subscription
    if subscription:
        end_date = subscription.get('end_date')
        if end_date:
            days_left = (end_date - datetime.now()).days
            subscription['days_left'] = days_left
    
    # Get user stats
    stats = db.get_user_stats(current_user.id)
    stats['total_processing_time'] = format_processing_time(
        stats.get('total_processing_time', 0)
    )
    
    return render_template('dashboard.html',
                         user=current_user,
                         transactions=transactions,
                         notifications=notifications,
                         notification_preferences=notification_preferences,
                         stats=stats,
                         has_more_notifications=len(notifications) == 5,
                         current_page=1)

@bp.route('/settings', methods=['POST'])
@login_required
def update_settings():
    """Update user settings."""
    db = get_db()
    
    # Get notification preferences from form
    notification_preferences = {
        'subscription_expiry': bool(request.form.get('notification_preferences.subscription_expiry')),
        'low_credits': bool(request.form.get('notification_preferences.low_credits')),
        'payment_confirmation': bool(request.form.get('notification_preferences.payment_confirmation')),
        'export_complete': bool(request.form.get('notification_preferences.export_complete')),
        'promotional': bool(request.form.get('notification_preferences.promotional')),
        'email_digest': request.form.get('notification_preferences.email_digest', 'daily')
    }
    
    # Update user settings
    success = db.update_user_settings(
        current_user.id,
        {
            'name': request.form.get('name'),
            'notification_preferences': notification_preferences
        }
    )
    
    if success:
        flash('Settings updated successfully!', 'success')
    else:
        flash('Failed to update settings. Please try again.', 'error')
    
    return redirect(url_for('dashboard.index'))

@bp.route('/notifications')
@login_required
def notifications():
    """Display notification history with pagination."""
    db = get_db()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    skip = (page - 1) * per_page
    
    notifications = db.get_notification_history(
        current_user.id,
        limit=per_page + 1,  # Get one extra to check if there are more
        skip=skip
    )
    
    has_more = len(notifications) > per_page
    if has_more:
        notifications = notifications[:-1]  # Remove the extra notification
    
    if request.headers.get('HX-Request'):
        # If it's an HTMX request, return just the notification list
        return render_template('partials/notification_list.html',
                             notifications=notifications,
                             has_more=has_more,
                             current_page=page)
    
    return render_template('notifications.html',
                         notifications=notifications,
                         has_more=has_more,
                         current_page=page)

def format_processing_time(seconds):
    """Format processing time in seconds to human readable string."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"
