import os
import json
import django
from datetime import datetime
from django.utils.timezone import make_aware
from django.db import transaction

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventbookingdjango.settings')
django.setup()

# Import các model từ app events
from events.models import User, Event, Tag, Ticket, Payment, Review, DiscountCode, Notification, ChatMessage, EventTrendingLog


def load_dummy_data():
    # Đọc file JSON
    with open('dummy_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Nhập dữ liệu cho User
    print("Đang nhập dữ liệu cho User...")
    for user_data in data.get('users', []):
        if User.objects.filter(username=user_data['username']).exists():
            print(f"User {user_data['username']} đã tồn tại, bỏ qua...")
            continue
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            role=user_data['role'],
            phone=user_data.get('phone', None),
            total_spent=user_data.get('total_spent', 0),
            is_active=user_data.get('is_active', True),
            is_staff=user_data.get('is_staff', False),
            is_superuser=user_data.get('is_superuser', False)
        )
        user.set_password(user_data['password'])
        user.save()
        print(f"Đã tạo user: {user.username}")

    # 2. Nhập dữ liệu cho Tag
    print("\nĐang nhập dữ liệu cho Tag...")
    for tag_data in data.get('tags', []):
        if Tag.objects.filter(name=tag_data['name']).exists():
            print(f"Tag {tag_data['name']} đã tồn tại, bỏ qua...")
            continue
        tag = Tag(name=tag_data['name'])
        tag.save()
        print(f"Đã tạo tag: {tag.name}")

    # 3. Nhập dữ liệu cho Event
    print("\nĐang nhập dữ liệu cho Event...")
    for event_data in data.get('events', []):
        if Event.objects.filter(title=event_data['title']).exists():
            print(f"Event {event_data['title']} đã tồn tại, bỏ qua...")
            continue
        try:
            organizer = User.objects.get(username=event_data['organizer'])
            if organizer.role != 'organizer':
                print(f"User {event_data['organizer']} không phải organizer, bỏ qua event {event_data['title']}...")
                continue
        except User.DoesNotExist:
            print(f"Organizer {event_data['organizer']} không tồn tại, bỏ qua event {event_data['title']}...")
            continue
        start_time = make_aware(datetime.strptime(event_data['start_time'], '%Y-%m-%dT%H:%M:%S'))
        end_time = make_aware(datetime.strptime(event_data['end_time'], '%Y-%m-%dT%H:%M:%S'))
        event = Event(
            title=event_data['title'],
            description=event_data['description'],
            category=event_data['category'],
            start_time=start_time,
            end_time=end_time,
            location=event_data['location'],
            latitude=event_data['latitude'],
            longitude=event_data['longitude'],
            organizer=organizer,
            ticket_price=event_data['ticket_price'],
            total_tickets=event_data['total_tickets'],
            sold_tickets=event_data.get('sold_tickets', 0),
            is_active=event_data.get('is_active', True)
        )
        event.save()
        # Thêm tags vào event
        for tag_name in event_data.get('tags', []):
            try:
                tag = Tag.objects.get(name=tag_name)
                event.tags.add(tag)
            except Tag.DoesNotExist:
                print(f"Tag {tag_name} không tồn tại, bỏ qua tag này cho event {event.title}...")
        event.save()
        print(f"Đã tạo event: {event.title}")

    # 4. Nhập dữ liệu cho DiscountCode
    print("\nĐang nhập dữ liệu cho DiscountCode...")
    for discount_data in data.get('discount_codes', []):
        if DiscountCode.objects.filter(code=discount_data['code']).exists():
            print(f"DiscountCode {discount_data['code']} đã tồn tại, bỏ qua...")
            continue
        valid_from = make_aware(datetime.strptime(discount_data['valid_from'], '%Y-%m-%dT%H:%M:%S'))
        valid_to = make_aware(datetime.strptime(discount_data['valid_to'], '%Y-%m-%dT%H:%M:%S'))
        discount = DiscountCode(
            code=discount_data['code'],
            discount_percentage=discount_data['discount_percentage'],
            user_group=discount_data['user_group'],
            is_active=discount_data.get('is_active', True),
            valid_from=valid_from,
            valid_to=valid_to,
            max_uses=discount_data.get('max_uses', None),
            used_count=discount_data.get('used_count', 0)
        )
        discount.save()
        print(f"Đã tạo discount code: {discount.code}")

    # 5. Nhập dữ liệu cho Ticket
    print("\nĐang nhập dữ liệu cho Ticket...")
    for ticket_data in data.get('tickets', []):
        try:
            event = Event.objects.get(title=ticket_data['event'])
            user = User.objects.get(username=ticket_data['user'])
        except (Event.DoesNotExist, User.DoesNotExist) as e:
            print(f"Event {ticket_data['event']} hoặc User {ticket_data['user']} không tồn tại, bỏ qua ticket...")
            continue
        if event.tickets.count() >= event.total_tickets:
            print(f"Event {event.title} đã hết vé, bỏ qua ticket...")
            continue
        if Ticket.objects.filter(qr_code=ticket_data['qr_code']).exists():
            print(f"Ticket với qr_code {ticket_data['qr_code']} đã tồn tại, bỏ qua...")
            continue
        purchase_date = make_aware(datetime.strptime(ticket_data['purchase_date'], '%Y-%m-%dT%H:%M:%S')) if ticket_data.get('purchase_date') else None
        check_in_date = make_aware(datetime.strptime(ticket_data['check_in_date'], '%Y-%m-%dT%H:%M:%S')) if ticket_data.get('check_in_date') else None
        ticket = Ticket(
            event=event,
            user=user,
            qr_code=ticket_data['qr_code'],
            is_paid=ticket_data.get('is_paid', False),
            is_checked_in=ticket_data.get('is_checked_in', False),
            purchase_date=purchase_date,
            check_in_date=check_in_date
        )
        ticket.save()
        print(f"Đã tạo ticket cho user {user.username} tại event {event.title}")

    # 6. Nhập dữ liệu cho Payment
    print("\nĐang nhập dữ liệu cho Payment...")
    for payment_data in data.get('payments', []):
        try:
            user = User.objects.get(username=payment_data['user'])
            discount_code = DiscountCode.objects.get(code=payment_data['discount_code']) if payment_data.get('discount_code') else None
        except User.DoesNotExist:
            print(f"User {payment_data['user']} không tồn tại, bỏ qua payment...")
            continue
        except DiscountCode.DoesNotExist:
            print(f"DiscountCode {payment_data['discount_code']} không tồn tại, bỏ qua discount code...")
            discount_code = None
        if Payment.objects.filter(transaction_id=payment_data['transaction_id']).exists():
            print(f"Payment với transaction_id {payment_data['transaction_id']} đã tồn tại, bỏ qua...")
            continue
        paid_at = make_aware(datetime.strptime(payment_data['paid_at'], '%Y-%m-%dT%H:%M:%S')) if payment_data.get('paid_at') else None
        with transaction.atomic():
            payment = Payment(
                user=user,
                amount=payment_data['amount'],
                payment_method=payment_data['payment_method'],
                status=payment_data.get('status', False),
                transaction_id=payment_data['transaction_id'],
                paid_at=paid_at,
                discount_code=discount_code
            )
            payment.save()
            # Gắn vé vào payment (many-to-many)
            ticket_qr_codes = payment_data.get('tickets', [])
            tickets = Ticket.objects.filter(qr_code__in=ticket_qr_codes)
            payment.tickets.set(tickets)
            print(f"Đã tạo payment cho user {user.username}")

    # 7. Nhập dữ liệu cho Review
    print("\nĐang nhập dữ liệu cho Review...")
    for review_data in data.get('reviews', []):
        try:
            event = Event.objects.get(title=review_data['event'])
            user = User.objects.get(username=review_data['user'])
        except (Event.DoesNotExist, User.DoesNotExist) as e:
            print(f"Event {review_data['event']} hoặc User {review_data['user']} không tồn tại, bỏ qua review...")
            continue
        if Review.objects.filter(event=event, user=user).exists():
            print(f"Review của user {user.username} cho event {event.title} đã tồn tại, bỏ qua...")
            continue
        review = Review(
            event=event,
            user=user,
            rating=review_data['rating'],
            comment=review_data.get('comment', None)
        )
        review.save()
        print(f"Đã tạo review cho event {event.title} bởi user {user.username}")

    # 8. Nhập dữ liệu cho Notification
    print("\nĐang nhập dữ liệu cho Notification...")
    for notif_data in data.get('notifications', []):
        try:
            event = Event.objects.get(title=notif_data['event']) if notif_data.get('event') else None
        except Event.DoesNotExist:
            print(f"Event {notif_data['event']} không tồn tại, bỏ qua notification...")
            continue
        notification = Notification(
            event=event,
            title=notif_data['title'],
            message=notif_data['message'],
            notification_type=notif_data.get('notification_type', 'general'),
            is_read=notif_data.get('is_read', False)
        )
        notification.save()
        print(f"Đã tạo notification cho event {notif_data.get('event')}")

    # 9. Nhập dữ liệu cho ChatMessage
    print("\nĐang nhập dữ liệu cho ChatMessage...")
    for chat_data in data.get('chat_messages', []):
        try:
            event = Event.objects.get(title=chat_data['event'])
            sender = User.objects.get(username=chat_data['sender'])
            receiver = User.objects.get(username=chat_data['receiver'])
        except (Event.DoesNotExist, User.DoesNotExist) as e:
            print(f"Event {chat_data['event']}, Sender {chat_data['sender']} hoặc Receiver {chat_data['receiver']} không tồn tại, bỏ qua chat message...")
            continue
        # Kiểm tra is_from_organizer trước khi tạo
        is_from_organizer = chat_data.get('is_from_organizer', False)
        if is_from_organizer and sender.role != 'organizer':
            print(f"Sender {sender.username} không phải organizer, không thể đặt is_from_organizer=True, bỏ qua...")
            continue
        chat_message = ChatMessage(
            event=event,
            sender=sender,
            receiver=receiver,
            message=chat_data['message'],
            is_from_organizer=is_from_organizer,
        )
        chat_message.save()
        print(f"Đã tạo chat message trong event {event.title} bởi {sender.username}")

    # 10. Nhập dữ liệu cho EventTrendingLog
    print("\nĐang nhập dữ liệu cho EventTrendingLog...")
    for trending_data in data.get('event_trending_logs', []):
        try:
            event = Event.objects.get(title=trending_data['event'])
        except Event.DoesNotExist:
            print(f"Event {trending_data['event']} không tồn tại, bỏ qua event trending log...")
            continue
        trending_log = EventTrendingLog(
            event=event,
            view_count=trending_data.get('view_count', 0),
            ticket_sold_count=trending_data.get('ticket_sold_count', 0)
        )
        trending_log.save()
        print(f"Đã tạo event trending log cho event {event.title}")


if __name__ == '__main__':
    load_dummy_data()
