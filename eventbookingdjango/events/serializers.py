from rest_framework import serializers
from rest_framework.serializers import ModelSerializer #Trong môn Các công nghệ lập trình hiện đại chỉ xài một loại này thôi
from django.db import models  # Import models để sử dụng các hàm aggregate như Sum
from events.models import Event, User, Tag, Ticket, Payment, DiscountCode,Notification,Review,ChatMessage,EventTrendingLog
from django.utils import timezone
from django.db.models import F
from django.db import transaction


# Đặt vé trực tuyến / Xem thông tin vé
class TicketSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')  # Lấy tên người dùng
    email = serializers.ReadOnlyField(source='user.email')  # Lấy email người dùng
    event_title = serializers.ReadOnlyField(source='event.title')  # Lấy tiêu đề sự kiện
    event_start_time = serializers.ReadOnlyField(source='event.start_time')  # Lấy thời gian bắt đầu sự kiện
    event_location = serializers.ReadOnlyField(source='event.location')  # Lấy địa điểm sự kiện
    qr_code = serializers.ReadOnlyField()  # Thêm trường qr_code để hiển thị mã QR

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['qr_code'] = instance.qr_code.url if instance.qr_code else ''
        return data

    class Meta:
        model = Ticket
        fields = [
            'id', 'username', 'email', 'purchase_date', 'qr_code',
            'event_title', 'event_start_time', 'event_location'
        ]
        read_only_fields = [
            'id', 'username', 'email', 'purchase_date', 'qr_code',
            'event_title', 'event_start_time', 'event_location'
        ]

    def create(self, validated_data):
        # Tự động gán user và event từ context
        user = self.context['request'].user
        event = self.context['event']
        return Ticket.objects.create(user=user, event=event, **validated_data)
    
# Thanh toán vé
class PaymentSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField()
    tickets = TicketSerializer(many=True, read_only=True)  # Lấy danh sách vé đã mua

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

    def get_tickets(self, obj):
        tickets = obj.tickets.all()
        return [
            {
                'id': ticket.id,
                'event': ticket.event.title,
                'qr_code': ticket.qr_code,
                'purchase_date': ticket.purchase_date,
            }
            for ticket in tickets
        ]

    
#Mã giảm giá cho khách hàng
class DiscountCodeSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()  # Trạng thái hợp lệ của mã giảm giá

    class Meta:
        model = DiscountCode
        fields = [
            'id', 'code', 'discount_percentage', 'valid_from', 'valid_to',
            'user_group', 'max_uses', 'used_count', 'is_active', 'is_valid'
        ]
        read_only_fields = ['id', 'used_count', 'is_valid']

    def get_is_valid(self, obj):
        """Sử dụng phương thức is_valid từ model."""
        return obj.is_valid()

# Thông báo & nhắc nhở sự kiện
class NotificationSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')  # Lấy tiêu đề sự kiện nếu có

    class Meta:
        model = Notification
        fields = ['id', 'event', 'event_title', 'message', 'notification_type', 'is_read', 'created_at']
        read_only_fields = ['id', 'event_title', 'created_at']

# Đánh giá sự kiện
class ReviewSerializer(serializers.ModelSerializer):
    user_infor = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'user', 'user_infor', 'event', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_user_infor(self, obj):
        """Trả về thông tin chi tiết của người dùng."""
        return {
            'username': obj.user.username,
            'avatar': obj.user.avatar.url if obj.user.avatar else None,
        }
    
    
#Chat real-time
class ChatMessageSerializer(ModelSerializer):
    user_info = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'event', 'sender', 'receiver', 'message', 'is_from_organizer', 'created_at', 'user_info']
        read_only_fields = ['id', 'created_at', 'user_info']

    def get_user_info(self, obj):
        return {
            'username': obj.sender.username,
            'avatar': obj.sender.avatar.url if obj.sender.avatar else None,
        }

