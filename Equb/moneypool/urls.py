from django.urls import path, include
from . import views

from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'equbs', views.EqubViewSet, basename='equb')
router.register(r'equbjoinrequests', views.EqubJoinRequestViewSet, basename='equbjoinrequest')
router.register(r'equbinviterequests', views.EqubInviteRequestViewSet, basename='equbinviterequest')
router.register(r'friendrequests', views.FriendRequestViewSet, basename='friendrequest')

urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
