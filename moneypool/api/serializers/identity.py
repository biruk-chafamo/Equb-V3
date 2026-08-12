from datetime import timedelta
from decimal import Decimal

from rest_framework import serializers

from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile

from ...models import *
from ...domain import validation


class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'url', 'username', 'first_name', 'last_name',
            'email', 'password', 'password2', 'bank_account', 'profile_picture'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        profile_picture = data.get('profile_picture')
        if profile_picture is not None:
            data['profile_picture'] = self.context['request'].build_absolute_uri(profile_picture)
        else:   
            data['profile_picture'] = None

        return data


    def validate(self, attrs):
        # not setting uniquness an non-null constraint in the ORM to avoid back filling the database
        if validation.is_blank_email(attrs.get('email')):
            raise serializers.ValidationError({"email": "This field may not be blank."})
        if User.objects.filter(email=attrs.get('email')).exists():
            raise serializers.ValidationError({"email": "This email is already used by a different account."})

        if not validation.passwords_match(attrs.get('password'), attrs.get('password2')):
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', '')
        validated_data.pop('password2', '')

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

    #  TODO: update (put requests) dont work. The problem is password

    # def update(self, instance, validated_data):
    #     password = validated_data.pop('password', '')
    #     validated_data.pop('password2', '')
    #     user = User.objects.create(**validated_data)
    #     if password:
    #         user.set_password(validated_data['password'])
    #     user.save()
    #     return user

class FriendshipSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Friendship
        fields = ['id', 'url', 'friend']

class PaymentMethodSerializer(serializers.HyperlinkedModelSerializer):
    def validate(self, attrs):
        user = self.context.get('request').user
        service = attrs.get('service')
        detail = attrs.get('detail')
        
        if PaymentMethod.objects.filter(user=user, service=service, detail=detail).exists():
            raise serializers.ValidationError(
                'A payment method with this user, service, and detail already exists.'
            )
        return attrs
    class Meta:
        model = PaymentMethod
        fields = ['id', 'url', 'user', 'service', 'detail']
        read_only_fields = ['id', 'user']

class ListUserSerializer(serializers.HyperlinkedModelSerializer):
    selected_payment_methods = PaymentMethodSerializer(many=True, read_only=True)
    joined_equbs = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    friends = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    class Meta:
        model = User
        fields = ['id', 'url', 'username', 'first_name', 'last_name', 'friends', 'score', 'selected_payment_methods', 'joined_equbs', 'profile_picture']  # TODO: remove friends from list
        read_only_fields = ['first_name', 'last_name', 'friends', 'score', 'joined_equbs']


class EditUserSerializer(serializers.HyperlinkedModelSerializer):
    selected_payment_methods = PaymentMethodSerializer(many=True, read_only=True)
    joined_equbs = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    friends = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    class Meta:
        model = User
        fields = ['id', 'url', 'username', 'first_name', 'last_name', 'email', 'bank_account', 'profile_picture', 'score', 'selected_payment_methods', 'friends', 'joined_equbs']
        read_only_fields = ['id', 'username', 'score', 'selected_payment_methods', 'friends', 'joined_equbs']


class GoogleAuthSerializer(serializers.Serializer):
    """
    Serializer for Google authentication requests.
    This makes the DRF browsable API show proper form fields.
    """
    id_token = serializers.CharField(
        required=True,
        help_text="Google ID token received from Google Sign-In",
        style={'placeholder': 'Google ID token...'}
    )
    PLATFORM_CHOICES = [
        ('web', 'Web'),
        ('ios', 'iOS'),
        ('android', 'Android'),
    ]

    platform = serializers.ChoiceField(
        choices=PLATFORM_CHOICES,
        required=False,
        default='web',
        help_text="Platform: web, ios, or android",
        style={'placeholder': 'web, ios, or android'}
    )
