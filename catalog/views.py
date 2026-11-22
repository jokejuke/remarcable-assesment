"""Storefront views (server-rendered)."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max, Min
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from .category_tree import get_category_tree
from .filters import ProductFilterSet
from .models import Favorite, Order, Product
from .services import OutOfStock, place_order


def login_required_action(view):
    """For POST actions: anonymous users go to the login page, then back to the page they came from."""

    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(safe_next(request))
        return view(request, *args, **kwargs)

    wrapped.__name__ = view.__name__
    wrapped.__doc__ = view.__doc__
    return wrapped


def safe_next(request, fallback="/"):
    """The `next` parameter if it points to this site, else `fallback`."""
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return fallback


class ProductListView(ListView):
    """Home page: product cards, filtered by the sidebar form."""

    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = settings.CATALOG_PAGE_SIZE

    def get_queryset(self):
        # Always bound (even to an empty query string), so the in-stock default applies.
        self.filterset = ProductFilterSet(
            self.request.GET,
            queryset=Product.objects.for_listing(self.request.user),
            request=self.request,
        )
        if not self.filterset.is_valid():
            return Product.objects.none()
        return self.filterset.qs

    def _filters_active(self, data, price_min, price_max, low, high):
        """True when the page applies anything beyond the defaults.

        Defaults: empty search, no category or tags, ALL matching, the full price range, and the
        stock and favourites options off. (`favorites` is ignored for anonymous visitors.)
        """
        tags = data.get("tags")
        return bool(
            data.get("q")
            or data.get("category")
            or tags
            or (data.get("match") == "any" and tags)
            or data.get("include_out_of_stock")
            or (data.get("favorites") and self.request.user.is_authenticated)
            or price_min != low
            or price_max != high
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.copy()
        query.pop("page", None)
        bounds = Product.objects.aggregate(low=Min("price_cents"), high=Max("price_cents"))
        low, high = bounds["low"] or 0, bounds["high"] or 0
        # Slider steps are whole dollars; round the bounds outwards.
        low, high = low // 100 * 100, -(-high // 100) * 100
        valid = self.filterset.is_valid()
        data = self.filterset.form.cleaned_data if valid else {}
        price_min = data.get("price_min") if data.get("price_min") is not None else low
        price_max = data.get("price_max") if data.get("price_max") is not None else high
        context.update(
            filters_active=not valid or self._filters_active(data, price_min, price_max, low, high),
            filter=self.filterset,
            form=self.filterset.form,
            category_tree=get_category_tree(),
            querystring=query.urlencode(),
            price_low=low,
            price_high=high,
            price_min=price_min,
            price_max=price_max,
            selected_tags={str(t) for t in self.request.GET.getlist("tags")},
            current_url=self.request.get_full_path(),
        )
        return context


class ProductDetailView(DetailView):
    """One product's page, found by slug. Shows out-of-stock products too."""

    template_name = "catalog/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return Product.objects.for_listing(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_url"] = self.request.get_full_path()
        return context


@require_POST
@login_required_action
def favorite_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    _, created = Favorite.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, f"Added “{product.name}” to your favourites.")
    return redirect(safe_next(request))


@require_POST
@login_required_action
def favorite_remove(request, product_id):
    deleted, _ = Favorite.objects.filter(user=request.user, product_id=product_id).delete()
    if deleted:
        messages.success(request, "Removed from your favourites.")
    return redirect(safe_next(request))


@require_POST
@login_required_action
def buy(request, product_id):
    """One-click purchase of a single unit."""
    product = get_object_or_404(Product, pk=product_id)
    try:
        order = place_order(request.user, [(product.pk, 1)])
    except OutOfStock:
        messages.error(request, f"Sorry, “{product.name}” is out of stock.")
    else:
        messages.success(request, f"Order #{order.pk} placed: 1 × {product.name}.")
    return redirect(safe_next(request))


class MyFavoritesView(LoginRequiredMixin, ListView):
    """All of the user's favourites, including out-of-stock products."""

    template_name = "catalog/my_favorites.html"
    context_object_name = "products"

    def get_queryset(self):
        return Product.objects.favorites_of(self.request.user).for_listing(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(category_tree=get_category_tree(), current_url=self.request.get_full_path())
        return context


class MyOrdersView(LoginRequiredMixin, ListView):
    template_name = "catalog/my_orders.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items__product")
