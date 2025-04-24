from django.apps import AppConfig


class PharmaciesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pharmacies'

    def ready(self):


        from . import signals
        # если сигналы в models.py