# Thống kê sự kiện nổi bật (Trending Events)
class EventTrendingLogSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')  # Lấy tiêu đề sự kiện

    class Meta:
        model = EventTrendingLog
        fields = ['id', 'event', 'event_title', 'view_count', 'ticket_sold_count', 'last_updated']
        read_only_fields = ['id', 'event_title', 'last_updated']

    
    
class EventStatisticSerializer(serializers.ModelSerializer):
    total_tickets_sold = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()  # Thống kê số lượt xem

    class Meta:
        model = Event
        fields = ['id', 'title', 'total_tickets_sold', 'total_revenue', 'view_count']

    def get_total_tickets_sold(self, obj):
        """Trả về tổng số vé đã bán."""
        return Ticket.objects.filter(event=obj, is_paid=True).count()

    def get_total_revenue(self, obj):
        """Trả về tổng doanh thu từ sự kiện."""
        total = Ticket.objects.filter(event=obj, is_paid=True).aggregate(
            total=models.Sum('event__ticket_price')
        )['total']
        return total or 0

    def get_view_count(self, obj):
        """Trả về số lượt xem của sự kiện."""
        trending_log = EventTrendingLog.objects.filter(event=obj).first()
        return trending_log.view_count if trending_log else 0


# Serializer cho Tag
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

# Serializer cho Event
class EventSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['poster'] = instance.poster.url if instance.poster else ''
        return data

    class Meta:
        model = Event
        fields = ['poster', 'title', 'location', 'start_time']
        read_only_fields = ['poster', 'title', 'location', 'start_time']

# Serializer cho User: Tạo user/thay đổi tags ,password
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'phone', 'role', 'tags']
        read_only_fields = ['id']

    def validate_tags(self, value):
        """Kiểm tra xem danh sách tag có hợp lệ không."""
        if value:
            for tag in value:
                if not Tag.objects.filter(id=tag.id).exists():
                    raise serializers.ValidationError(f"Tag với ID {tag.id} không tồn tại.")
        return value


    def create(self, validated_data):
        """Tạo người dùng mới và gán tags."""
        password = validated_data.pop('password')
        tags = validated_data.pop('tags', [])
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=password,
            phone=validated_data.get('phone'),
            role=validated_data.get('role', 'attendee')
        )
        if tags:
            user.tags.set(tags)  # Gán danh sách tag cho người dùng
        return user


    def update(self, instance, validated_data):
        """Cập nhật thông tin người dùng, bao gồm tags."""
        password = validated_data.pop('password', None)
        tags = validated_data.pop('tags', None)

        # Cập nhật các trường khác
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Cập nhật mật khẩu nếu có
        if password:
            instance.set_password(password)

        # Cập nhật tags nếu có
        if tags is not None:
            instance.tags.set(tags)

        instance.save()
        return instance


# Serializer chi tiết cho Event:Xem chi tiết event
class EventDetailSerializer(serializers.ModelSerializer):
    organizer = UserSerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    event_notifications = NotificationSerializer(many=True, read_only=True)
    chat_messages = ChatMessageSerializer(many=True, read_only=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)
    discount_codes = serializers.SerializerMethodField()

    def get_discount_codes(self, obj):
        """Lấy danh sách mã giảm giá hợp lệ có thể áp dụng cho sự kiện."""
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
        return data

    def create(self, validated_data):
        """Tạo sự kiện mới, gán tags và tạo vé."""
        tags = validated_data.pop('tags', [])
        organizer = validated_data.pop('organizer', None)  # Organizer được gán trong view

        with transaction.atomic():
            # Tạo sự kiện
            event = Event.objects.create(**validated_data)

            # Gán tags
            if tags:
                event.tags.set(tags)
            return event

    def update(self, instance, validated_data):
        """Cập nhật sự kiện, bao gồm tags."""
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




# Serializer chi tiết cho User:Profile
class UserDetailSerializer(serializers.ModelSerializer):
    organized_events = EventSerializer(many=True, read_only=True)
    tickets = TicketSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    notifications = NotificationSerializer(many=True, read_only=True)

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
            'organized_events', 'tickets', 'payments','notifications'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_staff', 'is_superuser', 'total_spent']




