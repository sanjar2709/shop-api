from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PAID = 'paid', _('Paid')
        SHIPPED = 'shipped', _('Shipped')
        DELIVERED = 'delivered', _('Delivered')
        CANCELLED = 'cancelled', _('Cancelled')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name=_('User'),
    )
    status = models.CharField(_('Status'), max_length=20, choices=Status.choices, default=Status.PENDING)
    total_price = models.DecimalField(_('Total price'), max_digits=12, decimal_places=2, default=0)
    shipping_address = models.TextField(_('Shipping address'))
    phone = models.CharField(_('Phone'), max_length=20)
    comment = models.TextField(_('Comment'), blank=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')
        indexes = (
            models.Index(fields=('user', 'status')),
            models.Index(fields=('status', 'created_at')),
        )

    def __str__(self):
        return f'Order #{self.pk}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name=_('Order'))
    # Product can be deleted later, so title and price are copied at checkout time
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items',
        verbose_name=_('Product'),
    )
    product_title = models.CharField(_('Product title'), max_length=200)
    price = models.DecimalField(_('Price'), max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(_('Quantity'), validators=(MinValueValidator(1),))

    class Meta:
        verbose_name = _('Order item')
        verbose_name_plural = _('Order items')

    def __str__(self):
        return f'{self.product_title} x {self.quantity}'

    @property
    def subtotal(self):
        return self.price * self.quantity
