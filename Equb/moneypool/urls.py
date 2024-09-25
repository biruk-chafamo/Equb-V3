from django.urls import path, include
from . import views

from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'equbs', views.EqubViewSet, basename='equb')
router.register(r'equbjoinrequests', views.EqubJoinRequestViewSet, basename='equbjoinrequest')
router.register(r'equbinviterequests', views.EqubInviteRequestViewSet, basename='equbinviterequest')
router.register(r'friendrequests', views.FriendRequestViewSet, basename='friendrequest')
router.register(r'bids', views.BidViewSet, basename='bid')
router.register(r'paymentconfirmationrequest', views.PaymentConfirmationRequestViewSet, basename='paymentconfirmationrequest')
router.register(r'paymentmethods', views.PaymentMethodViewSet, basename='paymentmethod')


urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api-auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api-auth/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    
]
