from rest_framework import serializers
from rest_framework.serializers import ModelSerializer #Trong môn Các công nghệ lập trình hiện đại chỉ xài một loại này thôi
from events.models import Event, User, Tag, Ticket, Payment, DiscountCode,Notification,Review,ChatMessage,EventTrendingLog

# Tạo sự kiện (Organizer tạo sự kiện)
class EventSerializer(ModelSerializer):
    organizer = serializers.ReadOnlyField(source='organizer.id')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['poster']=instance.poster.url if instance.poster else ''
        return data

    class Meta:
        model = Event
        fields = ['id','organizer', 'title', 'description', 'category', 'start_time','end_time','is_active','location','latitude','longitude','total_tickets','ticket_price','poster']
        read_only_fields = ['id', 'organizer']

# Đăng ký tài khoản (Admin, Organizer, Attendee)
class UserSerializer(ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'avatar', 'role', 'password', 'tags']
        read_only_fields = ['id']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

#Gợi ý theo sở thích
class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

# Đặt vé trực tuyến
class TicketSerializer(ModelSerializer):
    event_detail = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['id', 'user', 'event', 'qr_code', 'is_checked_in', 'created_at', 'event_detail']
        read_only_fields = ['id', 'qr_code', 'is_checked_in', 'created_at', 'event_detail']

    def get_event_detail(self, obj):
        return {
            'title': obj.event.title,
            'date': obj.event.date,
            'location': obj.event.location,
        }
# Thanh toán vé
class PaymentSerializer(ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'user', 'ticket', 'amount', 'payment_method', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']

# Thông báo & nhắc nhở sự kiện
class NotificationSerializer(ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'title', 'content', 'created_at', 'is_read']
        read_only_fields = ['id', 'created_at']

# Đánh giá sự kiện
class ReviewSerializer(ModelSerializer):
    user_infor= serializers.SerializerMethodField()
    class Meta:
        model = Review
        fields = ['id', 'user', 'event', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_user_info(self, obj):
        return {
            'username': obj.user.username,
            'avatar': obj.user.avatar.url if obj.user.avatar else None,
        }
    
#Thống kê vé, doanh thu (cho admin / organizer) ====> có vẻ sai
class EventStatisticSerializer(serializers.Serializer):
    event_id = serializers.IntegerField()
    event_title = serializers.CharField()
    total_tickets_sold = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    interested_count = serializers.IntegerField()

#Chat real-time
class ChatMessageSerializer(ModelSerializer):
    user_info = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'event', 'sender', 'message', 'timestamp', 'user_info']
        read_only_fields = ['id', 'timestamp', 'user_info']

    def get_user_info(self, obj):
        return {
            'username': obj.sender.username,
            'avatar': obj.sender.avatar.url if obj.sender.avatar else None,
        }
    
#Mã giảm giá cho khách hàng
class DiscountCodeSerializer(ModelSerializer):
    class Meta:
        model = DiscountCode
        fields = ['id', 'code', 'discount_percent', 'valid_from', 'valid_to', 'usage_limit', 'used_count', 'created_at']
        read_only_fields = ['id', 'created_at', 'used_count']
