import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Order

logger = logging.getLogger(__name__)


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_order_email(order_id, status):
    # Status is passed in, because by the time the task runs the order may have changed again
    order = Order.objects.select_related('user').prefetch_related('items').filter(pk=order_id).first()
    if order is None:
        return
    status_label = Order.Status(status).label

    lines = [f'- {item.product_title} x {item.quantity} = {item.subtotal}' for item in order.items.all()]
    message = '\n'.join((
        f'Order #{order.pk} status: {status_label}',
        '',
        *lines,
        '',
        f'Total: {order.total_price}',
    ))
    send_mail(
        subject=f'Order #{order.pk}: {status_label}',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=(order.user.email,),
    )


@shared_task
def cancel_unpaid_orders():
    """Cancel orders that were not paid in time and return their items to stock."""
    from .services import change_status

    deadline = timezone.now() - timedelta(minutes=settings.ORDER_PAYMENT_TIMEOUT_MINUTES)
    order_ids = Order.objects.filter(status=Order.Status.PENDING, created_at__lt=deadline).values_list('pk', flat=True)

    cancelled = 0
    for order_id in list(order_ids):
        with transaction.atomic():
            # The customer may have paid while we were looping, so check again under the lock
            order = Order.objects.select_for_update().get(pk=order_id)
            if order.status != Order.Status.PENDING:
                continue
            change_status(order, Order.Status.CANCELLED)
            cancelled += 1

    if cancelled:
        logger.info('Cancelled %s unpaid orders', cancelled)
    return cancelled
