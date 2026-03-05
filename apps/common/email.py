from django.conf import settings
from django.core.mail import send_mail

from .tasks import send_email_task


def send_email(subject, message, recipients):
    if not recipients:
        return 0
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@shopkart.com'
    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        return send_mail(subject, message, from_email, recipients, fail_silently=False)
    try:
        return send_email_task.delay(subject, message, from_email, recipients)
    except Exception:
        return send_mail(subject, message, from_email, recipients, fail_silently=False)
