# from django.shortcuts import render
# from django.http import HttpResponse

# # Create your views here.

# def index(request):
#     return HttpResponse("Hello, this is Event management and booking")

from events import serializers,paginators
from events.models import Event, User, Tag, Ticket, Payment, DiscountCode, Notification, Review, ChatMessage, EventTrendingLog
from rest_framework import viewsets, generics

class EventViewSet(viewsets.ModelViewSet):# Sử dụng ModelViewSet để cung cấp các phương thức CRUD cho mô hình Event
    queryset = Event.objects.filter(is_active=True)
    serializer_class = serializers.EventSerializer
    pagination_class = paginators.ItemPaginator  # Sử dụng phân trang tùy chỉnh


    def get_view_name(self):
        return "Danh sách sự kiện"  # Tiêu đề mới thay cho tiêu đề mặc định của viewset

class TagViewSet(viewsets.ViewSet,generics.ListAPIView): # Sử dụng ListAPIView để chỉ định rằng đây là một view chỉ hiển thị danh sách
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer
    pagination_class = paginators.ItemPaginator  # Sử dụng phân trang tùy chỉnh

    def get_view_name(self):
        return "Danh sách Tag"  # Tiêu đề mới thay cho tiêu đề mặc định của viewset
class UserViewSet(viewsets.ViewSet,generics.CreateAPIView):# Sử dụng CreateAPIView để chỉ định rằng đây là một view chỉ cho phép tạo mới
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer

    def get_view_name(self):
        return "Đăng ký tài khoản"  # Tiêu đề mới thay cho tiêu đề mặc định của viewset