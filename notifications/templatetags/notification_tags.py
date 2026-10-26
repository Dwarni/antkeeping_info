from django import template

from notifications.models import Notification

register = template.Library()


@register.simple_tag
def get_unread_notification_count(user):
    """Return count of unread notifications for authenticated user."""
    if not user or not user.is_authenticated:
        return 0
    return Notification.objects.filter(recipient=user, read_at__isnull=True).count()


@register.inclusion_tag("notifications/snippets/badge.html")
def notification_badge(user):
    """Render the notification badge element."""
    count = 0
    if user and user.is_authenticated:
        count = Notification.objects.filter(
            recipient=user, read_at__isnull=True
        ).count()
    return {"unread_count": count, "user": user}


@register.inclusion_tag("notifications/snippets/notification_item.html")
def render_notification_item(notification):
    """Render a single notification card/item."""
    title, message = notification.title_and_message
    return {
        "notification": notification,
        "title": title,
        "message": message,
    }
