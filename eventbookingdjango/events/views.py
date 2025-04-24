import uuid
from django.db.models import Q, Sum, Count
from django.utils import timezone

from rest_framework import viewsets, generics, permissions, status, parsers
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import perms

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import (
    Event, User, Tag, Ticket, Payment, DiscountCode,
    Notification, Review, ChatMessage, EventTrendingLog
)
from .serializers import (
    EventSerializer, EventDetailSerializer, UserSerializer, UserDetailSerializer,
    TagSerializer, TicketSerializer, PaymentSerializer, DiscountCodeSerializer,
    NotificationSerializer, ReviewSerializer, ChatMessageSerializer, EventTrendingLogSerializer
)
from .paginators import ItemPaginator
from rest_framework import serializers



class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    serializer_class = UserSerializer
    pagination_class = ItemPaginator
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'phone']
    ordering_fields = ['created_at', 'username']

    def get_permissions(self):
        if self.action in ['get_current_user', 'tickets', 'payments', 'notifications', 'sent_messages', 'profile', 'deactivate']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['create']:
            return [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        role = request.data.get('role', 'attendee')
        if role not in ['admin', 'organizer', 'attendee']:
            return Response({"error": "Vai trò không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['get', 'patch'], detail=False, url_path='current-user')
    def get_current_user(self, request):
        user = request.user
        if request.method == 'PATCH':
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(self.get_serializer(user).data)
        else:
            serializer = UserDetailSerializer(user)
            return Response(serializer.data)

    @action(methods=['post'], detail=False, url_path='deactivate')
    def deactivate(self, request):
        user = request.user
        user.is_active = False
        user.save()
        return Response({"detail": "Tài khoản đã bị xóa!."}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='tickets')
    def get_tickets(self, request):
        user = request.user

        tickets = user.tickets.all().select_related('event')
        page = self.paginate_queryset(tickets)
        serializer = serializers.TicketSerializer(page or tickets, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    @action(methods=['get'], detail=False, url_path='payments')
    def get_payments(self, request):
        user = request.user

        payments = user.payments.all().select_related('discount_code')
        page = self.paginate_queryset(payments)
        serializer = serializers.PaymentSerializer(page or payments, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    # @action(methods=['get'], detail=False, url_path='reviews')
    # def get_reviews(self, request):
    #     user = request.user
    #     reviews = user.event_reviews.all().select_related('event')
    #     page = self.paginate_queryset(reviews)
    #     serializer = serializers.ReviewSerializer(page or reviews, many=True)
    #     return self.get_paginated_response(serializer.data) if page else Response(serializer.data)



    # lazy loading / infinite scroll

    # Backend (API) vẫn phân trang bình thường (?page=1, ?page=2, ...)
    # Frontend (Vue/React/Next.js...) sẽ:
    # Gọi GET /api/my-notifications/?page=1 khi vừa load
    # Khi kéo xuống gần cuối danh sách → gọi GET /api/my-notifications/?page=2 để load tiếp
    # Append (nối thêm) vào danh sách đang hiển thị
    @action(detail=False, methods=['get'], url_path='my-notifications')
    def my_notifications(self, request):
        user = request.user
        tickets = Ticket.objects.filter(user=user).values('event_id')
        notifications = Notification.objects.filter(event__id__in=tickets).select_related('event')
        page = self.paginate_queryset(notifications)
        serializer = serializers.NotificationSerializer(page or notifications, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    @action(methods=['get'], detail=False, url_path='sent-messages')
    def get_sent_messages(self, request):
        user = request.user

        messages = user.sent_messages.all().select_related('event', 'receiver')
        page = self.paginate_queryset(messages)
        serializer = serializers.ChatMessageSerializer(page or messages, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)
    serializer_class = UserSerializer
    pagination_class = ItemPaginator
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'phone']
    ordering_fields = ['created_at', 'username']

    def get_permissions(self):
        if self.action in ['get_current_user', 'tickets', 'payments', 'notifications', 'sent_messages', 'profile', 'deactivate']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['create']:
            return [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        role = request.data.get('role', 'attendee')
        if role not in ['admin', 'organizer', 'attendee']:
            return Response({"error": "Vai trò không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['get', 'patch'], detail=False, url_path='current-user')
    def get_current_user(self, request):
        user = request.user
        if request.method == 'PATCH':
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(self.get_serializer(user).data)
        else:
            serializer = UserDetailSerializer(user)
            return Response(serializer.data)

    @action(methods=['post'], detail=False, url_path='deactivate')
    def deactivate(self, request):
        user = request.user
        user.is_active = False
        user.save()
        return Response({"detail": "Tài khoản đã bị xóa!."}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='tickets')
    def get_tickets(self, request):
        user = request.user

        tickets = user.tickets.all().select_related('event')
        page = self.paginate_queryset(tickets)
        serializer = serializers.TicketSerializer(page or tickets, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    @action(methods=['get'], detail=False, url_path='payments')
    def get_payments(self, request):
        user = request.user

        payments = user.payments.all().select_related('discount_code')
        page = self.paginate_queryset(payments)
        serializer = serializers.PaymentSerializer(page or payments, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    # @action(methods=['get'], detail=False, url_path='reviews')
    # def get_reviews(self, request):
    #     user = request.user
    #     reviews = user.event_reviews.all().select_related('event')
    #     page = self.paginate_queryset(reviews)
    #     serializer = serializers.ReviewSerializer(page or reviews, many=True)
    #     return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    # @action(methods=['get'], detail=False, url_path='notifications')
    # def get_notifications(self, request):
    #     user = request.user

    #     # Lọc thông báo dựa trên vé của người dùng
    #     tickets = Ticket.objects.filter(user=user).values('event_id')
    #     notifications = Notification.objects.filter(event__id__in=tickets).select_related('event')
    #     page = self.paginate_queryset(notifications)
    #     serializer = serializers.NotificationSerializer(page or notifications, many=True)
    #     return self.get_paginated_response(serializer.data) if page else Response(serializer.data)




    # lazy loading / infinite scroll

    # Backend (API) vẫn phân trang bình thường (?page=1, ?page=2, ...)
    # Frontend (Vue/React/Next.js...) sẽ:
    # Gọi GET /api/my-notifications/?page=1 khi vừa load
    # Khi kéo xuống gần cuối danh sách → gọi GET /api/my-notifications/?page=2 để load tiếp
    # Append (nối thêm) vào danh sách đang hiển thị
    @action(detail=False, methods=['get'], url_path='my-notifications')
    def my_notifications(self, request):
        user = request.user
        events = Event.objects.filter(tickets__user=user, tickets__is_checked_in=False).distinct()
        notifications = Notification.objects.filter(event__in=events)
        page = self.paginate_queryset(notifications)
        serializer = serializers.NotificationSerializer(page or notifications, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    @action(methods=['get'], detail=False, url_path='sent-messages')
    def get_sent_messages(self, request):
        user = request.user

        messages = user.sent_messages.all().select_related('event', 'receiver')
        page = self.paginate_queryset(messages)
        serializer = serializers.ChatMessageSerializer(page or messages, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

# ViewSet cho Event
#Xem sự kiện
# Cho phép người dùng xem danh sách sự kiện và chi tiết sự kiện
# Chỉ admin và organizer mới có quyền tạo và chỉnh sửa sự kiện
class EventViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView, generics.CreateAPIView,generics.UpdateAPIView):
    queryset = Event.objects.all()
    pagination_class = ItemPaginator
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['title', 'description', 'location','category']
    ordering_fields = ['start_time', 'ticket_price']
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_serializer_class(self):
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            return EventDetailSerializer
        return EventSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'suggest_events', 'hot_events', 'get_chat_messages']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['create']:
            return [perms.IsOrganizerUser()]
        elif self.action in ['update', 'partial_update', 'my_events']:
            return [perms.IsOrganizerOwner()]
        elif self.action == 'manage_reviews':
            # GET cho phép tất cả, POST yêu cầu xác thực sẽ kiểm tra trong view
            return [permissions.AllowAny()]
        return [perms.IsAdminOrOrganizer(), perms.IsEventOrganizer()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save(organizer=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        event = self.get_object()
        serializer = EventDetailSerializer(event, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        event = self.get_object()
        serializer = EventDetailSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'attendee':
            queryset = self.queryset.all()  # xem được cả sự kiện đã kết thúc để xem review
        elif user.role == 'organizer':
            queryset = self.queryset.filter(organizer=user)
        elif user.role == 'admin':
            queryset = self.queryset.all()
        else:
            queryset = self.queryset.none()

        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q) | Q(category__icontains=q))
        return queryset

    @action(methods=['get'], detail=True, url_path='tickets')
    def get_tickets(self, request, pk):
        event = self.get_object()
        tickets = event.tickets.filter(is_paid=True).select_related('user')
        page = self.paginate_queryset(tickets)
        serializer = TicketSerializer(page or tickets, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    @action(methods=['get', 'post'], detail=True, url_path='reviews')
    def manage_reviews(self, request, pk):
        event = self.get_object()
        if request.method == 'POST':
            if not request.user.is_authenticated:
                return Response({"detail": "Yêu cầu xác thực."}, status=status.HTTP_401_UNAUTHORIZED)
            serializer = ReviewSerializer(data={
                'user': request.user.pk,
                'event': pk,
                'rating': request.data.get('rating'),
                'comment': request.data.get('comment')
            })
            serializer.is_valid(raise_exception=True)
            review = serializer.save()
            return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
        reviews = event.reviews.all().select_related('user')
        page = self.paginate_queryset(reviews)
        serializer = ReviewSerializer(page or reviews, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    @action(methods=['get'], detail=True, url_path='chat-messages')
    def get_chat_messages(self, request, pk):
        event = self.get_object()
        messages = event.chat_messages.all().select_related('sender', 'receiver')
        page = self.paginate_queryset(messages)
        serializer = ChatMessageSerializer(page or messages, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='suggest')
    def suggest_events(self, request):
        user = request.user
        user_tickets = Ticket.objects.filter(user=user).values('event__category').distinct()
        categories = [ticket['event__category'] for ticket in user_tickets]
        queryset = Event.objects.filter(
            is_active=True,
            start_time__gte=timezone.now()
        ).select_related('organizer').prefetch_related('tags')
        if categories:
            queryset = queryset.filter(category__in=categories)
        suggested_events = queryset.order_by('start_time')[:5]
        serializer = self.get_serializer(suggested_events, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='hot')
    def hot_events(self, request):
        hot_events = Event.objects.filter(
            is_active=True,
            start_time__gte=timezone.now()
        ).annotate(tickets_sold=Count('tickets', filter=Q(tickets__is_paid=True))).order_by('-tickets_sold')[:5]
        serializer = self.get_serializer(hot_events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='statistics')
    def get_statistics(self, request, pk):
        event = self.get_object()
        if not (request.user == event.organizer or request.user.role == 'admin'):
            return Response({"error": "Không có quyền truy cập."}, status=status.HTTP_403_FORBIDDEN)
        tickets_sold = event.tickets.filter(is_paid=True).count()
        revenue = sum(ticket.event.ticket_price for ticket in event.tickets.filter(is_paid=True))
        data = {
            'tickets_sold': tickets_sold,
            'revenue': revenue,
            'average_rating': event.reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        }
        return Response(data)
    @action(detail=False, methods=['get'], url_path='my-events')
    def my_events(self, request):
        """Trả về danh sách các sự kiện do organizer hiện tại tổ chức."""
        user = request.user
        if user.role != 'organizer':
            return Response({"error": "You do not have permission to view this."}, status=403)
        events = Event.objects.filter(organizer=user)
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)


# Hiển thị danh sách các tag để gợi ý sự kiện theo sở thích
class TagViewSet(viewsets.ViewSet, generics.ListAPIView,generics.CreateAPIView,generics.UpdateAPIView,generics.DestroyAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = ItemPaginator
    filter_backends = [SearchFilter]
    search_fields = ['name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [perms.IsAdminOrOrganizer()]
        elif self.action == 'destroy':
            return [perms.IsAdminUser()]
        return [permissions.AllowAny()]

# Đặt vé và xem vé
import qrcode
# pip install qrcode[pil]
from io import BytesIO
from django.core.files.base import ContentFile

from rest_framework import mixins
#TicketViewSet cho phép người dùng đặt vé cho sự kiện và xem thông tin vé của mình
class TicketViewSet(viewsets.GenericViewSet,
                    mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.CreateModelMixin):
    """
    - Admin có thể xem và thao tác tất cả vé.
    - Organizer chỉ xem và thao tác vé của sự kiện do họ tổ chức.
    - Attendee chỉ xem và thao tác vé của chính họ.
    """
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]  
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return self.queryset  # Admin có thể xem tất cả vé
            # return self.queryset.filter(user=user) #test: xem vé của admin khi admin đăng nhập
        elif user.role == 'organizer':
            # Organizer chỉ xem vé của sự kiện do họ tổ chức
            return self.queryset.filter(event__organizer=user)
        else:
            # Người dùng chỉ xem vé của chính họ
            return self.queryset.filter(user=user)

    def perform_create(self, serializer):
        # Lấy event từ request
        event_id = self.request.data.get('event_id')
        event = Event.objects.get(pk=event_id)

        # Tạo ticket trước để có uuid
        ticket = serializer.save(user=self.request.user, event=event)

        # Tạo nội dung QR code dựa trên uuid của ticket
        qr_content = str(ticket.uuid)

        # Tạo QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)

        # Lưu QR code vào file
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code_file = ContentFile(buffer.getvalue(), name=f"ticket_{ticket.uuid}.png")

        # Cập nhật lại ticket với QR code
        ticket.qr_code.save(qr_code_file.name, qr_code_file)
        ticket.save()

    @action(detail=False, methods=['post'], url_path='verify')
    def verify_ticket(self, request):
        """Xác thực vé dựa trên uuid."""
        uuid_str = request.data.get('uuid')
        if not uuid_str:
            return Response({"error": "UUID is required."}, status=400)
        try:
            ticket = Ticket.objects.get(uuid=uuid.UUID(uuid_str))
        except (Ticket.DoesNotExist, ValueError):
            return Response({"error": "Invalid ticket UUID."}, status=404)

        # Kiểm tra organizer có quyền verify vé này không
        if request.user.role == 'organizer' and ticket.event.organizer != request.user:
            return Response({"error": "You do not have permission to verify this ticket."}, status=403)

        # Kiểm tra trạng thái vé
        if not ticket.is_paid:
            return Response({"error": "Ticket is not paid."}, status=400)
        if ticket.is_checked_in:
            return Response({"error": "Ticket has already been checked in."}, status=400)

        # Nếu hợp lệ, trả về thông tin vé
        serializer = self.get_serializer(ticket)
        return Response(serializer.data, status=200)

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
    
    # giới hạn danh sách các Payment mà người dùng được phép truy cập tùy theo vai trò (role) của họ.
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return self.queryset
        elif user.role == 'organizer':
            return self.queryset.filter(user__tickets__event__organizer=user).distinct()
        return self.queryset.filter(user=user)


# Thông báo và nhắc nhở
# Hiển thị thông báo và nhắc nhở cho người dùng hiện tại
class NotificationViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    pagination_class = ItemPaginator

    def get_permissions(self):
        if self.action == 'my_notifications':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'event_notifications':
            permission_classes = [permissions.AllowAny]
        elif self.action == 'create_notification':
            permission_classes = [perms.IsEventOwnerOrAdmin]
        else:
            permission_classes = [perms.IsEventOwnerOrAdmin]
        return [permission() for permission in permission_classes]

    # Ghi đè lại để tránh sử dụng queryset mặc định trong ListAPIView 
    # → nhằm ép buộc các custom action sử dụng filter riêng theo ngữ cảnh.
    # Tránh rò rỉ toàn bộ danh sách thông báo nếu ai đó vô tình truy cập GET /notification/.  
    def get_queryset(self):
        return Notification.objects.none()
    
    # lazy loading / infinite scroll

    # Backend (API) vẫn phân trang bình thường (?page=1, ?page=2, ...)
    # Frontend (Vue/React/Next.js...) sẽ:
    # Gọi GET /api/my-notifications/?page=1 khi vừa load
    # Khi kéo xuống gần cuối danh sách → gọi GET /api/my-notifications/?page=2 để load tiếp
    # Append (nối thêm) vào danh sách đang hiển thị


    @action(detail=False, methods=['get'], url_path='event-notifications')
    def event_notifications(self, request):
        event_id = request.query_params.get('event_id')
        if not event_id:
            return Response({"error": "event_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        notifications = Notification.objects.filter(event_id=event_id)
        page = self.paginate_queryset(notifications)
        serializer = self.get_serializer(page or notifications, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='create-notification')
    def create_notification(self, request):
        event_id = request.data.get('event_id')
        title = request.data.get('title')
        message = request.data.get('message')
        notification_type = request.data.get('notification_type', 'reminder')

        if not (request.user.role in ['admin', 'organizer']):
            return Response({"error": "Không có quyền truy cập."}, status=status.HTTP_403_FORBIDDEN)

        event = None
        if event_id:
            try:
                event = Event.objects.get(id=event_id)
            except Event.DoesNotExist:
                return Response({"error": "Sự kiện không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        notification = Notification(
            event=event,
            notification_type=notification_type,
            title=title,
            message=message,
            is_read=False
        )
        notification.save()

        # Gửi email cho tất cả người dùng có vé của sự kiện
        # if event:
        #     ticket_owners = User.objects.filter(tickets__event=event).distinct()
        #     recipient_emails = [user.email for user in ticket_owners if user.email]
        #     if recipient_emails:
        #         send_mail(
        #             subject=title,
        #             message=message,
        #             from_email=settings.EMAIL_HOST_USER,
        #             recipient_list=recipient_emails,
        #             fail_silently=True
        #         )
        # chưa có chức năng gửi email cho người dùng có vé của sự kiện

        return Response({
            "message": "Thông báo đã được tạo và email đã được gửi.",
            "notification": serializers.NotificationSerializer(notification).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='mark-as-read')
    def mark_as_read(self, request, pk=None):
        try:
            notification = self.get_object()
            user_notification, created = UserNotification.objects.get_or_create(
                user=request.user, notification=notification
            )
            user_notification.is_read = True
            user_notification.read_at = timezone.now()
            user_notification.save()
            return Response({'message': 'Thông báo đã được đánh dấu là đã đọc.'})
        except Notification.DoesNotExist:
            return Response({'error': 'Không tìm thấy thông báo.'}, status=404)




# Đánh giá sự kiện
# Cho phép người dùng đánh giá và viết nhận xét về sự kiện
class ReviewViewSet(viewsets.ViewSet, generics.ListCreateAPIView, generics.UpdateAPIView,generics.DestroyAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [perms.ReviewOwner]  # Chỉ người dùng đã đăng nhập mới được sửa review

    def get_queryset(self):
        """Trả về danh sách review cho sự kiện."""
        event_id = self.request.query_params.get('event_id')
        if event_id:
            return Review.objects.filter(event_id=event_id)
        return Review.objects.all()

    def perform_create(self, serializer):
        """Gán người dùng hiện tại khi tạo review."""
        serializer.save(user=self.request.user)

    def get_view_name(self):
        return "Đánh giá sự kiện"

# Thống kê và báo cáo
# Hiển thị thống kê sự kiện của organizer, bao gồm số vé đã bán, doanh thu, và số lượt xem
class EventTrendingLogView(viewsets.ViewSet, generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới xem thống kê
    serializer_class = EventTrendingLogSerializer

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
class DiscountCodeViewSet(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView):
    queryset = DiscountCode.objects.filter(is_active=True)
    serializer_class = DiscountCodeSerializer
    pagination_class = ItemPaginator

    def get_permissions(self):
        if self.action == 'create':
            return [perms.IsAdminOrOrganizer()]
        return [permissions.IsAuthenticated()]
    
# View cho EventTrendingLog
from rest_framework import mixins, viewsets, permissions
from .perms import IsAdminUser, IsOrganizerOwner

class EventTrendingLogViewSet(mixins.ListModelMixin,
                             mixins.RetrieveModelMixin,
                             viewsets.GenericViewSet):
    queryset = EventTrendingLog.objects.all().order_by('trending_score')
    serializer_class = EventTrendingLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser | IsOrganizerOwner]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return self.queryset.order_by('trending_score')
        elif user.role == 'organizer':
            return self.queryset.filter(event__organizer=user).order_by('trending_score')
        return EventTrendingLog.objects.none()
