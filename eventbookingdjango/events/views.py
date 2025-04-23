import uuid
from django.db.models import Q, Sum, Count
from django.utils import timezone

from rest_framework import viewsets, generics, permissions, status, parsers
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from events import perms
from events.perms import IsAdminOrOrganizer, IsAdmin, IsOrganizer, ReviewOwner,IsEventOwnerOrAdmin,IsOrganizerOwner

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from events.models import (
    Event, User, Tag, Ticket, Payment, DiscountCode,
    Notification, Review, ChatMessage, EventTrendingLog
)
from events.serializers import (
    EventSerializer, EventDetailSerializer, UserSerializer, UserDetailSerializer,
    TagSerializer, TicketSerializer, PaymentSerializer, DiscountCodeSerializer,
    NotificationSerializer, ReviewSerializer, ChatMessageSerializer,
    EventStatisticSerializer, EventTrendingLogSerializer
)
from events.paginators import ItemPaginator



# Đăng ký tài khoản
class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Cho phép mọi người đăng ký tài khoản
    parser_classes = [parsers.MultiPartParser, parsers.FormParser,JSONParser]  # Cho phép upload file (avatar)

    def get_view_name(self):
        return "Đăng ký tài khoản"
    
    @action(methods=['get','patch'],url_path='current-user',detail=False,permission_classes = [permissions.IsAuthenticated]) #detail false để không lộ id => security | để permission_classes p73 đây thì chỉ có cái này cần chứng thực
    def get_current_user(self,request):
        u=request.user
        if request.method.__eq__('PATCH'): #cập nhật
            for k,v in request.data.items():
                if k in ['first_name','last_name']:
                    setattr(u,k,v) # u.k=v
                elif k.__eq__('password'):
                    u.set_password(v)
            u.save()
        return Response(UserSerializer(u).data)

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
            return [IsOrganizer()]
        elif self.action in ['update', 'partial_update', 'my_events']:
            return [IsOrganizerOwner()]
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


# Gợi ý theo sở thích
# Hiển thị danh sách các tag để gợi ý sự kiện theo sở thích
class TagViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = ItemPaginator
    permission_classes = [permissions.AllowAny]  # Cho phép mọi người xem danh sách tag

    def get_view_name(self):
        return "Danh sách Tag"

# Xem và cập nhật profile người dùng, bao gồm thay đổi password
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

class UserProfileViewSet(viewsets.ViewSet,generics.RetrieveAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

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
    permission_classes = [permissions.IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới xem thông báo

    def get_queryset(self):
        """Trả về thông báo liên quan đến các sự kiện mà người dùng có vé tham gia."""
        user = self.request.user
        # Lấy danh sách các sự kiện mà người dùng có vé
        events = Event.objects.filter(tickets__user=user).distinct()
        # Trả về thông báo liên quan đến các sự kiện đó
        return Notification.objects.filter(event__in=events)

    def get_view_name(self):
        return "Thông báo và nhắc nhở"

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
class EventTrendingLogViewSet(mixins.ListModelMixin,
                             mixins.RetrieveModelMixin,
                             mixins.CreateModelMixin,
                             mixins.UpdateModelMixin,
                             mixins.DestroyModelMixin,
                             viewsets.ViewSet):
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
