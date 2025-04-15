from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.db.models import Sum, Count
from events.models import Event, User, Tag, Ticket, Payment, DiscountCode, Notification, Review, ChatMessage, EventTrendingLog
from events.serializers import (
    EventSerializer, UserSerializer, TagSerializer, TicketSerializer,
    PaymentSerializer, DiscountCodeSerializer, NotificationSerializer,
    ReviewSerializer, ChatMessageSerializer, EventStatisticSerializer,EventTrendingLogSerializer
)
from events.paginators import ItemPaginator

# Đăng ký tài khoản
#Cho phép người dùng đăng ký tài khoản với vai trò admin, organizer, hoặc attendee
class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Cho phép mọi người đăng ký tài khoản

    def get_view_name(self):
        return "Đăng ký tài khoản"

# Tạo sự kiện (chỉ dành cho organizer)
#Cho phép organizer tạo, cập nhật, và quản lý sự kiện của mình
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.filter(is_active=True)
    serializer_class = EventSerializer
    pagination_class = ItemPaginator
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới được truy cập

    def perform_create(self, serializer):
        """Gán organizer là người dùng hiện tại khi tạo sự kiện."""
        serializer.save(organizer=self.request.user)

    def get_view_name(self):
        return "Quản lý sự kiện"

# Gợi ý theo sở thích
# Hiển thị danh sách các tag để gợi ý sự kiện theo sở thích
class TagViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = ItemPaginator
    permission_classes = [permissions.AllowAny]  # Cho phép mọi người xem danh sách tag

    def get_view_name(self):
        return "Danh sách Tag"

# Đặt vé trực tuyến
# Cho phép người dùng đặt vé trực tuyến
class TicketViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới được đặt vé

    def perform_create(self, serializer):
        """Gán người dùng hiện tại khi đặt vé."""
        serializer.save(user=self.request.user)

    def get_view_name(self):
        return "Đặt vé trực tuyến"

# Thanh toán vé
# Xử lý thanh toán vé và cập nhật trạng thái vé
class PaymentViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới được thanh toán

    def perform_create(self, serializer):
        """Xử lý thanh toán và cập nhật trạng thái vé."""
        serializer.save(user=self.request.user)

    def get_view_name(self):
        return "Thanh toán vé"

# Thông báo và nhắc nhở
# Hiển thị thông báo và nhắc nhở cho người dùng hiện tại
class NotificationViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới xem thông báo

    def get_queryset(self):
        """Trả về thông báo liên quan đến các sự kiện của người dùng."""
        user = self.request.user
        if user.role == 'organizer':
            # Nếu là organizer, trả về thông báo cho các sự kiện mà họ tổ chức
            return Notification.objects.filter(event__organizer=user)
        else:
            # Nếu là attendee, trả về thông báo cho các sự kiện mà họ đã mua vé
            return Notification.objects.filter(event__tickets__user=user).distinct()

    def get_view_name(self):
        return "Thông báo và nhắc nhở"

# Đánh giá sự kiện
# Cho phép người dùng đánh giá và viết nhận xét về sự kiện
class ReviewViewSet(viewsets.ViewSet, generics.ListCreateAPIView, generics.UpdateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới được truy cập

    def get_queryset(self):
        """Trả về danh sách review cho sự kiện."""
        event_id = self.request.query_params.get('event_id')
        if event_id:
            return Review.objects.filter(event_id=event_id)
        return Review.objects.all()

    def perform_create(self, serializer):
        """Gán người dùng hiện tại khi tạo review."""
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """Chỉ cho phép người dùng sửa review của chính mình."""
        review = self.get_object()
        if review.user != self.request.user:
            raise permissions.PermissionDenied("Bạn không có quyền sửa review này.")
        serializer.save()

    def get_view_name(self):
        return "Đánh giá sự kiện"

# Thống kê và báo cáo
# Hiển thị thống kê sự kiện của organizer, bao gồm số vé đã bán, doanh thu, và số lượt xem
class OrganizerEventStatisticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới xem thống kê

    def get(self, request):
        organizer = request.user  # Lấy organizer từ người dùng đăng nhập
        events = Event.objects.filter(organizer=organizer)

        statistics = []
        for event in events:
            total_tickets_sold = Ticket.objects.filter(event=event, is_paid=True).count()
            total_revenue = Ticket.objects.filter(event=event, is_paid=True).aggregate(
                total=Sum('event__ticket_price')
            )['total'] or 0
            trending_log = EventTrendingLog.objects.filter(event=event).first()
            view_count = trending_log.view_count if trending_log else 0

            statistics.append({
                'id': event.id,
                'title': event.title,
                'total_tickets_sold': total_tickets_sold,
                'total_revenue': total_revenue,
                'view_count': view_count,
            })

        serializer = EventStatisticSerializer(statistics, many=True)
        return Response(serializer.data)

# Chat real-time
# Cho phép người dùng gửi và nhận tin nhắn liên quan đến sự kiện
class ChatMessageViewSet(viewsets.ViewSet, generics.ListCreateAPIView):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới được chat

    def perform_create(self, serializer):
        """Gán người gửi là người dùng hiện tại."""
        serializer.save(sender=self.request.user)

    def get_queryset(self):
        """Trả về tin nhắn liên quan đến sự kiện của người dùng."""
        return ChatMessage.objects.filter(event__organizer=self.request.user)

    def get_view_name(self):
        return "Chat real-time"

# Mã giảm giá
# Hiển thị danh sách mã giảm giá đang hoạt động
class DiscountCodeViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = DiscountCode.objects.filter(is_active=True)
    serializer_class = DiscountCodeSerializer
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới xem mã giảm giá

    def get_view_name(self):
        return "Danh sách mã giảm giá"
    
# View cho EventTrendingLog
class EventTrendingLogViewSet(viewsets.ModelViewSet):
    queryset = EventTrendingLog.objects.all()
    serializer_class = EventTrendingLogSerializer
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới được truy cập

    def get_queryset(self):
        """Chỉ trả về các log liên quan đến sự kiện của organizer hiện tại."""
        if self.request.user.role == 'organizer':
            return EventTrendingLog.objects.filter(event__organizer=self.request.user)
        return EventTrendingLog.objects.none()

    def perform_update(self, serializer):
        """Cập nhật log sự kiện."""
        serializer.save()

    def perform_create(self, serializer):
        """Tạo log sự kiện mới."""
        serializer.save()
