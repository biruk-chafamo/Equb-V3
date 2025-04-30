from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Q
from django.conf import settings
import stripe

from .serializers import *
from .models import *
from .permissions import *

stripe.api_key = settings.STRIPE_SECRET_KEY

class UserViewSet(viewsets.ModelViewSet):
    """
    users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')

    def get_permissions(self):
        if self.request.method in ['GET', 'POST']:
            return [permissions.AllowAny()]
        else:
            return [permissions.DjangoObjectPermissions()]

    def get_serializer_class(self):
        if self.request.method in ['DELETE', 'POST']:
            return RegisterUserSerializer
        if self.request.method in ['PUT', 'PATCH']:
            return EditUserSerializer
        return ListUserSerializer

    @action(detail=False, methods=['post'], url_path='createstripeaccount')
    @permission_classes([IsAuthenticated])
    def create_stripe_account(self, request):
        """
        create a stripe account for the current user
        """
        user = self.request.user
        if user.stripe_account_id:
            return Response(
                {"detail": "User already has a stripe account."},
                status=status.HTTP_400_BAD_REQUEST
            )
        account = stripe.Account.create(
            country='US',
            email=user.email,
            controller={
                "stripe_dashboard": {
                    "type": "none",
                },
            },
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True}
            },
        )
        user.stripe_account_id = account.id
        user.save()
        return Response({"account_id": account.id})

    @action(detail=False, methods=['get', 'patch', 'put'], url_path='currentuser')
    @permission_classes([IsAuthenticated])
    def current_user(self, request):
        """
        get details for the current user
        """
        user = self.request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='userprofile')
    @permission_classes([IsAuthenticated])
    def user_profile(self, request):
        """
        get user profile by id
        """
        name = request.query_params.get('id')
        if not name:
            return Response(
                {"detail": "Id is a required parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )
        user = self.get_queryset().get(id=name)
        friendsCount = user.friends.count()
        equbsCount = user.joined_equbs.count()
        serializer = self.get_serializer(user)
        return Response({
            "user": serializer.data,
            "friendsCount": friendsCount,
            "equbsCount": equbsCount
        })

    @action(detail=False, methods=['get'], url_path='friends')
    @permission_classes([IsAuthenticated])
    def friends(self, request):
        """
        get friends of the current user if no id is specified. 
        Otherwise, get friends of the user with the specified id.
        """
        id = request.query_params.get('id')
        if not id:
            user = self.request.user
        else:
            user = self.get_queryset().get(id=id)

        friends = user.friends.all()
        serializer = self.get_serializer(friends, many=True)
        return Response(serializer.data)
    
    @method_decorator(cache_page(120))
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        search for users by name paginated by 10
        """
        paginator = PageNumberPagination()
        paginator.page_size = 5
        name = request.query_params.get('name')
        if not name:
            return Response(
                {"detail": "Name is a required parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = User.objects.filter(
            Q(first_name__icontains=name) | 
            Q(last_name__icontains=name) | 
            Q(username__icontains=name)
        ).exclude(
            Q(id=request.user.id) | 
            Q(username__in=['deleted', 'AnonymousUser']) | 
            Q(is_staff=True)
        )
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

    
class EqubViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    """
    equbs joined by a user to be viewed or edited.
    """

    serializer_class = EqubSerializer

    def get_queryset(self):
        user = self.request.user
        joined_equbs = user.joined_equbs.all()
        invited_equbs = Equb.objects.filter(id__in=user.received_equbinviterequests.values_list('equb__id', flat=True))
        recommended_equbs = Equb.objects.filter(id__in=NewEqubNotification.objects.filter(receiver=user, equb__is_active=False).values_list('equb__id', flat=True))
        combined_equbs = joined_equbs | invited_equbs | recommended_equbs
        return combined_equbs.distinct()
        
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)
        
    @action(detail=False, methods=['get'], url_path='activeequbs')
    def active_equbs(self, request):
        """
        get equbs that user has joined and are active
        """
        user = self.request.user
        equbs = user.joined_equbs.filter(is_active=True, is_completed=False)
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='pendingequbs')
    def pending_equbs(self, request):
        """
        get equbs that user has joined and are not active but not completed
        """
        user = self.request.user
        equbs = user.joined_equbs.filter(is_active=False, is_completed=False)
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='invitedequbs')
    def invited_equbs(self, request):
        """
        get equbs that user has been invited to
        """
        user = self.request.user
        invitations = user.received_equbinviterequests.all()
        equbs = [invitation.equb for invitation in invitations]
        # making sure that the equbs are not active and user has not joined them
        equbs = [equb for equb in equbs if not equb.is_active and not user.joined_equbs.filter(id=equb.id).exists()]
        equbs = list(set(equbs))
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='pastequbs')
    def past_equbs(self, request):
        """
        get equbs that user has completed
        """
        user = self.request.user
        equbs = user.joined_equbs.filter(is_completed=True)
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='recommendedequbs')
    def recommended_equbs(self, request):
        """
        get new public equbs that have been created by users friends
        """
        user = self.request.user
        new_equb_notifications = NewEqubNotification.objects.filter(receiver=user, equb__is_active=False)
        equbs = [notification.equb for notification in new_equb_notifications]
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
   
    

class BidViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    """
    place and view bids for an equb.
    """

    serializer_class = BidSerializer

    def get_queryset(self):
        equbs = self.request.user.joined_equbs.all()
        if equbs is None:
            return None
        return Bid.objects.filter(equb__in=equbs) # all bids that belong to equbs joined by current user

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user, date=timezone.now(), 
            round=serializer.validated_data['equb'].balance_manager.finished_rounds + 1
        )


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
        equbs = user.joined_equbs.all()
        invites_to_joined_equbs = EqubInviteRequest.objects.filter(equb__in=equbs)
        received = user.received_equbinviterequests.all()
        return received | invites_to_joined_equbs

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in ['PUT', 'PATCH']:
            return AcceptEqubInviteRequestSerializer
        else:
            return EqubInviteRequestSerializer

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['get'], url_path='received')
    def received(self, request):
        """
        get equb invitations received by user
        """
        user = self.request.user
        invitations = user.received_equbinviterequests.filter(is_accepted=False, is_rejected=False, is_expired=False)
        # making sure that the equbs are not active and user has not joined them
        invitations = [invitation for invitation in invitations if not user.joined_equbs.filter(id=invitation.equb.id).exists()]
        serializer = self.get_serializer(invitations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='by-equb')
    def by_equb(self, request):
        """
        get equb invitations sent to anyone for a specific equb
        """
        equb_id = request.query_params.get('equb')
        if not equb_id:
            return Response(
                {"detail": "Equb is a required parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )
        invitations = EqubInviteRequest.objects.filter(equb=equb_id)
        serializer = self.get_serializer(invitations, many=True)
        return Response(serializer.data)

class FriendRequestViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        received = user.received_friendrequests.all()
        sent = user.sent_friendrequests.all()
        return received | sent

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in ['PUT', 'PATCH']:
            return AcceptFriendRequestSerializer
        else:
            return FriendRequestSerializer

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['get'], url_path='received')
    def received(self, request):
        """
        get friend requests received by user
        """
        user = self.request.user
        requests = user.received_friendrequests.filter(is_accepted=False, is_rejected=False, is_expired=False)
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='sent')
    def sent(self, request):
        """
        get friend requests sent by user
        """
        user = self.request.user
        requests = user.sent_friendrequests.filter(is_accepted=False, is_rejected=False, is_expired=False)
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)

class PaymentConfirmationRequestViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        received = user.received_paymentconfirmationrequests.all()
        sent = user.sent_paymentconfirmationrequests.all()
        return received | sent

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in ['PUT', 'PATCH']:
            return AddressPaymentConfirmationRequestSerializer
        else:
            return ListPaymentConfirmationRequestSerializer

    def perform_create(self, serializer):
        balance_manager = serializer.validated_data['equb'].balance_manager
        round = serializer.validated_data['round']
        payment_method = serializer.validated_data['payment_method']
        
        sender = self.request.user
        amount = balance_manager.calculate_losers_deductions(sender, round)
        # payment_method = sender.selected_payment_methods.get(service=service)
        
        serializer.save(
            sender=sender,
            receiver=balance_manager.wins.get(round=round).user,
            amount=amount,
            payment_method=payment_method
        )

    @action(detail=False, methods=['get'], url_path='by-equb-round')
    def get_by_equb_and_round(self, request):
        '''
        get all confirmed or unconfirmed payment confirmation requests
        for a specific equb and round. This excludes all rejected requests.
        '''
        equb_id = request.query_params.get('equb')
        round = request.query_params.get('round')

        if not equb_id or not round:
            return Response(
                {"detail": "Equb and round are required parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )
        queryset = PaymentConfirmationRequest.objects.filter(equb=equb_id, round=round, is_rejected=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class PaymentMethodViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        user = self.request.user
        return user.selected_payment_methods.all()
    
    def perform_create(self, serializer):        
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='services')
    def services(self, request):
        """
        get all available payment services as a list of strings
        """
        services = [service[0] for service in ServiceChoices.choices]
        return Response(services)
    


