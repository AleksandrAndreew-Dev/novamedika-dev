from django.core.mail import send_mail
from django.conf import settings


def send_test_email():
    subject = 'Тестовое письмо'
    message = 'Это тестовое письмо.'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = ['recipient_email@example.com']

    send_mail(subject, message, email_from, recipient_list)