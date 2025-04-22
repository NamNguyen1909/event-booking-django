from django.urls import path, include
from rest_framework.routers import DefaultRouter
from events import views

router = DefaultRouter()
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'tags', views.TagViewSet, basename='tag')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'tickets', views.TicketViewSet, basename='ticket')
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'discount_codes', views.DiscountCodeViewSet, basename='discount_code')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'reviews', views.ReviewViewSet, basename='review')
router.register(r'chat_messages', views.ChatMessageViewSet, basename='chat_message')
router.register(r'event_trending_logs', views.EventTrendingLogViewSet, basename='event_trending_log')
router.register(r'user-profile', views.UserProfileViewSet, basename='user-profile')

urlpatterns = [
    path('', include(router.urls)),
    path('event_statistics/', views.OrganizerEventStatisticsView.as_view(), name='event_statistics'),
]
