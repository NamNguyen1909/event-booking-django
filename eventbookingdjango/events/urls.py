from .views import PaymentViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Định nghĩa router cho các ViewSet
router = DefaultRouter()
router.register('users', views.UserViewSet, basename='user')
router.register('events', views.EventViewSet, basename='event')
router.register('tags', views.TagViewSet, basename='tag')
router.register('tickets', views.TicketViewSet, basename='ticket')
router.register('payments', views.PaymentViewSet, basename='payment')
router.register('discount-codes', views.DiscountCodeViewSet, basename='discount-code')
router.register('notifications', views.NotificationViewSet, basename='notification')
router.register('chat-messages', views.ChatMessageViewSet, basename='chat-message')
router.register('event-trending-logs', views.EventTrendingLogViewSet, basename='event-trending-log')
router.register('reviews', views.ReviewViewSet, basename='review')

# Định nghĩa các URL patterns
urlpatterns = [
    path('', include(router.urls)),
    path('payments/webhook/', PaymentViewSet.as_view({'post': 'payment_webhook'}), name='payment-webhook'),
]
