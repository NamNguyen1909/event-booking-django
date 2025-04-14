from django.urls import path,include
from . import views
from rest_framework.routers import DefaultRouter


router=DefaultRouter()
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'tags',views.TagViewSet,basename='tag')
router.register(r'users',views.UserViewSet,basename='user')

urlpatterns = [
    # path('', views.index),
    path('',include(router.urls)),
]