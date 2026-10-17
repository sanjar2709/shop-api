from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel


class Cart(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name=_('User'),
    )

    class Meta:
        verbose_name = _('Cart')
        verbose_name_plural = _('Carts')

    def __str__(self):
        return f'Cart of {self.user}'

    @property
    def total_price(self):
        return sum((item.subtotal for item in self.items.all()), 0)


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name=_('Cart'))
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, verbose_name=_('Product'))
    quantity = models.PositiveIntegerField(_('Quantity'), default=1, validators=(MinValueValidator(1),))

    class Meta:
        ordering = ('created_at',)
        verbose_name = _('Cart item')
        verbose_name_plural = _('Cart items')
        constraints = (
            models.UniqueConstraint(fields=('cart', 'product'), name='unique_product_in_cart'),
        )

    def __str__(self):
        return f'{self.product} x {self.quantity}'

    @property
    def subtotal(self):
        return self.product.price * self.quantity
