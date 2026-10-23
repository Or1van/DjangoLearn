from decimal import Decimal
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from expenses.models import Transaction

User = get_user_model()


class LanguageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")
        self.client.login(username="alice", password="pass12345")

    def switch(self, code):
        return self.client.post(reverse("set_language"),
                                {"language": code, "next": reverse("expenses:list")})

    def test_default_language_is_english(self):
        resp = self.client.get(reverse("expenses:list"))
        self.assertContains(resp, "Transactions")
        self.assertContains(resp, '<html lang="en">')

    def test_switch_to_ukrainian(self):
        resp = self.switch("uk")
        self.assertRedirects(resp, reverse("expenses:list"))
        resp = self.client.get(reverse("expenses:list"))
        self.assertContains(resp, "Транзакції")
        self.assertContains(resp, '<html lang="uk">')
        self.assertNotContains(resp, "No transactions yet.")

    def test_switch_back_to_english(self):
        self.switch("uk")
        self.switch("en")
        self.assertContains(self.client.get(reverse("expenses:list")), "Transactions")

    def test_unknown_language_is_ignored(self):
        self.switch("xx")
        self.assertContains(self.client.get(reverse("expenses:list")), "Transactions")

    def test_language_selector_lists_both(self):
        resp = self.client.get(reverse("expenses:list"))
        self.assertContains(resp, "English")
        self.assertContains(resp, "Українська")

    def test_forms_and_stats_are_translated(self):
        self.switch("uk")
        self.assertContains(self.client.get(reverse("expenses:create")), "Нова транзакція")
        self.assertContains(self.client.get(reverse("expenses:stats")), "Статистика")
        data = self.client.get(reverse("expenses:stats_api")).json()
        self.assertEqual(data["by_category"], [])

    def test_uncategorized_label_translated(self):
        Transaction.objects.create(user=self.user, title="x", amount=Decimal("1"),
                                   kind="expense", date=date(2025, 1, 1))
        self.switch("uk")
        data = self.client.get(reverse("expenses:stats_api")).json()
        self.assertEqual(data["by_category"][0]["name"], "Без категорії")

    def test_every_ukrainian_string_is_compiled(self):
        with translation.override("uk"):
            for msg in ("Income", "Expenses", "Balance", "Filter", "Save", "Cancel"):
                self.assertNotEqual(translation.gettext(msg), msg)

    def test_duplicate_category_error_translated(self):
        self.client.post(reverse("expenses:category_list"), {"name": "Food"})
        self.switch("uk")
        resp = self.client.post(reverse("expenses:category_list"), {"name": "Food"})
        self.assertContains(resp, "У вас вже є категорія")


class CurrencyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")
        self.client.login(username="alice", password="pass12345")
        Transaction.objects.create(user=self.user, title="Coffee", amount=Decimal("3.50"),
                                   kind="expense", date=date(2025, 1, 1))
        Transaction.objects.create(user=self.user, title="Pay", amount=Decimal("100"),
                                   kind="income", date=date(2025, 1, 2))

    def test_amounts_shown_in_dollars(self):
        resp = self.client.get(reverse("expenses:list"))
        self.assertContains(resp, "-$3.50")
        self.assertContains(resp, "+$100.00")

    def test_totals_shown_in_dollars(self):
        resp = self.client.get(reverse("expenses:list"))
        self.assertContains(resp, "$96.50")
