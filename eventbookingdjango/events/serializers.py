from rest_framework import serializers
from rest_framework.serializers import ModelSerializer #Trong môn Các công nghệ lập trình hiện đại chỉ xài một loại này thôi
from django.db import models  # Import models để sử dụng các hàm aggregate như Sum
from events.models import Event, User, Tag, Ticket, Payment, DiscountCode,Notification,Review,ChatMessage,EventTrendingLog


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


# Tạo sự kiện (Organizer tạo sự kiện)
class EventSerializer(ModelSerializer):
    organizer = serializers.ReadOnlyField(source='organizer.id')  # Hiển thị ID của organizer
    organizer_name = serializers.ReadOnlyField(source='organizer.username')  # Hiển thị tên của organizer
    tags = TagSerializer(many=True)  # Hiển thị tên các tag

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['poster'] = instance.poster.url if instance.poster else ''
        return data

    class Meta:
        model = Event
        fields = [
            'id', 'organizer', 'organizer_name', 'title', 'description', 'category',
            'start_time', 'end_time', 'is_active', 'location', 'latitude', 'longitude',
            'total_tickets', 'ticket_price', 'tags', 'poster', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organizer', 'organizer_name', 'created_at', 'updated_at']

# Đăng ký tài khoản (Admin, Organizer, Attendee)
class UserSerializer(serializers.ModelSerializer):
    # tags = TagSerializer(many=True)  # Hiển thị tên các tag
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)  # Hỗ trợ gửi danh sách ID
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['avatar'] = instance.avatar.url if instance.avatar else ''
        return data

    class Meta:
        model = User
        fields = ['username','password', 'email', 'role', 'phone', 'avatar','tags']
        extra_kwargs = {
            'password': 
                {'write_only': True},  # Không cho phép đọc password
            }
    
    def create(self, validated_data):
        tags = validated_data.pop('tags', [])  # Lấy danh sách tag từ dữ liệu
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        user.tags.set(tags)  # Gán các tag cho user
        return user

    # # Của thầy
    # def create(self, validated_data):
    #     data = validated_data.copy()
    #     u = User(**data)
    #     u.set_password(u.password)
    #     u.save()
    #     return u




# Đặt vé trực tuyến
class TicketSerializer(serializers.ModelSerializer):
    event_detail = serializers.SerializerMethodField()  # Thông tin chi tiết về sự kiện
    user_detail = serializers.SerializerMethodField()  # Thông tin chi tiết về người dùng

    class Meta:
        model = Ticket
        fields = [
            'id', 'user', 'user_detail', 'event', 'event_detail', 'qr_code',
            'is_paid', 'purchase_date', 'is_checked_in', 'check_in_date', 'created_at'
        ]
        read_only_fields = ['id', 'qr_code', 'is_paid', 'purchase_date', 'is_checked_in', 'check_in_date', 'created_at']

    def get_event_detail(self, obj):
        """Trả về thông tin chi tiết của sự kiện."""
        return {
            'title': obj.event.title,
            'start_time': obj.event.start_time,
            'location': obj.event.location,
        }

    def get_user_detail(self, obj):
        """Trả về thông tin chi tiết của người dùng."""
        return {
            'username': obj.user.username,
            'email': obj.user.email,
        }
    
# Thanh toán vé
class PaymentSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField()
    tickets = serializers.SerializerMethodField()  # Danh sách vé liên quan

    class Meta:
        model = Payment
        fields = ['id', 'user', 'user_detail', 'amount', 'payment_method', 'paid_at', 'transaction_id', 'tickets']
        read_only_fields = ['id', 'paid_at', 'transaction_id']

    def get_user_detail(self, obj):
        return {
            'username': obj.user.username,
            'email': obj.user.email,
        }

    def get_tickets(self, obj):
        tickets = obj.user.tickets.filter(is_paid=True)  # Lấy các vé đã thanh toán
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
