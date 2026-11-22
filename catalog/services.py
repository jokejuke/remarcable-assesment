"""Order placement: all-or-nothing, without overselling."""

from django.db import transaction
from django.db.models import F

from .models import Order, OrderItem, Product, unix_now


class OutOfStock(Exception):
    """Raised when one or more products lack enough stock. Nothing was changed."""

    def __init__(self, product_ids):
        self.product_ids = sorted(product_ids)
        super().__init__(f"Not enough stock for products: {self.product_ids}")


@transaction.atomic
def place_order(user, items):
    """Create an order for `items`, a list of `(product_id, quantity)` pairs.

    Each product's stock is decremented with a conditional UPDATE
    (`... WHERE items_available >= qty`), so concurrent orders can never sell
    more than is available. If any product is short, `OutOfStock` lists every
    short product and the transaction rolls back all decrements.
    Callers validate the input (quantity >= 1, distinct existing products).
    """
    items = sorted(items)  # consistent lock order on backends with row locks
    now = unix_now()
    short = []
    for product_id, quantity in items:
        updated = Product.objects.filter(pk=product_id, items_available__gte=quantity).update(
            items_available=F("items_available") - quantity,
            updated_at=now,  # update() bypasses save(), so set it here
        )
        if not updated:
            short.append(product_id)
    if short:
        raise OutOfStock(short)

    prices = dict(Product.objects.filter(pk__in=[pid for pid, _ in items]).values_list("id", "price_cents"))
    order = Order.objects.create(user=user, total_cents=sum(prices[pid] * qty for pid, qty in items))
    OrderItem.objects.bulk_create(
        OrderItem(order=order, product_id=pid, quantity=qty, unit_price_cents=prices[pid]) for pid, qty in items
    )
    return order
