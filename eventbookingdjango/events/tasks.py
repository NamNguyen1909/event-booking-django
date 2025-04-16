# from celery import shared_task
from django.utils.timezone import now, timedelta
from events.models import Event, Notification


# PAUSE celery không chạy interval task trên pythonanywhere được => Cron Jobs
# @shared_task
def create_notifications_for_upcoming_events():
    """Tạo thông báo cho các sự kiện sắp diễn ra."""
    today = now().date()
    upcoming_events = Event.objects.filter(
        start_time__date__in=[today + timedelta(days=7), today + timedelta(days=1)]
    )

    for event in upcoming_events:
        # Tạo một thông báo duy nhất cho sự kiện
        Notification.objects.create(
            event=event,
            message=f"Sự kiện '{event.title}' sẽ diễn ra vào {event.start_time.date()}!",
            notification_type='reminder'
        )