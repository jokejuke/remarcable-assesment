"""The one filter definition shared by the storefront and the API.

Each filter delegates to a `ProductQuerySet` method, so the query logic stays in
`querysets.py`. Two defaults are applied in `filter_queryset`, because they act
when a parameter is *absent*: out-of-stock products are hidden unless
`include_out_of_stock` is set, and `favorites` only applies to logged-in users.
"""

import django_filters
from django import forms
from django_filters.widgets import BooleanWidget

from .category_tree import get_category_tree
from .models import Tag


def category_choices():
    return [(node.id, node.name) for node in get_category_tree().nodes]


class CategoryTreeWidget(forms.RadioSelect):
    """Radio buttons indented by tree depth, with "All" first.

    Each option also carries `data-id`, `data-parent` and `data-has-children`, which the
    storefront script uses to collapse and expand branches.
    """

    option_template_name = "catalog/widgets/category_option.html"

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option["depth"] = 0
        option["node"] = None
        if value not in (None, ""):
            for node in get_category_tree().nodes:
                if str(node.id) == str(value):
                    option["depth"] = node.depth
                    option["node"] = node
                    break
        return option


class IntegerFilter(django_filters.NumberFilter):
    field_class = forms.IntegerField


class ProductFilterForm(forms.Form):
    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("price_min"), cleaned.get("price_max")
        if low is not None and high is not None and low > high:
            self.add_error("price_max", "The maximum price must be greater than or equal to the minimum price.")
        return cleaned


class ProductFilterSet(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_search", label="Search", max_length=200)
    category = django_filters.ChoiceFilter(
        choices=category_choices,
        empty_label="All",
        method="filter_category",
        widget=CategoryTreeWidget,
        help_text="Category id; includes every category below it.",
    )
    tags = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        method="filter_tags",
        widget=forms.CheckboxSelectMultiple,
        help_text="Tag ids; repeat the parameter for several tags.",
    )
    match = django_filters.ChoiceFilter(
        choices=[("all", "All selected tags"), ("any", "Any selected tag")],
        empty_label=None,
        method="filter_noop",  # read by filter_tags
        help_text="How `tags` combine: `all` (default) or `any`.",
    )
    price_min = IntegerFilter(method="filter_noop", min_value=0, label="Minimum price (cents)")
    price_max = IntegerFilter(method="filter_noop", min_value=0, label="Maximum price (cents)")
    include_out_of_stock = django_filters.BooleanFilter(
        method="filter_noop",
        widget=BooleanWidget,
        help_text="Include products with zero stock (hidden by default).",
    )
    favorites = django_filters.BooleanFilter(
        method="filter_noop",
        widget=BooleanWidget,
        help_text="Only the current user's favourites (requires authentication).",
    )

    class Meta:
        form = ProductFilterForm
        fields = []  # all filters are declared above

    # -- filter methods -------------------------------------------------------

    def filter_noop(self, queryset, name, value):
        return queryset

    def filter_search(self, queryset, name, value):
        return queryset.search(value)

    def filter_category(self, queryset, name, value):
        return queryset.in_category(int(value))

    def filter_tags(self, queryset, name, value):
        match = self.form.cleaned_data.get("match") or "all"
        return queryset.with_tags([tag.pk for tag in value], match)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        data = self.form.cleaned_data
        queryset = queryset.price_between(data.get("price_min"), data.get("price_max"))
        if not data.get("include_out_of_stock"):
            queryset = queryset.in_stock()
        user = getattr(self.request, "user", None)
        if data.get("favorites") and user is not None and user.is_authenticated:
            queryset = queryset.favorites_of(user)
        return queryset
