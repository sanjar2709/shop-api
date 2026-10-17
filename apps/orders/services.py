from django.db import transaction
from django.db.models import F
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from apps.cart.models import CartItem
from apps.catalog.models import Product

from .models import Order, OrderItem
from .tasks import send_order_email

# Which status can follow which. Anything else is rejected.
ALLOWED_TRANSITIONS = {
    Order.Status.PENDING: (Order.Status.PAID, Order.Status.CANCELLED),
    Order.Status.PAID: (Order.Status.SHIPPED, Order.Status.CANCELLED),
    Order.Status.SHIPPED: (Order.Status.DELIVERED,),
    Order.Status.DELIVERED: (),
    Order.Status.CANCELLED: (),
}


@transaction.atomic
def create_order(user, *, shipping_address, phone, comment=''):
    cart_items = list(CartItem.objects.filter(cart__user=user))
    if not cart_items:
        raise ValidationError({'cart': _('Your cart is empty.')})

    # Lock the product rows until the transaction ends, so two customers
    # can't buy the last item at the same time. Locking in id order avoids deadlocks.
    product_ids = sorted(item.product_id for item in cart_items)
    products = Product.objects.select_for_update().filter(pk__in=product_ids).order_by('pk').in_bulk()

    errors = []
    for item in cart_items:
        product = products.get(item.product_id)
        if product is None or not product.is_active:
            errors.append(_('Product is no longer available.'))
        elif product.stock < item.quantity:
            errors.append(
                _('"%(title)s": only %(stock)s left in stock.') % {'title': product.title, 'stock': product.stock}
            )
    if errors:
        raise ValidationError({'cart': errors})

    order = Order.objects.create(user=user, shipping_address=shipping_address, phone=phone, comment=comment)

    order_items = []
    total = 0
    for item in cart_items:
        product = products[item.product_id]
        order_items.append(OrderItem(
            order=order,
            product=product,
            product_title=product.title,
            price=product.price,
            quantity=item.quantity,
        ))
        total += product.price * item.quantity
        Product.objects.filter(pk=product.pk).update(stock=F('stock') - item.quantity)

    OrderItem.objects.bulk_create(order_items)
    order.total_price = total
    order.save(update_fields=('total_price', 'updated_at'))

    CartItem.objects.filter(cart__user=user).delete()

    # Send the email only after the order is really saved
    transaction.on_commit(lambda: send_order_email.delay(order.pk, order.status))
    return order


@transaction.atomic
def change_status(order, new_status):
    order = Order.objects.select_for_update().get(pk=order.pk)

    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise ValidationError({
            'status': _('Cannot change status from "%(old)s" to "%(new)s".') % {'old': order.status, 'new': new_status}
        })

    if new_status == Order.Status.CANCELLED:
        # Put the items back in stock
        for item in order.items.exclude(product=None):
            Product.objects.filter(pk=item.product_id).update(stock=F('stock') + item.quantity)

    order.status = new_status
    order.save(update_fields=('status', 'updated_at'))

    transaction.on_commit(lambda: send_order_email.delay(order.pk, new_status))
    return order
