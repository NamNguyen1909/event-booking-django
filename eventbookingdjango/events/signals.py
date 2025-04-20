# events/signals.py

from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Tag,Event,Notification,Ticket,Review,ChatMessage,EventTrendingLog,Payment,DiscountCode
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.db.models.signals import pre_save, post_save, post_delete

#tự động tạo thông báo khi sự kiện được cập nhật
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Event)
def create_notification_for_event_update(sender, instance, created, **kwargs):
    """Tạo thông báo khi sự kiện được cập nhật."""
    if not created:  # Chỉ chạy khi sự kiện được cập nhật
        tickets = Ticket.objects.filter(event=instance)
        for ticket in tickets:
            Notification.objects.create(
                event=instance,
                message=f"Sự kiện '{instance.title}' đã được cập nhật.",
                notification_type='update'
            )


@receiver(post_migrate)
def create_default_tags(sender, **kwargs):
    # Tạo các tag mặc định
    default_tags = [
        'tech', 'health', 'education', 'religious', 'charity', 'networking',
        'startup', 'career', 'family', 'kids', 'outdoor', 'indoor',
        'free', 'paid', 'food', 'drink', 'fashion', 'environment',
        'art', 'film', 'sports_fan', 'fitness', 'music_band',
        'political', 'science', 'literature', 'music'
    ]
    # Tạo superuser mặc định
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@gmail.com',
            password='123'
        )

# Signal để cập nhật total_spent của User khi Payment được lưu
@receiver(post_save, sender=Payment)
def update_user_total_spent(sender, instance, **kwargs):
    if instance.status:
        with transaction.atomic():
            user = instance.user
            user.total_spent += instance.amount
            user.save()


# Signal để cập nhật is_active của Event trước khi lưu
@receiver(pre_save, sender=Event)
def update_event_status(sender, instance, **kwargs):
    if instance.end_time < timezone.now():
        instance.is_active = False

@receiver(pre_save, sender=DiscountCode)
def update_discount_code_status(sender, instance, **kwargs):
    # Cập nhật trạng thái is_active dựa trên is_valid
    instance.is_active = instance.is_valid()

@receiver(post_save, sender=Ticket)
def update_sold_tickets_on_save(sender, instance, created, **kwargs):
    if created and instance.is_paid:
        # Nếu tạo mới và đã thanh toán
        Event.objects.filter(pk=instance.event.pk).update(
            sold_tickets=F('sold_tickets') + 1
        )
    elif not created:
        # Nếu là update và is_paid vừa chuyển từ False -> True
        old = Ticket.objects.get(pk=instance.pk)
        if not old.is_paid and instance.is_paid:
            Event.objects.filter(pk=instance.event.pk).update(
                sold_tickets=F('sold_tickets') + 1
            )


# Signal để cập nhật sold_tickets của Event khi Ticket bị xóa
@receiver(post_delete, sender=Ticket)
def update_sold_tickets_on_delete(sender, instance, **kwargs):
    with transaction.atomic():
        event = instance.event
        event.sold_tickets = event.tickets.count()  # type: ignore
        event.save()
