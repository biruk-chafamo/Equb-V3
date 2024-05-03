from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.response import Response

from .serializers import *
from .models import *
from .permissions import *


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')

    def get_permissions(self):
        if self.request.method in ['GET', 'POST']:
            return [permissions.AllowAny()]
        else:
            return [permissions.DjangoObjectPermissions()]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE', 'POST']:
            return RegisterUserSerializer
        # if self.request.method in ['PUT']:
        #     return UserSerializer
        return ListUserSerializer


class EqubViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows equbs joined by a user to be viewed or edited.
    """

    serializer_class = EqubSerializer

    def get_queryset(self):
        user = self.request.user
        return user.joined_equbs.all()  # TODO: include invited equbs and recommended equbs to queryset for 'GET'

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


class EqubJoinRequestViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):

    def get_queryset(self):
        user = self.request.user
        return user.received_equbjoinrequests  # TODO: include sent_equbjoinrequests

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in ['PUT', 'PATCH']:
            return AcceptEqubJoinRequestSerializer
        else:
            return EqubJoinRequestSerializer

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user, receiver=serializer.validated_data['equb'].creator)


class EqubInviteRequestViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):

    def get_queryset(self):
        user = self.request.user
        return user.received_equbinviterequests  # TODO: include sent_equbinviterequests

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in ['PUT', 'PATCH']:
            return AcceptEqubInviteRequestSerializer
        else:
            return EqubInviteRequestSerializer

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)


class FriendRequestViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return user.received_friendrequests

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in ['PUT', 'PATCH']:
            return AcceptFriendRequestSerializer
        else:
            return FriendRequestSerializer

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

