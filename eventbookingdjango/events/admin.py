from django.contrib import admin
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe
from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.urls import path
from .models import (
    User, Event, Tag, Ticket, Payment, Review, DiscountCode, Notification,
    ChatMessage, EventTrendingLog, UserNotification
)

# Form tùy chỉnh cho Event
class EventForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorUploadingWidget, required=False)

    class Meta:
        model = Event
        fields = '__all__'

# Form tùy chỉnh cho Notification
class NotificationForm(forms.ModelForm):
    message = forms.CharField(widget=CKEditorUploadingWidget, required=False)

    class Meta:
        model = Notification
        fields = '__all__'

# Form tùy chỉnh cho ChatMessage
class ChatMessageForm(forms.ModelForm):
    message = forms.CharField(widget=CKEditorUploadingWidget)

    class Meta:
        model = ChatMessage
        fields = '__all__'

# Admin cho User
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'role', 'total_spent', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'phone']
    list_filter = ['role', 'is_active', 'created_at']
    readonly_fields = ['avatar_view', 'total_spent']
    list_per_page = 20

    def avatar_view(self, user):
        if user.avatar:
            return mark_safe(f"<img src='{user.avatar.url}' width='200' />")
        return "Không có ảnh đại diện"
    avatar_view.short_description = "Avatar"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('tags')

# Admin cho Event
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'start_time', 'organizer', 'is_active', 'total_tickets', 'sold_tickets']
    search_fields = ['title', 'description', 'location']
    list_filter = ['category', 'is_active', 'start_time']
    readonly_fields = ['poster_view', 'sold_tickets']
    form = EventForm
    list_per_page = 20

    def poster_view(self, event):
        if event.poster:
            return mark_safe(f"<img src='{event.poster.url}' width='200' />")
        return "Không có poster"
    poster_view.short_description = "Poster"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organizer').prefetch_related('tags')

    class Media:
        css = {
            'all': ('/static/css/admin_styles.css',)
        }

# Admin cho Tag
class TagAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']
    list_per_page = 20

# Admin cho Ticket
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'event', 'user', 'qr_code_view', 'is_paid', 'is_checked_in', 'created_at']
    search_fields = ['event__title', 'user__username', 'uuid']
    list_filter = ['is_paid', 'is_checked_in', 'created_at']
    readonly_fields = ['qr_code_view']
    list_per_page = 20

    def qr_code_view(self, ticket):
        if ticket.qr_code:
            return mark_safe(f"<img src='{ticket.qr_code.url}' width='100' />")
        return "Không có QR code"
    qr_code_view.short_description = "QR Code"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event', 'user')

# Admin cho Payment
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'payment_method', 'status', 'paid_at']
    search_fields = ['user__username', 'transaction_id']
    list_filter = ['payment_method', 'status', 'paid_at']
    readonly_fields = ['transaction_id']
    list_per_page = 20

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'discount_code').prefetch_related('tickets')

# Admin cho Review
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'event', 'user', 'rating', 'comment', 'created_at']
    search_fields = ['event__title', 'user__username', 'comment']
    list_filter = ['rating', 'created_at']
    list_per_page = 20

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event', 'user')

# Admin cho DiscountCode
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'discount_percentage', 'user_group', 'is_active', 'valid_from', 'valid_to']
    search_fields = ['code']
    list_filter = ['user_group', 'is_active', 'valid_from', 'valid_to']
    list_editable = ['is_active']
    list_per_page = 20

