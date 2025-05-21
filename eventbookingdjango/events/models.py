from datetime import timedelta
from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from cloudinary.models import CloudinaryField
import uuid
from decimal import Decimal

# pip install qrcode[pil]
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile


# Quản lý người dùng tùy chỉnh
class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username and not email:
            raise ValueError('Phải cung cấp username hoặc email.')
        if email:
            email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)


class CustomerGroup(models.TextChoices):
    NEW = 'new', 'Khách hàng mới'
    REGULAR = 'regular', 'Khách phổ thông'
    VIP = 'vip', 'Khách VIP'
    SUPER_VIP = 'super_vip', 'Khách siêu VIP'
    UNKNOWN = 'unknown', 'Không xác định'


# Người dùng
class User(AbstractBaseUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('organizer', 'Organizer'),
        ('attendee', 'Attendee'),
    )

    username = models.CharField(max_length=255, unique=True, db_index=True)
    password = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='attendee')
    phone = models.CharField(max_length=15, null=True, blank=True)
    avatar = CloudinaryField('avatar', null=True, blank=True)

    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    tags = models.ManyToManyField('Tag', blank=True, related_name='users')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.username or self.email

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    def get_customer_group(self):
        now = timezone.now()
        if (now - self.created_at) <= timedelta(days=7):
            return CustomerGroup.NEW
        if self.total_spent < 500000:
            return CustomerGroup.REGULAR
        if 500000 <= self.total_spent <= 2000000:
            return CustomerGroup.VIP
        if self.total_spent > 2000000:
            return CustomerGroup.SUPER_VIP
        return CustomerGroup.UNKNOWN


# Sự kiện
class EventQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True, end_time__gte=timezone.now())


# Sự kiện
class Event(models.Model):
    CATEGORY_CHOICES = (
        ('music', 'Music'),
        ('sports', 'Sports'),
        ('seminar', 'Seminar'),
        ('conference', 'Conference'),
        ('festival', 'Festival'),
        ('workshop', 'Workshop'),
        ('party', 'Party'),
        ('competition', 'Competition'),
        ('other', 'Other'),
    )

    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    location = models.CharField(max_length=500)
    latitude = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])

    total_tickets = models.IntegerField(validators=[MinValueValidator(0)])
    ticket_price = models.DecimalField(max_digits=9, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    sold_tickets = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    tags = models.ManyToManyField('Tag', blank=True, related_name='events')

    poster = CloudinaryField('poster', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_time__lt=models.F('end_time')),
                name='start_time_before_end_time'
            ),
        ]
        indexes = [
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['organizer']),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Thời gian bắt đầu phải trước thời gian kết thúc.")
        if self.organizer.role != 'organizer':
            raise ValidationError("Chỉ có người tổ chức mới có thể tạo sự kiện.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    #chuyển sang signals.py update_event_status
    # def check_event_status(self):
    #     if timezone.now() > self.end_time:
    #         self.is_active = False
    #         self.save()


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, db_index=True)

    def __str__(self):
        return self.name


# Vé
class Ticket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    qr_code = CloudinaryField('qr_code', null=True, blank=True)  # Lưu QR code

    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    purchase_date = models.DateTimeField(null=True, blank=True)

    is_checked_in = models.BooleanField(default=False)
    check_in_date = models.DateTimeField(null=True, blank=True)
    payment=models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='tickets')

    class Meta:
        indexes = [
            models.Index(fields=['user', 'event']),
            models.Index(fields=['qr_code']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Vé của {self.user} - Sự kiện {self.event.title}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.pk:  # Chỉ kiểm tra khi tạo mới
                # Giả sử event có thuộc tính sold_tickets (tự tính hoặc trường riêng cập nhật)
                if self.event.sold_tickets >= self.event.total_tickets:
                    raise ValidationError("Hết vé cho sự kiện này.")
            super().save(*args, **kwargs)

    def mark_as_paid(self, paid_at):
        self.is_paid = True
        self.purchase_date = paid_at
        self.save()

    def check_in(self):
        if not self.is_checked_in:
            self.is_checked_in = True
            self.check_in_date = timezone.now()
            self.save()


# Thanh toán
class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('momo', 'MoMo'),
        ('vnpay', 'VNPay'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    transaction_id = models.CharField(max_length=255, unique=True)
    discount_code = models.ForeignKey('DiscountCode', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='payments')

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['transaction_id']),
        ]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.pk:
                # Respect the status set externally, default to False if not set
                if self.status is None:
                    self.status = False

                if self.status and not self.paid_at:
                    self.paid_at = timezone.now()

                super().save(*args, **kwargs)  # Save before assigning tickets

            else:
                # Update payment if modified
                if self.status and not self.paid_at:
                    self.paid_at = timezone.now()
                super().save(*args, **kwargs)

            # Mark tickets as paid
            for ticket in Ticket.objects.filter(payment=self):
                if not ticket.is_paid:
                    ticket.mark_as_paid(self.paid_at)

            # Update discount code usage count
            if self.discount_code and self.discount_code.is_valid():
                self.discount_code.used_count += 1
                self.discount_code.save()

    def get_display_transaction_id(self):
        return f"****{self.transaction_id[-4:]}"  # Hiển thị 4 ký tự cuối để bảo mật


# Đánh giá
class Review(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_reviews')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0  # Đảm bảo default=0 để phù hợp với phản hồi
    )
    comment = models.TextField(null=True, blank=True)
    
    # Thêm dòng này để cho phép phản hồi review khác
    parent_review = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['event', 'user']),
            models.Index(fields=['parent_review']),
        ]

    def __str__(self):
        return f"{self.user} - {self.rating} sao cho {self.event}"



