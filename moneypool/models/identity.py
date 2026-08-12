from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class User(AbstractUser):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bank_account = models.DecimalField(max_digits=13, decimal_places=2, default=0.00)
    friends = models.ManyToManyField("self", through='Friendship', blank=True)
    payment_methods = models.ManyToManyField('PaymentMethod', blank=True, related_name='users')
    stripe_account_id = models.CharField(max_length=150, blank=True)
    google_id = models.CharField(max_length=100, blank=True, null=True, unique=True, help_text="Google user ID for Google authentication")
    score = models.DecimalField(
        max_digits=3, decimal_places=2, default=4, 
        validators=[MinValueValidator(0.01), MaxValueValidator(5.00)]
    )

    def delete(self, *args, **kwargs):
        for equb in (self.joined_equbs.all() | self.created_equbs.all()):
            if equb.is_active and not equb.is_completed:
                raise NotImplementedError("Cannot delete user that is part of active equbs.") # Todo Change error type
        super().delete()

    def remove_friend(self, friend: 'User') -> None:
        self.friends.remove(friend)

    class Meta:
        indexes = [
            models.Index(fields=['first_name']),
            models.Index(fields=['last_name']),
            models.Index(fields=['username']),
        ]

class ServiceChoices(models.TextChoices):
        VENMO = 'Venmo', 'Venmo'
        PAYPAL = 'PayPal', 'PayPal'
        CASHAPP = 'CashApp', 'CashApp'
        CASH = 'Cash', 'Cash'
        ZELLE = 'Zelle', 'Zelle'
        BANK_TRANSFER = 'Bank Transfer', 'Bank Transfer'

class PaymentMethod(models.Model):
    service = models.CharField(max_length=150, choices=ServiceChoices.choices)
    detail = models.CharField(max_length=150, default='')
    user = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='selected_payment_methods')

    def __str__(self):
        return f"{self.get_service_display()}: {self.detail}"
    
    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(fields=['user', 'service', 'detail'], name='unique_user_service')
    #     ]

class Friendship(models.Model):
    friend = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='friendships')
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date_joined']

    # TODO removing friend


def deleted_user():
    return User.objects.get_or_create(username='deleted', first_name='deleted', last_name='deleted')[0]
