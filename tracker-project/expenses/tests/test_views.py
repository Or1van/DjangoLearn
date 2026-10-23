from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from expenses.models import Category, Transaction

User = get_user_model()


class BaseCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")
        self.other = User.objects.create_user("bob", password="pass12345")
        self.client.login(username="alice", password="pass12345")

    def tx(self, user=None, **kw):
        data = dict(user=user or self.user, title="Item", amount=Decimal("10"),
                    kind=Transaction.EXPENSE, date=date(2025, 1, 15))
        data.update(kw)
        return Transaction.objects.create(**data)


class AuthTests(TestCase):
    def test_login_required_redirects(self):
        for name in ("expenses:list", "expenses:create", "expenses:stats",
                     "expenses:category_list"):
            url = reverse(name)
            resp = self.client.get(url)
            self.assertRedirects(resp, f"{reverse('login')}?next={url}")

    def test_signup_creates_user_and_logs_in(self):
        resp = self.client.post(reverse("signup"), {
            "username": "newuser", "password1": "Str0ngPass!word",
            "password2": "Str0ngPass!word"})
        self.assertRedirects(resp, reverse("expenses:dashboard"))
        user = User.objects.get(username="newuser")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_signup_password_mismatch(self):
        resp = self.client.post(reverse("signup"), {
            "username": "x", "password1": "Str0ngPass!word", "password2": "other"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="x").exists())

    def test_login_page_renders(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)


class ListViewTests(BaseCase):
    def test_shows_only_own_transactions(self):
        self.tx(title="Mine")
        self.tx(user=self.other, title="Theirs")
        resp = self.client.get(reverse("expenses:list"))
        self.assertContains(resp, "Mine")
        self.assertNotContains(resp, "Theirs")

    def test_totals(self):
        self.tx(amount=Decimal("30"), kind=Transaction.EXPENSE)
        self.tx(amount=Decimal("100"), kind=Transaction.INCOME)
        resp = self.client.get(reverse("expenses:list"))
        self.assertEqual(resp.context["total_income"], Decimal("100"))
        self.assertEqual(resp.context["total_expense"], Decimal("30"))
        self.assertEqual(resp.context["balance"], Decimal("70"))

    def test_empty_totals_are_zero(self):
        resp = self.client.get(reverse("expenses:list"))
        self.assertEqual(resp.context["balance"], Decimal("0"))

    def test_filter_by_kind(self):
        self.tx(title="Spend")
        self.tx(title="Earn", kind=Transaction.INCOME)
        resp = self.client.get(reverse("expenses:list"), {"kind": "income"})
        self.assertContains(resp, "Earn")
        self.assertNotContains(resp, "Spend")

    def test_filter_by_category(self):
        cat = Category.objects.create(user=self.user, name="Food")
        self.tx(title="Pizza", category=cat)
        self.tx(title="Bus")
        resp = self.client.get(reverse("expenses:list"), {"category": cat.pk})
        self.assertContains(resp, "Pizza")
        self.assertNotContains(resp, "Bus")

    def test_filter_by_date_range(self):
        self.tx(title="Jan", date=date(2025, 1, 5))
        self.tx(title="Mar", date=date(2025, 3, 5))
        resp = self.client.get(reverse("expenses:list"),
                               {"date_from": "2025-02-01", "date_to": "2025-04-01"})
        self.assertContains(resp, "Mar")
        self.assertNotContains(resp, "Jan")

    def test_search_by_title(self):
        self.tx(title="Coffee beans")
        self.tx(title="Rent")
        resp = self.client.get(reverse("expenses:list"), {"q": "coffee"})
        self.assertContains(resp, "Coffee beans")
        self.assertNotContains(resp, "Rent")

    def test_totals_respect_filters(self):
        self.tx(amount=Decimal("5"))
        self.tx(amount=Decimal("50"), kind=Transaction.INCOME)
        resp = self.client.get(reverse("expenses:list"), {"kind": "expense"})
        self.assertEqual(resp.context["total_income"], Decimal("0"))
        self.assertEqual(resp.context["total_expense"], Decimal("5"))

    def test_invalid_filter_values_ignored(self):
        self.tx()
        resp = self.client.get(reverse("expenses:list"),
                               {"category": "abc", "date_from": "nope", "kind": "zzz"})
        self.assertEqual(resp.status_code, 200)

    def test_pagination(self):
        for i in range(25):
            self.tx(title=f"T{i}")
        resp = self.client.get(reverse("expenses:list"))
        self.assertEqual(len(resp.context["transactions"]), 15)
        resp = self.client.get(reverse("expenses:list"), {"page": 2})
        self.assertEqual(len(resp.context["transactions"]), 10)