# Mã giảm giá
class DiscountCode(models.Model):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2,
                                              validators=[MinValueValidator(0), MaxValueValidator(100)])
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    user_group = models.CharField(
        max_length=50,
        choices=CustomerGroup.choices,
        default=CustomerGroup.UNKNOWN
    )
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(valid_from__lte=models.F('valid_to')),
                name='valid_from_before_valid_to'
            ),
        ]
        indexes = [
            models.Index(fields=['code', 'is_active']),
        ]

    def __str__(self):
        return self.code

    def is_valid(self):
        now = timezone.now()
        if self.valid_from <= now <= self.valid_to and (self.max_uses is None or self.used_count < self.max_uses):
            return True
        return False


# Thông báo
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('reminder', 'Reminder'),
        ('update', 'Event Update'),
    )
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='event_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='reminder')
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']

# Chưa có cơ chế gửi thông báo real-time (cần tích hợp WebSocket hoặc Django Channels).
# Để đánh dấu thông báo  đã được người dùng đọc hay chưa
class UserNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_notifications')
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='user_notifications')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'notification')  # Mỗi user - notification chỉ 1 bản ghi



# Tin nhắn trò chuyện
class ChatMessage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    is_from_organizer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['event', 'sender', 'receiver']),
        ]

    def save(self, *args, **kwargs):
        if self.is_from_organizer and self.sender.role != 'organizer':
            raise ValidationError("Chỉ có người tổ chức mới có thể gửi tin nhắn với tư cách người tổ chức.")
        super().save(*args, **kwargs)

    # Chưa có cơ chế hỗ trợ chat real-time (cần tích hợp WebSocket hoặc Django Channels).


import math
from datetime import date

class EventTrendingLog(models.Model):
    # EventTrendingLog dùng chung khóa chính với Event (tức là cùng một ID, kiểu như extension của bảng Event)
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='trending_log', primary_key=True)
    view_count = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    trending_score = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    interest_score = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def calculate_score(self):
        today = date.today()
        sold_tickets = self.event.sold_tickets
        total_tickets = self.event.total_tickets
        review_count = self.event.reviews.count()
        sales_start_date = self.event.created_at.date() if self.event.created_at else today

        # Tỷ lệ vé đã bán
        sold_ratio = sold_tickets / total_tickets if total_tickets else 0
        # Tốc độ bán
        days_since_sales_start = (today - sales_start_date).days or 1
        velocity = sold_tickets / days_since_sales_start
        views = self.view_count

        # Trending score
        trending_score = (
            (sold_ratio * 0.5) +
            (velocity * 0.3) +
            (math.log(views + 1) * 0.2)
        )
        self.trending_score = round(trending_score, 4)

        # Interest score – có thể điều chỉnh trọng số tùy mục tiêu
        interest_score = (
            (self.trending_score * 0.5) +
            (sold_tickets * 0.3) +
            (review_count * 0.2)
        )
        self.interest_score = round(interest_score, 4)

        self.save(update_fields=['trending_score', 'interest_score'])


    class Meta:
        indexes = [
            models.Index(fields=['event', 'last_updated']),
        ]
        ordering = ['-trending_score']
