from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from expenses.forms import CategoryForm, TransactionForm
from expenses.models import Category, Transaction

User = get_user_model()


class FormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")
        self.other = User.objects.create_user("bob", password="pass12345")

    def test_category_name_is_stripped(self):
        form = CategoryForm({"name": "  Food  "}, user=self.user)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "Food")

    def test_category_form_blank_invalid(self):
        self.assertFalse(CategoryForm({"name": ""}, user=self.user).is_valid())

    def test_other_user_can_reuse_name(self):
        Category.objects.create(user=self.other, name="Food")
        self.assertTrue(CategoryForm({"name": "Food"}, user=self.user).is_valid())

    def test_transaction_form_only_offers_own_categories(self):
        mine = Category.objects.create(user=self.user, name="Mine")
        Category.objects.create(user=self.other, name="Theirs")
        form = TransactionForm(user=self.user)
        self.assertEqual(list(form.fields["category"].queryset), [mine])

    def test_transaction_form_assigns_user(self):
        form = TransactionForm({"title": "x", "amount": "1", "kind": "expense",
                                "date": "2025-01-01"}, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().user, self.user)

    def test_transaction_form_rejects_bad_kind_and_date(self):
        form = TransactionForm({"title": "x", "amount": "1", "kind": "zzz",
                                "date": "not-a-date"}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("kind", form.errors)
        self.assertIn("date", form.errors)


class EdgeCaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")
        self.client.login(username="alice", password="pass12345")

    def tx(self, **kw):
        data = dict(user=self.user, title="Item", amount=Decimal("10"),
                    kind="expense", date=date(2025, 1, 15))
        data.update(kw)
        return Transaction.objects.create(**data)

    def test_search_matches_note(self):
        self.tx(title="A", note="birthday present")
        self.tx(title="B")
        resp = self.client.get(reverse("expenses:list"), {"q": "birthday"})
        self.assertEqual([t.title for t in resp.context["transactions"]], ["A"])

    def test_date_filter_is_inclusive(self):
        self.tx(title="Edge", date=date(2025, 3, 1))
        resp = self.client.get(reverse("expenses:list"),
                               {"date_from": "2025-03-01", "date_to": "2025-03-01"})
        self.assertEqual(len(resp.context["transactions"]), 1)

    def test_combined_filters(self):
        food = Category.objects.create(user=self.user, name="Food")
        self.tx(title="Hit", category=food, kind="expense")
        self.tx(title="WrongKind", category=food, kind="income")
        self.tx(title="NoCat")
        resp = self.client.get(reverse("expenses:list"),
                               {"category": food.pk, "kind": "expense"})
        self.assertEqual([t.title for t in resp.context["transactions"]], ["Hit"])

    def test_pagination_keeps_filters_in_links(self):
        for i in range(25):
            self.tx(title=f"T{i}")
        resp = self.client.get(reverse("expenses:list"), {"kind": "expense"})
        self.assertContains(resp, "kind=expense&amp;page=2")

    def test_out_of_range_page_falls_back_to_last(self):
        self.tx()
        resp = self.client.get(reverse("expenses:list"), {"page": 99})
        self.assertEqual(resp.status_code, 200)

    def test_decimal_precision_in_totals(self):
        self.tx(amount=Decimal("0.10"))
        self.tx(amount=Decimal("0.20"))
        resp = self.client.get(reverse("expenses:list"))
        self.assertEqual(resp.context["total_expense"], Decimal("0.30"))

    def test_edit_form_prefills_values(self):
        t = self.tx(title="Prefilled")
        resp = self.client.get(reverse("expenses:update", args=[t.pk]))
        self.assertContains(resp, "Prefilled")
        self.assertContains(resp, "2025-01-15")

    def test_deleting_category_keeps_transactions_in_list(self):
        c = Category.objects.create(user=self.user, name="Gone")
        self.tx(title="Survivor", category=c)
        self.client.post(reverse("expenses:category_delete", args=[c.pk]))
        resp = self.client.get(reverse("expenses:list"))
        self.assertContains(resp, "Survivor")

    def test_get_does_not_delete(self):
        t = self.tx()
        self.client.get(reverse("expenses:delete", args=[t.pk]))
        self.assertTrue(Transaction.objects.filter(pk=t.pk).exists())

    def test_logout_requires_post_and_logs_out(self):
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("expenses:list")).status_code, 302)

    def test_login_flow(self):
        self.client.logout()
        resp = self.client.post(reverse("login"),
                                {"username": "alice", "password": "pass12345"})
        self.assertRedirects(resp, reverse("expenses:dashboard"))

    def test_login_wrong_password(self):
        self.client.logout()
        resp = self.client.post(reverse("login"),
                                {"username": "alice", "password": "wrong"})
        self.assertEqual(resp.status_code, 200)

    def test_stats_api_months_sorted(self):
        self.tx(date=date(2025, 3, 1))
        self.tx(date=date(2025, 1, 1))
        months = [m["month"] for m in
                  self.client.get(reverse("expenses:stats_api")).json()["by_month"]]
        self.assertEqual(months, sorted(months))

    def test_stats_page_loads_chartjs(self):
        resp = self.client.get(reverse("expenses:stats"))
        self.assertContains(resp, "chart.js")
        self.assertContains(resp, 'id="by-category"')
        self.assertContains(resp, 'id="by-month"')
