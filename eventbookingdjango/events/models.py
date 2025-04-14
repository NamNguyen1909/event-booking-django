from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField


from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

from datetime import timedelta
from django.utils import timezone

from django.core.validators import MinValueValidator, MaxValueValidator # Thêm validator này để kiểm tra giá trị tối đa/tối thiểu cho các trường số
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

# Người dùng
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('organizer', 'Organizer'),
        ('attendee', 'Attendee'),
    )

    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='attendee')
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = CloudinaryField('avatar', null=True, blank=True)
    #1 yếu tố để phân loại user
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0,validators=[MinValueValidator(0)])
    #Chọn khi tạo user, để gợi ý theo sở thích
    tags = models.ManyToManyField('Tag', blank=True, related_name='users')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    # Dùng cả username lẫn email để login
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username or self.email

    # Thêm các phương thức cần thiết cho quyền
    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    def get_customer_group(self):
        now = timezone.now()
        if (now - self.created_at) <= timedelta(days=7):
            return CustomerGroup.NEW
        if self.total_spent < 500_000:
            return CustomerGroup.REGULAR
        if 500_000 <= self.total_spent <= 2000000:
            return CustomerGroup.VIP
        if self.total_spent > 2000000:
            return CustomerGroup.SUPER_VIP
        return CustomerGroup.UNKNOWN

    #khi checkout dùng
    # if user.get_customer_group() == discount_code.user_group:
    # Cho phép áp dụng mã giảm giá


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
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    # Dùng khi kết nối bản đồ Google
    location = models.CharField(max_length=500)
    latitude = models.FloatField()
    longitude = models.FloatField()

    total_tickets = models.IntegerField()
    ticket_price = models.DecimalField(max_digits=9, decimal_places=2,validators=[MinValueValidator(0)])

    tags = models.ManyToManyField('Tag', blank=True)

    poster = CloudinaryField('poster', null=True, blank=True)  # Hình ảnh sự kiện

    def __str__(self):
        return self.title
    
    def save(self):
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be before end time.")
    
    #hàm kiểm tra thời gian sau khi end_time qua thì is_active = False
    def check_event_status(self):
        if timezone.now() > self.end_time:
            self.is_active = False
            self.save()

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Ticket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    qr_code = models.CharField(max_length=255, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    purchase_date = models.DateTimeField(auto_now_add=True)

    is_checked_in = models.BooleanField(default=False)
    check_in_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Ticket of {self.user} for {self.event.title}"
    
    #hàm kiểm tra sau khi check in thì cho is_active = False luôn => Vé vô hiệu lực không thể check in nữa
    def check_in(self):
        if not self.is_checked_in:
            self.is_checked_in = True
            self.check_in_date = timezone.now()
            self.is_active = False 

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('momo', 'MoMo'),
        ('vnpay', 'VNPay'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2,validators=[MinValueValidator(0)])
    # Chọn 1 cái trong PAYMENT_METHOD_CHOICES
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    paid_at = models.DateTimeField(auto_now_add=True)

class CustomerGroup(models.TextChoices):
    NEW = 'new', 'Khách hàng mới'
    REGULAR = 'regular', 'Khách phổ thông'
    VIP = 'vip', 'Khách VIP'
    SUPER_VIP = 'super_vip', 'Khách siêu VIP'
    UNKNOWN = 'unknown', 'Không xác định'

class DiscountCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2,validators=[MinValueValidator(0)])
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

    def __str__(self):
        return self.code
    #hàm kiểm tra mã giảm giá có còn hiệu lực không
    def is_valid(self): 
        now = timezone.now()
        if self.valid_from <= now <= self.valid_to and self.used_count < self.max_uses:
            return True
        return False

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('reminder', 'Reminder'),
        ('update', 'Event Update'),
        ('general', 'General Notification'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='general')
    is_read = models.BooleanField(default=False)
    is_email_sent = models.BooleanField(default=False)  # Theo dõi trạng thái gửi email
    created_at = models.DateTimeField(auto_now_add=True)
    # Chưa có cơ chế gửi email tự động (cần tích hợp với một dịch vụ gửi email như SendGrid hoặc Mailgun).
    # Chưa có cơ chế gửi thông báo đẩy (cần tích hợp với Firebase Cloud Messaging hoặc một dịch vụ tương tự).

class Review(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])  # Giới hạn từ 1 đến 5
    comment = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)  # Trạng thái phê duyệt
    created_at = models.DateTimeField(auto_now_add=True)

class ChatMessage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')  # Người gửi
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')  # Người nhận
    message = models.TextField()
    is_from_organizer = models.BooleanField(default=False)  # Phân biệt tin nhắn từ ban tổ chức
    created_at = models.DateTimeField(auto_now_add=True)
    # Chưa có cơ chế hỗ trợ chat real-time (cần tích hợp WebSocket hoặc Django Channels).

class EventTrendingLog(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    view_count = models.IntegerField(default=0) # Số lượt xem
    ticket_sold_count = models.IntegerField(default=0) # Số vé đã bán
    # like_count = models.IntegerField(default=0)  # Số lượt yêu thích
    last_updated = models.DateTimeField(auto_now=True)

# Nếu cần thêm tính năng yêu thích sự kiện, có thể tạo model Like như sau:
# class Like(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
#     event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='likes')
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         constraints = [
#             models.UniqueConstraint(fields=['user', 'event'], name='unique_user_event_like')
#         ]

#     def __str__(self):
#         return f"{self.user.username} liked {self.event.title}"