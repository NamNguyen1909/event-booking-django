from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import (
    User, Event, Tag, Ticket, Payment, Review, DiscountCode, Notification,
    ChatMessage, EventTrendingLog, UserNotification
)
from django.db import transaction
from django.utils import timezone
from django.db.models import F
from django.db import models
from decimal import Decimal
from cloudinary.utils import cloudinary_url


# Serializer cho Tag
class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


# Serializer cho Review
class ReviewSerializer(serializers.ModelSerializer):
    user_infor = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'user', 'user_infor', 'event', 'rating', 'comment', 'parent_review', 'created_at']
        read_only_fields = ['id', 'created_at', 'user']

    def validate_rating(self, value):
        # Chỉ kiểm tra nếu rating được cung cấp và không phải là phản hồi
        if value is not None and not self.initial_data.get('parent_review'):
            if not (1 <= value <= 5):
                raise serializers.ValidationError("Điểm đánh giá phải từ 1 đến 5.")
        return value

    def validate(self, data):
        # Nếu là phản hồi (parent_review được cung cấp), không yêu cầu rating
        if data.get('parent_review'):
            user = self.context['request'].user
            event = data['parent_review'].event
            if user.role != 'organizer' or event.organizer != user:
                raise serializers.ValidationError("Chỉ organizer của sự kiện mới có thể phản hồi đánh giá.")
            # Gán rating mặc định là 0 nếu không cung cấp
            data['rating'] = data.get('rating', 0)
        else:
            # Nếu là review gốc, yêu cầu rating
            if 'rating' not in data or data['rating'] is None:
                raise serializers.ValidationError({"rating": "Điểm đánh giá là bắt buộc cho review gốc."})
        return data

    def get_user_infor(self, obj):
        """Trả về thông tin chi tiết của người dùng."""
        return {
            'username': obj.user.username,
            'avatar': obj.user.avatar.url if obj.user.avatar else None,
        }


# Serializer cho Notification
class NotificationSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title', allow_null=True)
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'event', 'event_title', 'title', 'message', 'notification_type', 'is_read', 'created_at']
        read_only_fields = ['id', 'event_title', 'created_at']

    def get_is_read(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # Sử dụng filter().first() để tránh truy vấn không cần thiết
        user_notification = UserNotification.objects.filter(
            user=request.user,
            notification=obj
        ).first()
        return user_notification.is_read if user_notification else False


# Serializer cho ChatMessage
class ChatMessageSerializer(ModelSerializer):
    user_info = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'event', 'sender', 'receiver', 'message', 'is_from_organizer', 'created_at', 'user_info']
        read_only_fields = ['id', 'event', 'created_at', 'user_info', 'is_from_organizer']

    def get_user_info(self, obj):
        return {
            'username': obj.sender.username,
            'avatar': obj.sender.avatar.url if obj.sender.avatar else None,
        }


# Serializer cho DiscountCode
class DiscountCodeSerializer(ModelSerializer):
    class Meta:
        model = DiscountCode
        fields = [
            'id', 'code', 'discount_percentage', 'valid_from', 'valid_to',
            'user_group', 'max_uses', 'used_count', 'is_active'
        ]
        read_only_fields = ['used_count']


