from django.apps import AppConfig

class MoneypoolConfig(AppConfig):
    name = 'moneypool'

    def ready(self):
        import moneypool.signals