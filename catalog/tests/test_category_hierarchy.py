"""Spec: category-hierarchy."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog import category_tree
from catalog.category_tree import get_category_tree
from catalog.models import Category

from .factories import build_tree, container, leaf, product


class CategoryModelTests(TestCase):
    def test_top_level_and_child(self):
        electronics = container("Electronics")
        audio = container("Audio", electronics)
        self.assertIsNone(electronics.parent)
        self.assertEqual(list(electronics.children.all()), [audio])

    def test_duplicate_name_under_different_parent_rejected(self):
        a, b = container("A"), container("B")
        container("Audio", a)
        with self.assertRaises(IntegrityError):
            container("Audio", b)

    def test_both_kinds_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            Category.objects.create(name="X", has_products=True, has_subcategories=True)

    def test_neither_kind_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            Category.objects.create(name="X", has_products=False, has_subcategories=False)

    def test_both_kinds_rejected_by_validation(self):
        c = Category(name="X", has_products=True, has_subcategories=True)
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_edit_changes_updated_at_only(self):
        c = leaf("Old")
        Category.objects.filter(pk=c.pk).update(created_at=1000, updated_at=1000)
        c.refresh_from_db()
        with mock.patch("catalog.models.unix_now", return_value=2000):
            c.name = "New"
            c.save()
        c.refresh_from_db()
        self.assertEqual(c.created_at, 1000)
        self.assertEqual(c.updated_at, 2000)

    def test_save_with_update_fields_still_sets_updated_at(self):
        c = leaf("Old")
        with mock.patch("catalog.models.unix_now", return_value=3000):
            c.name = "New"
            c.save(update_fields=["name"])
        c.refresh_from_db()
        self.assertEqual(c.updated_at, 3000)


class CategoryValidationTests(TestCase):
    def setUp(self):
        self.t = build_tree()

    def assertInvalid(self, category, field=None):
        with self.assertRaises(ValidationError) as ctx:
            category.full_clean()
        if field:
            self.assertIn(field, ctx.exception.message_dict)
        return ctx.exception

    def test_level_3_allowed(self):
        c = Category(name="Earbuds", parent=self.t["audio"], has_products=True, has_subcategories=False)
        c.full_clean()

    def test_beyond_max_depth_rejected(self):
        # Headphones holds products, so make a level-3 container to test depth on its own.
        Category.objects.filter(pk=self.t["speakers"].pk).update(has_products=False, has_subcategories=True)
        c = Category(name="Deep", parent_id=self.t["speakers"].pk, has_products=True, has_subcategories=False)
        err = self.assertInvalid(c, "parent")
        self.assertIn("deeper than 3", str(err))

    def test_moving_subtree_beyond_limit_rejected(self):
        electronics = self.t["electronics"]
        electronics.parent = self.t["books"]
        err = self.assertInvalid(electronics, "parent")
        self.assertIn("level 4", str(err))

    @override_settings(CATALOG_MAX_CATEGORY_DEPTH=2)
    def test_configured_depth_two(self):
        top = container("Top")
        Category(name="Level2", parent=top, has_products=True, has_subcategories=False).full_clean()
        level2 = container("Level2c", top)
        self.assertInvalid(Category(name="Level3", parent=level2, has_products=True, has_subcategories=False), "parent")

    def test_parent_must_hold_subcategories(self):
        c = Category(name="Sub", parent=self.t["headphones"], has_products=True, has_subcategories=False)
        self.assertInvalid(c, "parent")

    def test_deepest_level_must_hold_products(self):
        c = Category(name="Box", parent=self.t["audio"], has_products=False, has_subcategories=True)
        err = self.assertInvalid(c)
        self.assertIn("deepest level", str(err))

    def test_switching_category_with_products_rejected(self):
        product("Phones", self.t["headphones"])
        h = self.t["headphones"]
        h.has_products, h.has_subcategories = False, True
        self.assertInvalid(h)
        h.refresh_from_db()
        self.assertTrue(h.has_products)

    def test_switching_category_with_children_rejected(self):
        audio = self.t["audio"]
        audio.has_products, audio.has_subcategories = True, False
        self.assertInvalid(audio)

    def test_own_parent_is_a_loop(self):
        e = self.t["electronics"]
        e.parent = e
        err = self.assertInvalid(e, "parent")
        self.assertIn("itself", str(err))

    def test_under_own_descendant_is_a_loop(self):
        e = self.t["electronics"]
        e.parent = self.t["audio"]
        self.assertInvalid(e, "parent")
        e.refresh_from_db()
        self.assertIsNone(e.parent)

    def test_validation_reads_database_not_cache(self):
        get_category_tree()  # warm the cache
        with self.assertNumQueries(4):  # parents, parent kind, products/children exists
            self.t["computers"].full_clean(validate_unique=False, validate_constraints=False)


class CategoryDeleteTests(TestCase):
    def test_delete_with_products_refused(self):
        t = build_tree()
        product("Phones", t["headphones"])
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            t["headphones"].delete()
        with self.assertRaises(ProtectedError):
            t["audio"].delete()

    def test_delete_empty_category(self):
        c = leaf("Empty")
        c.delete()
        self.assertFalse(Category.objects.filter(name="Empty").exists())


class CategoryTreeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.t = build_tree()

    def test_paths(self):
        tree = get_category_tree()
        self.assertEqual(tree.path(self.t["headphones"].pk), "Electronics > Audio > Headphones")
        self.assertEqual(tree.path(self.t["books"].pk), "Books")
        self.assertEqual(self.t["headphones"].path, "Electronics > Audio > Headphones")

    def test_descendants(self):
        tree = get_category_tree()
        t = self.t
        self.assertEqual(
            tree.descendant_ids(t["electronics"].pk),
            {t["electronics"].pk, t["audio"].pk, t["headphones"].pk, t["speakers"].pk, t["computers"].pk},
        )
        self.assertEqual(tree.descendant_ids(t["headphones"].pk), {t["headphones"].pk})
        self.assertEqual(tree.descendant_ids(999999), set())

    def test_depth_first_order(self):
        nodes = get_category_tree().nodes
        self.assertEqual(
            [(n.name, n.depth) for n in nodes],
            [
                ("Books", 1), ("Fiction", 2),
                ("Electronics", 1), ("Audio", 2), ("Headphones", 3), ("Speakers", 3), ("Computers", 2),
            ],
        )

    def test_warm_cache_runs_no_queries(self):
        get_category_tree()
        with self.assertNumQueries(0):
            get_category_tree().path(self.t["audio"].pk)

    def test_cache_timeout_is_one_hour(self):
        with mock.patch.object(category_tree.cache, "get_or_set", wraps=cache.get_or_set) as spy:
            get_category_tree()
        self.assertEqual(spy.call_args.kwargs["timeout"], 3600)


class CategoryCacheInvalidationTests(TestCase):
    def setUp(self):
        self.t = build_tree()
        cache.clear()
        get_category_tree()  # warm

    def test_rename_visible_after_commit(self):
        audio = self.t["audio"]
        with self.captureOnCommitCallbacks(execute=True):
            audio.name = "Sound"
            audio.save()
        self.assertEqual(get_category_tree().path(self.t["headphones"].pk), "Electronics > Sound > Headphones")

    def test_move_visible_after_commit(self):
        computers = self.t["computers"]
        new_parent = container("Tech")
        with self.captureOnCommitCallbacks(execute=True):
            computers.parent = new_parent
            computers.save()
        self.assertEqual(get_category_tree().path(computers.pk), "Tech > Computers")

    def test_delete_visible_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.t["fiction"].delete()
        self.assertNotIn(self.t["fiction"].pk, get_category_tree())

    def test_rolled_back_save_keeps_cache(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            try:
                with transaction.atomic():
                    audio = self.t["audio"]
                    audio.name = "Sound"
                    audio.save()
                    raise RuntimeError("roll back")
            except RuntimeError:
                pass
        self.assertEqual(callbacks, [])  # nothing scheduled after a rollback
        self.assertEqual(get_category_tree().path(self.t["audio"].pk), "Electronics > Audio")


class CategoryAdminTests(TestCase):
    def setUp(self):
        self.t = build_tree()
        self.admin = get_user_model().objects.create_superuser("admin", "a@example.com", "pass-for-tests-123")
        self.client.force_login(self.admin)

    def test_changelist(self):
        response = self.client.get(reverse("admin:catalog_category_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Electronics &gt; Audio &gt; Headphones")

    def test_add_sets_both_flags_from_kind(self):
        response = self.client.post(
            reverse("admin:catalog_category_add"),
            {"name": "Earbuds", "parent": self.t["audio"].pk, "kind": "products"},
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        c = Category.objects.get(name="Earbuds")
        self.assertTrue(c.has_products)
        self.assertFalse(c.has_subcategories)

    def test_delete_with_products_shows_protected_page(self):
        product("Phones", self.t["headphones"])
        url = reverse("admin:catalog_category_delete", args=[self.t["headphones"].pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "would require deleting the following protected related objects")
        self.assertContains(response, "Phones")

    def test_invalid_parent_shows_form_error(self):
        url = reverse("admin:catalog_category_change", args=[self.t["electronics"].pk])
        response = self.client.post(url, {"name": "Electronics", "parent": self.t["audio"].pk, "kind": "subcategories"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("parent", response.context["adminform"].form.errors)

    def test_parent_choices_only_hold_subcategories(self):
        response = self.client.get(reverse("admin:catalog_category_add"))
        choices = {c.pk for c in response.context["adminform"].form.fields["parent"].queryset}
        self.assertEqual(choices, {self.t["electronics"].pk, self.t["audio"].pk, self.t["books"].pk})
