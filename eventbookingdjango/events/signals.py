# events/signals.py

from django.db.models.signals import post_migrate, pre_save, post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Tag, Event, Notification, Ticket, Review, ChatMessage, EventTrendingLog, Payment, DiscountCode, UserNotification
from django.db import transaction
from django.db.models import F
from django.utils import timezone


# Tự động tạo thông báo khi sự kiện được cập nhật
@receiver(post_save, sender=Event)
def create_notification_for_event_update(sender, instance, created, **kwargs):
    """Tạo thông báo khi sự kiện được cập nhật."""
    if not created:  # Chỉ chạy khi sự kiện được cập nhật
        with transaction.atomic():
            # Tạo một thông báo duy nhất cho sự kiện
            notification = Notification.objects.create(
                event=instance,
                title=f"Cập nhật sự kiện: {instance.title}",
                message=f"Sự kiện '{instance.title}' đã được cập nhật.",
                notification_type='update'
            )
            # Lấy danh sách user có vé cho sự kiện
            ticket_owners = Ticket.objects.filter(event=instance).select_related('user').values_list('user', flat=True).distinct()
            # Tạo UserNotification cho từng user
            user_notifications = [
                UserNotification(user_id=user_id, notification=notification)
                for user_id in ticket_owners
            ]
            UserNotification.objects.bulk_create(user_notifications)


# Tự động tạo UserNotification khi Notification được tạo thủ công
@receiver(post_save, sender=Notification)
def create_usernotification_for_manual_notification(sender, instance, created, **kwargs):
    if created:
        with transaction.atomic():
            User = get_user_model()
            if instance.event:
                # Lấy user có vé sự kiện
                ticket_owners = Ticket.objects.filter(event=instance.event).select_related('user').values_list('user', flat=True).distinct()
            else:
                # Nếu không có event, lấy tất cả user
                ticket_owners = User.objects.all().values_list('id', flat=True)

            user_notifications = [
                UserNotification(user_id=user_id, notification=instance)
                for user_id in ticket_owners
            ]
            UserNotification.objects.bulk_create(user_notifications)


# Tạo tag và superuser mặc định sau khi migrate
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
    # Tạo Tag objects nếu chưa tồn tại
    for tag_name in default_tags:
        Tag.objects.get_or_create(name=tag_name)
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
def update_user_total_spent(sender, instance, created, **kwargs):
    with transaction.atomic():
        user = instance.user
        if created:
            # Nếu là tạo mới và thanh toán thành công
            if instance.status:
                user.total_spent += instance.amount
                user.save(update_fields=['total_spent'])
        else:
            # Nếu là cập nhật
            old_payment = Payment.objects.get(pk=instance.pk)
            if old_payment.status != instance.status:
                if instance.status:
                    # Từ chưa thanh toán sang thanh toán thành công
                    user.total_spent += instance.amount
                else:
                    # Từ thanh toán thành công sang chưa thanh toán
                    user.total_spent -= old_payment.amount
                user.save(update_fields=['total_spent'])
            elif instance.status and old_payment.amount != instance.amount:
                # Nếu đã thanh toán và amount thay đổi
                user.total_spent = user.total_spent - old_payment.amount + instance.amount
                user.save(update_fields=['total_spent'])


# Signal để cập nhật is_active của Event trước khi lưu
@receiver(pre_save, sender=Event)
def update_event_status(sender, instance, **kwargs):
    if instance.end_time < timezone.now():
        instance.is_active = False


# Signal để cập nhật is_active của DiscountCode trước khi lưu
@receiver(pre_save, sender=DiscountCode)
def update_discount_code_status(sender, instance, **kwargs):
    # Cập nhật trạng thái is_active dựa trên is_valid
    instance.is_active = instance.is_valid()


# Signal để cập nhật sold_tickets và EventTrendingLog khi Ticket được lưu
@receiver(post_save, sender=Ticket)
def update_sold_tickets_on_save(sender, instance, created, **kwargs):
    with transaction.atomic():
        event = instance.event
        trending_log, _ = EventTrendingLog.objects.get_or_create(event=event)

        if created and instance.is_paid:
            # Nếu tạo mới và đã thanh toán
            Event.objects.filter(pk=event.pk).update(
                sold_tickets=F('sold_tickets') + 1
            )
            trending_log.total_revenue += event.ticket_price
        elif not created:
            # Nếu là cập nhật
            old = Ticket.objects.get(pk=instance.pk)
            if not old.is_paid and instance.is_paid:
                # Từ chưa thanh toán sang thanh toán thành công
                Event.objects.filter(pk=event.pk).update(
                    sold_tickets=F('sold_tickets') + 1
                )
                trending_log.total_revenue += event.ticket_price
            elif old.is_paid and not instance.is_paid:
                # Từ thanh toán thành công sang chưa thanh toán
                Event.objects.filter(pk=event.pk).update(
                    sold_tickets=F('sold_tickets') - 1
                )
                trending_log.total_revenue -= event.ticket_price

        # Lưu thay đổi cho trending_log và tính toán score
        trending_log.save()
        trending_log.calculate_score()


# Signal để cập nhật sold_tickets và EventTrendingLog khi Ticket bị xóa
@receiver(post_delete, sender=Ticket)
def update_sold_tickets_on_delete(sender, instance, **kwargs):
    with transaction.atomic():
        event = instance.event
        # Đếm số vé đã thanh toán
        sold_tickets = event.tickets.filter(is_paid=True).count()
        event.sold_tickets = sold_tickets
        event.save(update_fields=['sold_tickets'])

        # Cập nhật EventTrendingLog
        trending_log, _ = EventTrendingLog.objects.get_or_create(event=event)
        if instance.is_paid:
            trending_log.total_revenue -= event.ticket_price
            trending_log.save()
            trending_log.calculate_score()


# Signal để tự động tạo EventTrendingLog khi tạo Event mới
@receiver(post_save, sender=Event)
def create_event_trending_log(sender, instance, created, **kwargs):
    if created:
        EventTrendingLog.objects.create(event=instance)