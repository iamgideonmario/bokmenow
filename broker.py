import os
from celery import Celery

celery_app = Celery(
    "booking",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

@celery_app.task(bind=True, max_retries=3)
def send_confirmation_email(self, booking_id):
    try:
        print(f"[MOCK EMAIL] Booking {booking_id} confirmed")
        # In production, integrate SendGrid/Mailgun here
        return True
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)