class CreateUpdateDeleteTests(BaseCase):
    def payload(self, **kw):
        data = {"title": "Taxi", "amount": "15.00", "kind": "expense",
                "date": "2025-02-01", "category": "", "note": ""}
        data.update(kw)
        return data

    def test_create(self):
        resp = self.client.post(reverse("expenses:create"), self.payload())
        self.assertRedirects(resp, reverse("expenses:list"))
        t = Transaction.objects.get()
        self.assertEqual((t.user, t.title, t.amount), (self.user, "Taxi", Decimal("15.00")))

    def test_create_invalid_amount(self):
        resp = self.client.post(reverse("expenses:create"), self.payload(amount="-1"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_create_cannot_use_foreign_category(self):
        foreign = Category.objects.create(user=self.other, name="Secret")
        resp = self.client.post(reverse("expenses:create"),
                                self.payload(category=foreign.pk))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_update(self):
        t = self.tx(title="Old")
        resp = self.client.post(reverse("expenses:update", args=[t.pk]),
                                self.payload(title="New"))
        self.assertRedirects(resp, reverse("expenses:list"))
        t.refresh_from_db()
        self.assertEqual(t.title, "New")

    def test_cannot_update_foreign_transaction(self):
        t = self.tx(user=self.other)
        resp = self.client.post(reverse("expenses:update", args=[t.pk]), self.payload())
        self.assertEqual(resp.status_code, 404)

    def test_delete_requires_post_confirmation(self):
        t = self.tx()
        self.assertEqual(self.client.get(reverse("expenses:delete", args=[t.pk])).status_code, 200)
        self.assertTrue(Transaction.objects.filter(pk=t.pk).exists())
        self.client.post(reverse("expenses:delete", args=[t.pk]))
        self.assertFalse(Transaction.objects.filter(pk=t.pk).exists())

    def test_cannot_delete_foreign_transaction(self):
        t = self.tx(user=self.other)
        resp = self.client.post(reverse("expenses:delete", args=[t.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=t.pk).exists())


class CategoryViewTests(BaseCase):
    def test_list_only_own(self):
        Category.objects.create(user=self.user, name="Mine")
        Category.objects.create(user=self.other, name="Theirs")
        resp = self.client.get(reverse("expenses:category_list"))
        self.assertContains(resp, "Mine")
        self.assertNotContains(resp, "Theirs")

    def test_create(self):
        self.client.post(reverse("expenses:category_list"), {"name": "Travel"})
        self.assertTrue(Category.objects.filter(user=self.user, name="Travel").exists())

    def test_duplicate_name_rejected(self):
        Category.objects.create(user=self.user, name="Travel")
        resp = self.client.post(reverse("expenses:category_list"), {"name": "Travel"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Category.objects.filter(user=self.user).count(), 1)

    def test_delete_own(self):
        c = Category.objects.create(user=self.user, name="Travel")
        self.client.post(reverse("expenses:category_delete", args=[c.pk]))
        self.assertFalse(Category.objects.filter(pk=c.pk).exists())

    def test_cannot_delete_foreign(self):
        c = Category.objects.create(user=self.other, name="Travel")
        resp = self.client.post(reverse("expenses:category_delete", args=[c.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Category.objects.filter(pk=c.pk).exists())


class StatsTests(BaseCase):
    def test_stats_page_renders(self):
        self.assertEqual(self.client.get(reverse("expenses:stats")).status_code, 200)

    def test_stats_api_by_category_and_month(self):
        food = Category.objects.create(user=self.user, name="Food")
        self.tx(amount=Decimal("20"), category=food, date=date(2025, 1, 5))
        self.tx(amount=Decimal("30"), category=food, date=date(2025, 2, 5))
        self.tx(amount=Decimal("7"), date=date(2025, 2, 6))
        self.tx(amount=Decimal("500"), kind=Transaction.INCOME, date=date(2025, 2, 7))
        self.tx(user=self.other, amount=Decimal("999"))
        data = self.client.get(reverse("expenses:stats_api")).json()
        by_cat = {r["name"]: r["total"] for r in data["by_category"]}
        self.assertEqual(by_cat, {"Food": 50.0, "Uncategorized": 7.0})
        months = {r["month"]: r for r in data["by_month"]}
        self.assertEqual(months["2025-01"]["expense"], 20.0)
        self.assertEqual(months["2025-02"]["expense"], 37.0)
        self.assertEqual(months["2025-02"]["income"], 500.0)

    def test_stats_api_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("expenses:stats_api")).status_code, 302)

    def test_stats_api_empty(self):
        data = self.client.get(reverse("expenses:stats_api")).json()
        self.assertEqual(data, {"by_category": [], "by_month": []})