# Admin cho Notification
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'event', 'notification_type', 'title', 'created_at', 'get_ticket_owners', 'get_is_read_status']
    search_fields = ['title', 'message']
    list_filter = ['notification_type', 'created_at']
    form = NotificationForm
    list_per_page = 20

    def get_ticket_owners(self, obj):
        if obj.event:
            ticket_owners = Ticket.objects.filter(event=obj.event).values_list('user__username', flat=True).distinct()
            return ", ".join(ticket_owners) or "No users"
        return "No event"
    get_ticket_owners.short_description = "Ticket Owners"

    def get_is_read_status(self, obj):
        """
        Hiển thị trạng thái is_read của thông báo dựa trên UserNotification.
        Nếu có ít nhất một UserNotification liên quan chưa đọc, trả về 'Chưa đọc'.
        """
        user_notifications = obj.user_notifications.all()
        if not user_notifications.exists():
            return "Không có người nhận"
        if user_notifications.filter(is_read=False).exists():
            return "Chưa đọc"
        return "Đã đọc"
    get_is_read_status.short_description = "Trạng thái đọc"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event')

# Admin cho ChatMessage
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'event', 'sender', 'receiver', 'message_preview', 'is_from_organizer', 'created_at']
    search_fields = ['message', 'sender__username', 'receiver__username', 'event__title']
    list_filter = ['is_from_organizer', 'created_at']
    form = ChatMessageForm
    list_per_page = 20

    def message_preview(self, obj):
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    message_preview.short_description = "Message Preview"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event', 'sender', 'receiver')

# Admin cho EventTrendingLog
class EventTrendingLogAdmin(admin.ModelAdmin):
    list_display = ['get_event_id', 'event', 'view_count', 'get_ticket_sold_count', 'total_revenue', 'trending_score', 'interest_score', 'last_updated']
    search_fields = ['event__title']
    list_filter = ['last_updated']
    list_per_page = 20

    def get_event_id(self, obj):
        return obj.event.id

    get_event_id.short_description = 'Event ID'

    def get_ticket_sold_count(self, obj):
        return obj.event.sold_tickets
    get_ticket_sold_count.short_description = "Tickets Sold"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event')

# Admin cho UserNotification
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'notification', 'is_read', 'read_at', 'created_at']
    search_fields = ['user__username', 'notification__title']
    list_filter = ['is_read', 'created_at']
    list_per_page = 20

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'notification')

# Custom Admin Site
class MyAdminSite(admin.AdminSite):
    site_header = 'Hệ Thống Quản Lý Sự Kiện'
    site_title = 'Quản Trị Sự Kiện'
    index_title = 'Chào Mừng Đến Với Trang Quản Trị Sự Kiện'

    def get_urls(self):
        return [
            path('event-stats/', self.event_stats, name='event-stats'),
        ] + super().get_urls()

    def event_stats(self, request):
        # Thống kê số lượng sự kiện theo danh mục
        event_stats = Event.objects.values('category').annotate(event_count=Count('id')).order_by('category')
        # Thống kê số lượng vé đã bán theo sự kiện
        ticket_stats = Event.objects.annotate(
            ticket_count=Count('tickets', filter=Q(tickets__is_paid=True))
        ).values('title', 'ticket_count')
        # Thống kê lượt xem và xu hướng
        trending_stats = EventTrendingLog.objects.values('event__title', 'view_count', 'total_revenue', 'trending_score', 'interest_score')

        return TemplateResponse(request, 'admin/event_stats.html', {
            'event_stats': event_stats,
            'ticket_stats': ticket_stats,
            'trending_stats': trending_stats,
        })

# Khởi tạo admin site
admin_site = MyAdminSite(name='event_admin')

# Đăng ký các model
admin_site.register(User, UserAdmin)
admin_site.register(Event, EventAdmin)
admin_site.register(Tag, TagAdmin)
admin_site.register(Ticket, TicketAdmin)
admin_site.register(Payment, PaymentAdmin)
admin_site.register(Review, ReviewAdmin)
admin_site.register(DiscountCode, DiscountCodeAdmin)
admin_site.register(Notification, NotificationAdmin)
admin_site.register(ChatMessage, ChatMessageAdmin)
admin_site.register(EventTrendingLog, EventTrendingLogAdmin)
admin_site.register(UserNotification, UserNotificationAdmin)