from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from expenses.models import Category, Transaction

User = get_user_model()


class CategoryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")

    def test_str_returns_name(self):
        self.assertEqual(str(Category.objects.create(user=self.user, name="Food")), "Food")

    def test_name_unique_per_user(self):
        Category.objects.create(user=self.user, name="Food")
        with self.assertRaises(IntegrityError):
            Category.objects.create(user=self.user, name="Food")

    def test_same_name_allowed_for_different_users(self):
        bob = User.objects.create_user("bob", password="pass12345")
        Category.objects.create(user=self.user, name="Food")
        Category.objects.create(user=bob, name="Food")
        self.assertEqual(Category.objects.filter(name="Food").count(), 2)


class TransactionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")

    def make(self, **kw):
        data = dict(user=self.user, title="Lunch", amount=Decimal("12.50"),
                    kind=Transaction.EXPENSE, date=date(2025, 1, 10))
        data.update(kw)
        return Transaction(**data)

    def test_str(self):
        self.assertEqual(str(self.make()), "Lunch (-12.50)")
        self.assertEqual(str(self.make(kind=Transaction.INCOME, title="Pay")), "Pay (+12.50)")

    def test_amount_must_be_positive(self):
        for bad in (Decimal("0"), Decimal("-5")):
            with self.assertRaises(ValidationError):
                self.make(amount=bad).full_clean()

    def test_category_is_optional(self):
        self.make().full_clean()

    def test_deleting_category_keeps_transaction(self):
        cat = Category.objects.create(user=self.user, name="Food")
        tx = self.make(category=cat)
        tx.save()
        cat.delete()
        tx.refresh_from_db()
        self.assertIsNone(tx.category)

    def test_default_ordering_newest_first(self):
        old = self.make(date=date(2025, 1, 1))
        old.save()
        new = self.make(date=date(2025, 2, 1))
        new.save()
        self.assertEqual(list(Transaction.objects.all()), [new, old])
