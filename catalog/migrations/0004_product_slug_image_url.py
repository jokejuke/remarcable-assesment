import django.core.validators
from django.db import migrations, models
from django.utils.text import slugify


def fill_slugs(apps, schema_editor):
    """Give every existing product a unique slug (same rule as `catalog.models.unique_slug`)."""
    Product = apps.get_model("catalog", "Product")
    taken = set()
    for product in Product.objects.order_by("id"):
        base = slugify(product.name)[:200] or "product"
        slug, n = base, 1
        while slug in taken:
            n += 1
            slug = f"{base}-{n}"
        taken.add(slug)
        product.slug = slug
        product.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="image_url",
            field=models.URLField(
                blank=True,
                help_text="Address of one picture (http or https). Leave empty to show a placeholder.",
                max_length=500,
                validators=[django.core.validators.URLValidator(schemes=["http", "https"])],
            ),
        ),
        # 1. add the slug as nullable and non-unique
        migrations.AddField(
            model_name="product",
            name="slug",
            field=models.SlugField(max_length=220, null=True),
        ),
        # 2. fill it for the existing rows
        migrations.RunPython(fill_slugs, migrations.RunPython.noop),
        # 3. make it unique and non-null
        migrations.AlterField(
            model_name="product",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="Public URL part. Generated from the name when left empty; it does not change on rename.",
                max_length=220,
                unique=True,
            ),
        ),
    ]
