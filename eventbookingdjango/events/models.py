from datetime import timedelta
from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from cloudinary.models import CloudinaryField
import uuid

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
    ticket_price = models.DecimalField(max_digits=9, decimal_places=2, validators=[MinValueValidator(0)])
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
    qr_code = CloudinaryField('qr_code', null=True, blank=True)  # Lưu QR code

    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    purchase_date = models.DateTimeField(null=True, blank=True)

    is_checked_in = models.BooleanField(default=False)
    check_in_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'event']),
            models.Index(fields=['qr_code']),
        ]

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
    tickets = models.ManyToManyField(Ticket, related_name='payments', blank=True)  # Danh sách vé liên quan
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
                # Nếu là tạo mới (chưa có id), thì tự động lấy các vé chưa thanh toán
                unpaid_tickets = Ticket.objects.filter(user=self.user, is_paid=False).select_related('event')
                total = sum(ticket.event.ticket_price for ticket in unpaid_tickets)

                # Áp dụng giảm giá nếu có
                if self.discount_code and self.discount_code.is_valid():
                    discount = total * (self.discount_code.discount_percentage / 100)
                    total -= discount
                self.amount = max(total, 0)

                self.status = True  # Giả định là thanh toán thành công (bạn có thể tùy chỉnh)
                if self.status and not self.paid_at:
                    self.paid_at = timezone.now()

                super().save(*args, **kwargs)  # Phải save trước khi gọi set() cho ManyToMany
                self.tickets.set(unpaid_tickets)  # Gắn vé vào payment

            else:
                # Cập nhật thanh toán (nếu có cập nhật sau này)
                if self.status and not self.paid_at:
                    self.paid_at = timezone.now()
                super().save(*args, **kwargs)

            # Đánh dấu vé là đã thanh toán
            for ticket in self.tickets.all():
                if not ticket.is_paid:
                    ticket.mark_as_paid(self.paid_at)

            # Cập nhật số lần dùng của mã giảm giá
            if self.discount_code and self.discount_code.is_valid():
                self.discount_code.used_count += 1
                self.discount_code.save()

    def get_display_transaction_id(self):
        return f"****{self.transaction_id[-4:]}"  # Hiển thị 4 ký tự cuối để bảo mật


# Đánh giá
class Review(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_reviews')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['event', 'user']),
        ]

    def __str__(self):
        return f"Đánh giá {self.rating} - {self.event.title}"


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
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='general')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_read', ]),
        ]

    def __str__(self):
        return self.title


# Tin nhắn trò chuyện
class ChatMessage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    is_from_organizer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['event', 'sender', 'receiver']),
        ]

    def save(self, *args, **kwargs):
        if self.is_from_organizer and self.sender.role != 'organizer':
            raise ValidationError("Chỉ có người tổ chức mới có thể gửi tin nhắn với tư cách người tổ chức.")
        super().save(*args, **kwargs)

    # Chưa có cơ chế hỗ trợ chat real-time (cần tích hợp WebSocket hoặc Django Channels).


class EventTrendingLog(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='trending_logs')
    view_count = models.IntegerField(default=0)
    ticket_sold_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['event', 'last_updated']),
        ]