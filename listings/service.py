import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from . import models


try:
    SECRET = settings.CHAPA_SECRET_KEY
    CHAPA_API = settings.CHAPA_API_KEY
except AttributeError as e:
    raise ImproperlyConfigured(f"One or more chapa config missing {e}, please check in your settings file")


class ChapaAPIService:
    @classmethod
    def get_headers(cls) -> dict:
        return {
            'Content-type': 'application/json',
            'Authorization': f'Bearer {SECRET}'
        }

    @classmethod
    def get_base_url(cls) -> str:
        return CHAPA_API

    @classmethod
    def send_request(cls, transaction: models.Payment, update_record=True) -> dict:
        data = {
            'amount': transaction.amount,
            'currency': transaction.currency,
            'email': transaction.email,
            'first_name': transaction.first_name,
            'last_name': transaction.last_name,
            'tx_ref': transaction.id.__str__(),
            'phone_number': transaction.phone_number
        }

        transaction_url = f'{cls.get_base_url()}/transaction/initialize'
        response = requests.post(transaction_url, json=data, headers=cls.get_headers())

        data = response.json()
        if data and data.get('status') == 'success' and update_record:
            transaction.status = transaction.PENDING
            transaction.checkout_url = data.get('data').get('checkout_url')
            transaction.save()

        return data
    
    @classmethod
    def verify_payment(cls, transaction: models.Payment) -> dict:
        response = requests.get(
            f'{cls.get_base_url()}/transaction/verify/{transaction.id}',
            headers=cls.get_headers(),
        )
        return response.json()