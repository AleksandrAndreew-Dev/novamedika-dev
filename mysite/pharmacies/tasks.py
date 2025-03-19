from celery import shared_task
from django.core.mail import send_mail
from .models import Order

@shared_task
def order_created(order_id):
    """
    Asynchronous task to send an email notification when an order is created.
    """
    try:
        order = Order.objects.get(id=order_id)
        subject = f"Order Confirmation: #{order_id}"
        message = (
            f"Dear {order.user_name} {order.user_surname},\n\n"
            f"Thank you for your order!\n"
            f"Product: {order.product_name}\n"
            f"Price: {order.product_price}\n"
            f"Quantity: {order.quantity}\n"
            f"Pharmacy: {order.pharmacy_name} (#{order.pharmacy_number})\n\n"
            f"Your order ID is {order.id}. You will receive further updates soon."
        )
        # mail_sent = send_mail(
        #     subject,
        #     message,
        #     'admin@myshop.com',  # Replace with your "from" email address
        #     [order.user_phone],  # Replace with the recipient's email
        # )
        print(subject, message)
    except Order.DoesNotExist:
        return False
