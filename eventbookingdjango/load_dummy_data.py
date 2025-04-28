import os
import json
import django
from datetime import datetime
import django.utils.timezone as timezone
from django.db import transaction
import uuid
import qrcode
import io
import base64
from cloudinary.uploader import upload
from decimal import Decimal

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventbookingdjango.settings')
django.setup()

# Import các model từ app bem
from events.models import User, Event, Tag, Ticket, Payment, Review, DiscountCode, Notification, ChatMessage, EventTrendingLog, UserNotification


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
        start_time = timezone.make_aware(datetime.strptime(event_data['start_time'], '%Y-%m-%dT%H:%M:%S'))
        end_time = timezone.make_aware(datetime.strptime(event_data['end_time'], '%Y-%m-%dT%H:%M:%S'))
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
            sold_tickets=0,  # Ban đầu chưa có vé nào được bán
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
        valid_from = timezone.make_aware(datetime.strptime(discount_data['valid_from'], '%Y-%m-%dT%H:%M:%S'))
        valid_to = timezone.make_aware(datetime.strptime(discount_data['valid_to'], '%Y-%m-%dT%H:%M:%S'))
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
    tickets_map = {}  # Lưu trữ vé để sử dụng trong Payment
    for ticket_data in data.get('tickets', []):
        try:
            event = Event.objects.get(title=ticket_data['event'])
            user = User.objects.get(username=ticket_data['user'])
        except (Event.DoesNotExist, User.DoesNotExist) as e:
            print(f"Event {ticket_data['event']} hoặc User {ticket_data['user']} không tồn tại, bỏ qua ticket...")
            continue
        if event.tickets.filter(is_paid=True).count() >= event.total_tickets:
            print(f"Event {event.title} đã hết vé, bỏ qua ticket...")
            continue

        # Tạo QR code
        qr_code = str(uuid.uuid4())
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_code)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_image = buffer.getvalue()

        # Tải lên Cloudinary
        try:
            upload_result = upload(qr_code_image, resource_type="image", folder="qr_codes")
            qr_code_url = upload_result['secure_url']
        except Exception as e:
            print(f"Lỗi khi tải QR code lên Cloudinary: {e}, bỏ qua ticket...")
            continue

        ticket = Ticket(
            event=event,
            user=user,
            qr_code=qr_code_url,
            is_paid=ticket_data.get('is_paid', False),
            is_checked_in=ticket_data.get('is_checked_in', False)
        )
        ticket.save()
        if ticket.is_paid:
            event.sold_tickets += 1
            event.save(update_fields=['sold_tickets'])
        print(f"Đã tạo ticket cho user {user.username} tại event {event.title}")
        tickets_map[f"{event.title}_{user.username}_{ticket_data['is_paid']}_{ticket_data['is_checked_in']}"] = ticket

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

        # Lấy danh sách vé từ ticket_keys
        ticket_keys = payment_data.get('tickets', [])
        tickets = []
        for i in range(0, len(ticket_keys), 4):
            event_title = ticket_keys[i]
            user_name = ticket_keys[i + 1]
            is_paid = ticket_keys[i + 2]
            is_checked_in = ticket_keys[i + 3]
            key = f"{event_title}_{user_name}_{is_paid}_{is_checked_in}"
            if key in tickets_map:
                tickets.append(tickets_map[key])
            else:
                print(f"Không tìm thấy ticket cho {key}, bỏ qua...")

        if not tickets:
            print(f"Không có vé hợp lệ cho payment của user {user.username}, bỏ qua payment...")
            continue

        # Tính toán lại amount để đảm bảo nhất quán
        total_amount = sum(ticket.event.ticket_price for ticket in tickets)
        amount_before_discount = total_amount  # Tính toán để kiểm tra, nhưng không lưu
        discount_applied = 0  # Tính toán để kiểm tra, nhưng không lưu
        final_amount = total_amount

        if discount_code:
            # Kiểm tra mã giảm giá hợp lệ
            if (discount_code.is_active and
                    discount_code.valid_from <= timezone.now() <= discount_code.valid_to and
                    (discount_code.max_uses is None or discount_code.used_count < discount_code.max_uses)):
                discount_applied = Decimal(str((total_amount * discount_code.discount_percentage) / 100))
                final_amount = total_amount - discount_applied
                discount_code.used_count += 1
                discount_code.save(update_fields=['used_count'])
            else:
                print(f"Mã giảm giá {discount_code.code} không hợp lệ hoặc đã hết lượt sử dụng, bỏ qua áp dụng mã...")
                discount_code = None
                final_amount = total_amount

        # Chuyển payment_data['amount'] thành Decimal để so sánh
        payment_amount_from_data = Decimal(str(payment_data['amount']))

        # So sánh amount tính toán với amount trong dữ liệu
        if abs(final_amount - payment_amount_from_data) > Decimal('0.01'):
            print(f"Cảnh báo: Amount trong dữ liệu ({payment_amount_from_data}) không khớp với tính toán ({final_amount}) cho user {user.username}, sử dụng amount tính toán...")
            payment_amount = final_amount
        else:
            payment_amount = payment_amount_from_data

        # Kiểm tra trạng thái payment và vé
        payment_status = payment_data.get('status', False)
        paid_at = timezone.make_aware(datetime.strptime(payment_data['paid_at'], '%Y-%m-%dT%H:%M:%S')) if payment_data.get('paid_at') else None

        if payment_status:
            # Nếu payment có status=True, đảm bảo tất cả vé liên quan cũng có is_paid=True
            for ticket in tickets:
                if not ticket.is_paid:
                    print(f"Vé cho event {ticket.event.title} của user {user.username} chưa được thanh toán (is_paid=False), nhưng payment có status=True, điều chỉnh ticket...")
                    ticket.is_paid = True
                    ticket.save()
                    # Cập nhật sold_tickets của event
                    ticket.event.sold_tickets += 1
                    ticket.event.save(update_fields=['sold_tickets'])
        else:
            # Nếu payment có status=False, đảm bảo tất cả vé liên quan có is_paid=False
            for ticket in tickets:
                if ticket.is_paid:
                    print(f"Vé cho event {ticket.event.title} của user {user.username} đã được thanh toán (is_paid=True), nhưng payment có status=False, điều chỉnh ticket...")
                    ticket.is_paid = False
                    ticket.save()
                    # Cập nhật sold_tickets của event
                    ticket.event.sold_tickets -= 1
                    ticket.event.save(update_fields=['sold_tickets'])

        with transaction.atomic():
            payment = Payment(
                user=user,
                amount=payment_amount,
                payment_method=payment_data['payment_method'],
                status=payment_status,
                transaction_id=payment_data['transaction_id'],
                paid_at=paid_at,
                discount_code=discount_code
            )
            payment.save()
            payment.tickets.set(tickets)

            # Cập nhật total_spent của user nếu payment có status=True
            if payment.status:
                user.total_spent += payment.amount
                user.save(update_fields=['total_spent'])

            print(f"Đã tạo payment cho user {user.username} với transaction_id {payment.transaction_id}")

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
            notification_type=notif_data.get('notification_type', 'reminder')
        )
        notification.save()
        # Tạo UserNotification cho tất cả người dùng có vé của sự kiện
        if event:
            ticket_owners = Ticket.objects.filter(event=event).values_list('user', flat=True).distinct()
            for user_id in ticket_owners:
                user = User.objects.get(id=user_id)
                UserNotification.objects.create(
                    user=user,
                    notification=notification,
                    is_read=False
                )
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
        is_from_organizer = chat_data.get('is_from_organizer', False)
        if is_from_organizer and sender.role != 'organizer':
            print(f"Sender {sender.username} không phải organizer, không thể đặt is_from_organizer=True, bỏ qua...")
            continue
        chat_message = ChatMessage(
            event=event,
            sender=sender,
            receiver=receiver,
            message=chat_data['message'],
            is_from_organizer=is_from_organizer
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
        # Kiểm tra xem EventTrendingLog đã tồn tại cho event này chưa
        if EventTrendingLog.objects.filter(event=event).exists():
            print(f"EventTrendingLog cho event {event.title} đã tồn tại, bỏ qua...")
            continue
        # Tính total_revenue dựa trên sold_tickets và ticket_price
        total_revenue = event.sold_tickets * event.ticket_price
        trending_log = EventTrendingLog(
            event=event,
            view_count=trending_data.get('view_count', 0),
            total_revenue=total_revenue  # Sửa lỗi cú pháp
        )
        trending_log.save()
        # Tính trending_score và interest_score
        trending_log.calculate_score()
        print(f"Đã tạo event trending log cho event {event.title}")


if __name__ == '__main__':
    load_dummy_data()