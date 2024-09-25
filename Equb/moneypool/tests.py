import json

from django.urls import reverse
from django.test.client import RequestFactory
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from decimal import Decimal

from .serializers import *
from .models import *
from .tasks import select_winner_task

class ActivateEqubTestCase(APITestCase):
    equb_list_url = reverse('equb-list')
    equb_join_request_list_url = reverse('equbinviterequest-list')
    
    def setUp(self):
        self.users = {}
        self.user_urls = {}
        for idx in range(3):
            user = User.objects.create_user(
                username=f'test_user_{idx}', email=f'test_{idx}@gamil.com',
                first_name=f'test_first_name_{idx}', last_name=f'test_last_name_{idx}',
                password=f'test_password_{idx}', bank_account=Decimal('100.00')
            )
            self.users[idx] = user
            self.user_urls[idx] = Util.get_test_object_url('User', user)

        self.client.login(username='test_user_0', password='test_password_0')

    def tearDown(self):
        User.objects.all().delete()
        Equb.objects.all().delete()
        BalanceManager.objects.all().delete()
        HighestBid.objects.all().delete()
        Bid.objects.all().delete()
        PaymentConfirmationRequest.objects.all().delete()
        OutBidNotification.objects.all().delete()
        EqubInviteRequest.objects.all().delete()
        Win.objects.all().delete()

    def test_create_equb_authenticated(self):
        """
        Ensure we can create a new equb object.
        """
        data = {'name': 'test_equb', 'max_members': 3, 'amount': 100, 'cycle': "00:10:00", 'is_private': False}
        response = self.client.post(self.equb_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_equb_invite_authenticated(self):
        # creating equb by authenticated user, test_user_0
        data = {'name': 'test_equb', 'max_members': 2, 'amount': 100, 'cycle': "00:10:00", 'is_private': False}
        self.client.post(self.equb_list_url, data)
        
        # inviting test_user_1 to join the equb
        equb = Equb.objects.get(name='test_equb')
        data = {'equb': Util.get_test_object_url('Equb', equb), 'receiver': self.user_urls[1]}
        response = self.client.post(self.equb_join_request_list_url, data)
        
        # checking if the invite request was created
        self.assertEqual(EqubInviteRequest.objects.filter(equb=equb, receiver=self.users[1]).count(), 1)

        # logging in test_user_1 to accept invitation to join equb
        self.client.login(username='test_user_1', password='test_password_1')
        response.data.update({'is_accepted': True})
        self.client.put(response.data['url'], response.data)  # accepting connection request

        equb = Equb.objects.get(name='test_equb')
        # checking if test_user_1 joined equb
        self.assertEqual(equb.members.all().count(), 2) 
        # checking if equb is active because max_members is reached
        self.assertEqual(equb.is_active, True)
        # checking if balance manager is initialized because equb is active
        self.assertEqual(equb.balance_manager.finished_rounds, 0) 

    def test_equb_bid(self):
        # calling test_create_equb_invite_authenticated to create equb and invite test_user_1
        self.test_create_equb_invite_authenticated()
        equb = Equb.objects.get(name='test_equb')
        self.assertEqual(equb.members.all().count(), 2) 

        data = {
            'equb': Util.get_test_object_url('Equb', equb), 
            'amount': 0.1, 'round': 1
        }
        response = self.client.post(reverse('bid-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(HighestBid.objects.get(equb=equb).bid.amount, Decimal('0.10'))
        self.assertEqual(OutBidNotification.objects.all().count(), equb.members.all().count())

        # outbidding test_user_0
        self.client.login(username='test_user_1', password='test_password_1')
        data = {
            'equb': Util.get_test_object_url('Equb', equb), 
            'amount': 0.2, 'round': 1
        }
        response = self.client.post(reverse('bid-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(HighestBid.objects.get(equb=equb).bid.amount, Decimal('0.20'))
        self.assertEqual(OutBidNotification.objects.all().count(), 2 * equb.members.all().count())

        # force background task to update winner account and make sure test_user_1 is the winner
        # because test_user_1 outbid test_user_0
        select_winner_task.now(equb.name)
        equb = Equb.objects.get(name='test_equb')
        self.assertEqual(equb.balance_manager.received.all()[0].username, 'test_user_1')
        

    def test_equb_payment_request(self):
        # calling test_create_equb_invite_authenticated to create equb and invite test_user_1
        self.test_create_equb_invite_authenticated()
        equb = Equb.objects.get(name='test_equb')
        self.assertEqual(equb.members.all().count(), 2) 

        # making test_user_0 win equb by bidding for the first round
        self.client.login(username='test_user_0', password='test_password_0')
        data = {'equb': Util.get_test_object_url('Equb', equb), 'amount': 0.9, 'round': 1}
        response = self.client.post(reverse('bid-list'), data)
        select_winner_task.now(equb.name) # this will make user 0 the winner

        # sending a payment confirmation request from user_1 to user_0
        self.client.login(username='test_user_1', password='test_password_1')
        data = {'equb': Util.get_test_object_url('Equb', equb), 'round': 1}
        response = self.client.post(reverse('paymentconfirmationrequest-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            PaymentConfirmationRequest.objects.get(equb=equb, sender=self.users[1]).amount, 
            equb.balance_manager.calculate_losers_deductions(member=self.users[1], round=1)
        )

        # starting off round 2 by making user_0 accept payment confirmation request from user_1
        self.client.login(username='test_user_0', password='test_password_0')
        self.client.put(response.data['url'], {'is_accepted': True})
        
        select_winner_task.now(equb.name) # this will make user_1 the winner
        
        # sending a payment confirmation request from user_0 to user_1
        data = {'equb': Util.get_test_object_url('Equb', equb), 'round': 2}
        response = self.client.post(reverse('paymentconfirmationrequest-list'), data)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            PaymentConfirmationRequest.objects.get(equb=equb, sender=self.users[0]).amount, 
            equb.balance_manager.calculate_losers_deductions(member=self.users[0], round=2)
        )

        # completing equb by making user_1 accept payment confirmation request from user_0
        self.client.login(username='test_user_1', password='test_password_1')
        self.client.put(response.data['url'], {'is_accepted': True})
        equb = Equb.objects.get(name='test_equb')
        self.assertEqual(equb.balance_manager.finished_rounds, 2)
        self.assertEqual(equb.is_completed, True)


class Util:
    @staticmethod
    def get_test_object_url(model_name: str, instance):
        model_name = model_name.lower()
        return 'http://testserver' + reverse(f'{model_name}-detail', kwargs={'pk': instance.pk})
