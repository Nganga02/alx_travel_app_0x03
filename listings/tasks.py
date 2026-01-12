from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_kwargs={"max_retries": 3})
def send_booking_confirmation_email(self, recipient_email, booking_id):
    subject = "Booking Confirmation"
    message = f"""
    Your booking has been confirmed!

    Booking ID: {booking_id}

    Thank you for choosing ALX Travel.
    """

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        fail_silently=False,
    )
