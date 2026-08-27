from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Q
from django.conf import settings
import stripe

from google.auth.transport import requests
from google.oauth2 import id_token
from rest_framework_simplejwt.tokens import RefreshToken
from enum import Enum

from ..serializers import *
from ...models import *
from ..permissions import *
from ..pagination import BoundedPagination
from ...services import equb_service
from ...adapters.django_notifier import default_notifier


class AuthPlatform(Enum):
    WEB = 'web'
    IOS = 'ios'
    ANDROID = 'android'
    
    @classmethod
    def get_client_id(cls, platform_value):
        """Get appropriate Google Client ID based on platform"""
        if platform_value == cls.IOS.value and hasattr(settings, 'GOOGLE_CLIENT_ID_IOS'):
            return settings.GOOGLE_CLIENT_ID_IOS
        elif platform_value == cls.ANDROID.value and hasattr(settings, 'GOOGLE_CLIENT_ID_ANDROID'):
            return settings.GOOGLE_CLIENT_ID_ANDROID
        else:
            # Default to web client ID
            return settings.GOOGLE_CLIENT_ID

stripe.api_key = settings.STRIPE_SECRET_KEY

class UserViewSet(viewsets.ModelViewSet):
    """
    users to be viewed or edited.
    """
    pagination_class = BoundedPagination
    queryset = User.objects.all().order_by('-date_joined').prefetch_related(
        'selected_payment_methods', 'friends', 'joined_equbs'
    )

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

        friends = user.friends.prefetch_related(
            'selected_payment_methods', 'friends', 'joined_equbs'
        )
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
        ).order_by('id')
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

    


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def google_auth(request):
    """
    Authenticate user with Google ID token and return JWT tokens.
    Handles email conflicts with existing password-based accounts.
    """
    # Validate request data using serializer
    from ..serializers import GoogleAuthSerializer
    serializer = GoogleAuthSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        id_token_str = serializer.validated_data['id_token']

        # Choose the correct client ID based on platform using enum
        platform = serializer.validated_data.get('platform', AuthPlatform.WEB.value)
        client_id = AuthPlatform.get_client_id(platform)

        # Verify the Google ID token
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            client_id
        )

        if not idinfo.get('email_verified'):
            return Response({
                'error': 'email_not_verified',
                'message': 'Your Google email address is not verified.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Extract user information from the verified token
        google_id = idinfo['sub']
        email = idinfo['email']
        first_name = idinfo.get('given_name', '')
        last_name = idinfo.get('family_name', '')

        # Check if user exists with this Google ID
        try:
            user = User.objects.get(google_id=google_id)
        except User.DoesNotExist:
            # Check if user exists with this email but no Google ID (password account)
            existing_user = User.objects.filter(email__iexact=email, google_id__isnull=True).first()
            if existing_user:
                return Response({
                    'error': 'account_exists_with_password',
                    'message': 'An account with this email already exists. Please sign in with your password.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user exists with this email and has Google ID (shouldn't happen, but safety check)
            existing_google_user = User.objects.filter(email=email, google_id__isnull=False).first()
            if existing_google_user:
                # Update the google_id in case it changed (rare but possible)
                existing_google_user.google_id = google_id
                existing_google_user.save()
                user = existing_google_user
            else:
                # Create new user with Google authentication
                user = User.objects.create_user(
                    username=email,  # Using email as username
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    google_id=google_id
                )
        
        # Generate JWT tokens for the user
        refresh = RefreshToken.for_user(user)
        
        # Return the tokens and user data
        from ..serializers import ListUserSerializer
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': ListUserSerializer(user, context={'request': request}).data
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        # Invalid token
        return Response({
            'error': 'invalid_token',
            'message': 'Invalid Google ID token'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        # Other errors
        return Response({
            'error': 'authentication_failed',
            'message': 'Google authentication failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def check_signin_method(request):
    """
    Check what authentication methods are available for a given email.
    Helps users understand how they should sign in.
    """
    email = request.data.get('email', '').strip().lower()
    
    if not email:
        return Response({
            'error': 'email_required',
            'message': 'Email address is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email__iexact=email)
        
        has_password = user.has_usable_password()
        has_google_signin = bool(user.google_id)
        
        # Determine primary signin method
        if has_google_signin and not has_password:
            primary_method = 'google'
            message = 'This email is registered with Google Sign-In. Please use "Continue with Google" to sign in.'
        elif has_password and not has_google_signin:
            primary_method = 'password' 
            message = 'This email uses email and password authentication.'
        elif has_password and has_google_signin:
            primary_method = 'both'
            message = 'This email can sign in with either Google or email/password.'
        else:
            # Edge case: user exists but no auth method (shouldn't happen)
            primary_method = 'none'
            message = 'Account exists but no authentication method is set up. Please contact support.'
            
        return Response({
            'exists': True,
            'has_password': has_password,
            'has_google_signin': has_google_signin,
            'primary_method': primary_method,
            'message': message,
            'can_reset_password': has_password
        })
        
    except User.DoesNotExist:
        return Response({
            'exists': False,
            'message': 'No account found with this email address.'
        })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def smart_password_reset(request):
    """
    Smart password reset that checks authentication method before sending reset email.
    Replaces the default django_rest_passwordreset endpoint with better UX.
    """
    email = request.data.get('email', '').strip().lower()
    
    if not email:
        return Response({
            'error': 'email_required',
            'message': 'Email address is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email__iexact=email)
        
        has_password = user.has_usable_password()
        has_google_signin = bool(user.google_id)
        
        if has_google_signin and not has_password:
            # Google-only user - don't send reset email
            return Response({
                'error': 'google_only_account',
                'message': 'This email is registered with Google Sign-In. Please use "Continue with Google" to sign in.',
                'signin_method': 'google'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        elif not has_password and not has_google_signin:
            # Edge case: no auth method
            return Response({
                'error': 'no_auth_method',
                'message': 'Account exists but no authentication method is set up. Please contact support.',
                'signin_method': 'none'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        elif has_password:
            # User has password - proceed with normal reset flow
            from django_rest_passwordreset.models import ResetPasswordToken
            from django_rest_passwordreset.signals import reset_password_token_created
            
            # Create reset token
            token = ResetPasswordToken.objects.create(user=user)
            
            # Send the signal to trigger email (our existing signal handler will send the email)
            reset_password_token_created.send(
                sender=smart_password_reset,
                instance=None,
                reset_password_token=token
            )
            
            message = 'Password reset email has been sent.'
            if has_google_signin:
                message += ' You can also sign in with Google.'
                
            return Response({
                'message': message,
                'signin_method': 'both' if has_google_signin else 'password'
            })
            
    except User.DoesNotExist:
        # For security, don't reveal if email exists or not
        # But provide helpful guidance
        return Response({
            'message': 'If an account with this email exists, you will receive a password reset email shortly.',
            'help': 'If you signed up with Google, try using "Continue with Google" instead.'
        })
        
    except Exception as e:
        return Response({
            'error': 'reset_failed',
            'message': 'Password reset request failed. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
