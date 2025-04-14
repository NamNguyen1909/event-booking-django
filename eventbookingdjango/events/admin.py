from django.contrib import admin
from events.models import User, Event, Tag, Ticket, Payment, DiscountCode, Notification, Review, ChatMessage, EventTrendingLog
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count
from django.template.response import TemplateResponse
from django.urls import path

# Customize the admin interface for the Event model
class MyEventAdmin(admin.ModelAdmin): 
    list_display = ('id', 'title', 'organizer', 'start_time', 'end_time', 'total_tickets', 'ticket_price', 'location', 'Tag_list')
    list_filter = ('organizer', 'category', 'start_time', 'end_time', 'tags')
    search_fields = ('title', 'description', 'location', 'tags__name')

    def Tag_list(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()])
    Tag_list.short_description = 'Tags'

    readonly_fields = ('poster_preview',)

    def poster_preview(self, obj):
        if obj.poster:
            return mark_safe(f"<img src='{obj.poster.url}' width='300' height='300' />")
        return "No Image"
    poster_preview.short_description = 'Poster Preview'

class MyUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'phone', 'avatar', 'role')
    list_filter = ('role',)
    search_fields = ('username', 'email', 'phone')

    readonly_fields = ('avatar_preview',)
    def avatar_preview(self, obj):
        if obj.avatar:
            return mark_safe(f"<img src='{obj.avatar.url}' width='300' height='300' />")
        return "No Image"

# Statistics and reporting: Admins and organizers can view reports on ticket sales,
# revenue, and interest levels through visual charts.
class MyAdminSite(admin.AdminSite):
    site_header = "QUẢN LÝ SỰ KIỆN VÀ ĐẶT VÉ TRỰC TUYẾN"

    def get_urls(self):
        return [path('stats/', self.event_stats)] + super().get_urls()

    def event_stats(self, request):
        # Calculate total tickets sold
        total_tickets = Ticket.objects.count()
        
        # Calculate total revenue
        total_revenue = Payment.objects.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Get event popularity data
        events = Event.objects.annotate(
            tickets_sold=Count('tickets'),
            total_revenue=Sum('tickets__payment__amount')
        ).order_by('-tickets_sold')[:10]
        
        return TemplateResponse(request, 'admin/stats.html', {
            'total_tickets': total_tickets,
            'total_revenue': total_revenue,
            'events': events,
            'title': 'Event Statistics'
        })

admin_site = MyAdminSite(name='EventsAdmin')

# Register your models here.
admin_site.register(User, MyUserAdmin)
admin_site.register(Event, MyEventAdmin)
admin_site.register(Ticket)
admin_site.register(Payment)
admin_site.register(Tag)
admin_site.register(DiscountCode)
admin_site.register(Notification)
admin_site.register(Review)
admin_site.register(ChatMessage)
admin_site.register(EventTrendingLog)