# Serializer cho Event
class EventSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['poster'] = instance.poster.url if instance.poster else ''
        return data

    class Meta:
        model = Event
        fields = [
            'id', 'organizer', 'title', 'description', 'category', 'start_time', 'end_time',
            'is_active', 'location', 'latitude', 'longitude', 'total_tickets', 'ticket_price',
            'sold_tickets', 'tags', 'poster', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organizer', 'sold_tickets', 'created_at', 'updated_at']

        # Đảm bảo các trường không bắt buộc khi cập nhật (partial update)
        extra_kwargs = {
            'title': {'required': False},
            'description': {'required': False},
            'category': {'required': False},
            'start_time': {'required': False},
            'end_time': {'required': False},
            'is_active': {'required': False},
            'location': {'required': False},
            'latitude': {'required': False},
            'longitude': {'required': False},
            'total_tickets': {'required': False},
            'ticket_price': {'required': False},
            'poster': {'required': False},
            'tags': {'required': False},
        }

    # Xử lý ticket_price dưới dạng DecimalField để đảm bảo validate đúng
    ticket_price = serializers.DecimalField(
        max_digits=9,
        decimal_places=2,
        min_value=Decimal('0'),
        required=False
    )
    from decimal import Decimal
    total_tickets = serializers.IntegerField(min_value=Decimal('0'), required=False)
    latitude = serializers.FloatField(min_value=Decimal('-90'), max_value=Decimal('90'), required=False)
    longitude = serializers.FloatField(min_value=Decimal('-180'), max_value=Decimal('180'), required=False)


# Serializer cho Ticket
class TicketSerializer(ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')  # Lấy tên người dùng
    email = serializers.ReadOnlyField(source='user.email')  # Lấy email người dùng
    event_title = serializers.ReadOnlyField(source='event.title')  # Lấy tiêu đề sự kiện
    event_start_time = serializers.ReadOnlyField(source='event.start_time')  # Lấy thời gian bắt đầu sự kiện
    event_location = serializers.ReadOnlyField(source='event.location')  # Lấy địa điểm sự kiện
    event_id = serializers.ReadOnlyField(source='event.id')  # Lấy event id
    qr_code = serializers.ReadOnlyField()  # Thêm trường qr_code để hiển thị mã QR

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.qr_code:
            public_id = str(instance.qr_code)  # hoặc instance.qr_code.public_id nếu cần chính xác hơn
            url, options = cloudinary_url(public_id)
            data['qr_code'] = url
        else:
            data['qr_code'] = ''
        return data

    class Meta:
        model = Ticket
        fields = [
            'id', 'username', 'email', 'purchase_date', 'qr_code',
            'event_title', 'event_start_time', 'event_location', 'event_id','is_paid','uuid'
        ]
        read_only_fields = [
            'id', 'username', 'email', 'purchase_date', 'qr_code',
            'event_title', 'event_start_time', 'event_location', 'event_id','is_paid','uuid'
        ]

    def create(self, validated_data):
        # Tự động gán user và event từ context
        user = self.context['request'].user
        event = self.context['event']
        return Ticket.objects.create(user=user, event=event, **validated_data)


# Serializer cho Payment
class PaymentSerializer(ModelSerializer):
    user_detail = serializers.SerializerMethodField()
    tickets = TicketSerializer(many=True, read_only=True)  # Lấy danh sách vé đã mua

    amount = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ['id', 'user', 'user_detail', 'amount', 'payment_method', 'paid_at', 'transaction_id', 'tickets']
        read_only_fields = ['id', 'paid_at', 'transaction_id']

    def get_user_detail(self, obj):
        return {
            'username': obj.user.username,
            'email': obj.user.email,
            'phone': obj.user.phone,
        }

    def get_amount(self, obj):
        # Convert Decimal to string for JSON serialization
        return str(obj.amount)


# Serializer cho User
class UserSerializer(ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'phone', 'role', 'tags', 'avatar','is_staff']
        read_only_fields = ['id','is_staff']

    def validate_tags(self, value):
        if value:
            for tag in value:
                if not Tag.objects.filter(id=tag.id).exists():
                    raise serializers.ValidationError(f"Tag với ID {tag.id} không tồn tại.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        tags = validated_data.pop('tags', [])
        avatar = validated_data.pop('avatar', None)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=password,
            phone=validated_data.get('phone'),
            role=validated_data.get('role', 'attendee'),
            avatar=avatar
        )
        if tags:
            user.tags.set(tags)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        tags = validated_data.pop('tags', None)
        avatar = validated_data.pop('avatar', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if tags is not None:
            instance.tags.set(tags)
        if avatar is not None:
            instance.avatar = avatar
        instance.save()
        return instance


# Serializer chi tiết cho User: Profile
class UserDetailSerializer(ModelSerializer):
    organized_events = EventSerializer(many=True, read_only=True)
    tickets = TicketSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    user_notifications = serializers.SerializerMethodField()

    def get_user_notifications(self, obj):
        # Lấy danh sách UserNotification của user
        user_notifications = obj.user_notifications.all()
        # Trả về danh sách Notification tương ứng
        notifications = [user_notification.notification for user_notification in user_notifications]
        return NotificationSerializer(notifications, many=True, context=self.context).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['avatar'] = instance.avatar.url if instance.avatar else ''
        data['customer_group'] = instance.get_customer_group().value
        return data

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'phone', 'avatar', 'total_spent',
            'tags', 'is_active', 'is_staff', 'is_superuser', 'created_at', 'updated_at',
            'organized_events', 'tickets', 'payments', 'user_notifications'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_staff', 'is_superuser', 'total_spent']


# Serializer cho EventDetail
class EventDetailSerializer(serializers.ModelSerializer):
    organizer = UserSerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    event_notifications = NotificationSerializer(many=True, read_only=True)
    chat_messages = ChatMessageSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    discount_codes = serializers.SerializerMethodField()

    def get_discount_codes(self, obj):
        now = timezone.now()
        discount_codes = DiscountCode.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now
        ).exclude(
            max_uses__isnull=False,
            used_count__gte=F('max_uses')
        )
        return DiscountCodeSerializer(discount_codes, many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['poster'] = instance.poster.url if instance.poster else ''
        data['sold_tickets'] = instance.sold_tickets
        data['ticket_price'] = str(instance.ticket_price) if instance.ticket_price is not None else None
        return data

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        # Lấy organizer từ context (user hiện tại)
        user = self.context['request'].user
        if not user.is_authenticated or user.role != 'organizer':
            raise serializers.ValidationError("Chỉ có organizer mới có thể tạo sự kiện.")
        validated_data['organizer'] = user
        with transaction.atomic():
            event = Event.objects.create(**validated_data)
            if tags:
                event.tags.set(tags)
            return event

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if tags is not None:
            instance.tags.set(tags)
        instance.save()
        return instance

    class Meta:
        model = Event
        fields = [
            'id', 'organizer', 'title', 'description', 'category', 'start_time',
            'end_time', 'is_active', 'location', 'latitude', 'longitude',
            'total_tickets', 'ticket_price', 'sold_tickets', 'tags', 'poster',
            'created_at', 'updated_at', 'reviews', 'event_notifications',
            'chat_messages', 'discount_codes'
        ]
        read_only_fields = ['created_at', 'updated_at', 'sold_tickets', 'reviews',
                            'event_notifications', 'chat_messages', 'organizer']


# Serializer cho EventTrendingLog
class EventTrendingLogSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')  # Lấy tiêu đề sự kiện
    event_poster = serializers.ReadOnlyField(source='event.poster.url')  # Lấy poster sự kiện

    class Meta:
        model = EventTrendingLog
        fields = [ 'event', 'event_title', 'event_poster', 'view_count', 'total_revenue', 'trending_score', 'interest_score', 'last_updated']
        read_only_fields = ['event_title', 'last_updated']