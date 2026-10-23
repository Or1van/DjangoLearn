from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from expenses.models import Category, Transaction

User = get_user_model()


class Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")
        self.other = User.objects.create_user("bob", password="pass12345")
        self.client.login(username="alice", password="pass12345")
        self.today = timezone.localdate()

    def tx(self, user=None, **kw):
        data = dict(user=user or self.user, title="Item", amount=Decimal("10"),
                    kind="expense", date=self.today)
        data.update(kw)
        return Transaction.objects.create(**data)


class DashboardTests(Base):
    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("expenses:dashboard"))
        self.assertRedirects(resp, f"{reverse('login')}?next=/")

    def test_empty_state(self):
        resp = self.client.get(reverse("expenses:dashboard"))
        self.assertContains(resp, "get started")
        self.assertFalse(resp.context["has_data"])

    def test_month_totals_and_balance(self):
        self.tx(amount=Decimal("100"), kind="expense")
        self.tx(amount=Decimal("500"), kind="income")
        resp = self.client.get(reverse("expenses:dashboard"))
        self.assertEqual(resp.context["income"], Decimal("500"))
        self.assertEqual(resp.context["expense"], Decimal("100"))
        self.assertEqual(resp.context["balance"], Decimal("400"))

    def test_net_worth_is_all_time(self):
        self.tx(amount=Decimal("1000"), kind="income", date=self.today - timedelta(days=400))
        self.tx(amount=Decimal("250"), kind="expense")
        resp = self.client.get(reverse("expenses:dashboard"))
        self.assertEqual(resp.context["net_worth"], Decimal("750"))
        self.assertEqual(resp.context["income"], Decimal("0"))

    def test_delta_vs_previous_month(self):
        first = self.today.replace(day=1)
        self.tx(amount=Decimal("100"), date=first - timedelta(days=1))
        self.tx(amount=Decimal("150"), date=first)
        resp = self.client.get(reverse("expenses:dashboard"))
        self.assertEqual(resp.context["delta"], 50)

    def test_delta_none_without_previous_data(self):
        self.tx()
        self.assertIsNone(self.client.get(reverse("expenses:dashboard")).context["delta"])

    def test_chart_data_trend_has_six_months(self):
        self.tx()
        data = self.client.get(reverse("expenses:dashboard")).context["dash_data"]
        self.assertEqual(len(data["trend"]), 6)
        self.assertEqual(data["trend"][-1]["expense"], 10.0)

    def test_chart_categories_use_category_colors(self):
        cat = Category.objects.create(user=self.user, name="Food", color="#ff0000", icon="🍕")
        self.tx(category=cat, amount=Decimal("42"))
        row = self.client.get(reverse("expenses:dashboard")).context["dash_data"]["by_category"][0]
        self.assertEqual((row["name"], row["color"], row["total"]), ("Food", "#ff0000", 42.0))

    def test_isolated_from_other_users(self):
        self.tx(user=self.other, amount=Decimal("999"), title="Secret")
        resp = self.client.get(reverse("expenses:dashboard"))
        self.assertNotContains(resp, "Secret")
        self.assertEqual(resp.context["expense"], Decimal("0"))

    def test_recent_limited_to_six(self):
        for i in range(10):
            self.tx(title=f"R{i}")
        self.assertEqual(len(self.client.get(reverse("expenses:dashboard")).context["recent"]), 6)

    def test_ukrainian_dashboard(self):
        self.tx()
        self.client.post(reverse("set_language"), {"language": "uk", "next": "/"})
        resp = self.client.get(reverse("expenses:dashboard"))
        self.assertContains(resp, "Загальний баланс")
        self.assertContains(resp, "Останні транзакції")

    def test_login_redirects_to_dashboard(self):
        self.client.logout()
        resp = self.client.post(reverse("login"), {"username": "alice", "password": "pass12345"})
        self.assertRedirects(resp, reverse("expenses:dashboard"))


class ListPeriodAndSortTests(Base):
    def titles(self, **params):
        resp = self.client.get(reverse("expenses:list"), params)
        return [t.title for t in resp.context["transactions"]]

    def test_period_month(self):
        self.tx(title="now")
        self.tx(title="old", date=self.today - timedelta(days=90))
        self.assertEqual(self.titles(period="month"), ["now"])

    def test_period_30d(self):
        self.tx(title="recent", date=self.today - timedelta(days=10))
        self.tx(title="old", date=self.today - timedelta(days=60))
        self.assertEqual(self.titles(period="30d"), ["recent"])

    def test_period_year(self):
        self.tx(title="now")
        self.tx(title="ancient", date=self.today.replace(month=1, day=1) - timedelta(days=1))
        self.assertEqual(self.titles(period="year"), ["now"])

    def test_invalid_period_ignored(self):
        self.tx(title="a", date=self.today - timedelta(days=500))
        self.assertEqual(self.titles(period="bogus"), ["a"])

    def test_sort_by_amount(self):
        self.tx(title="small", amount=Decimal("1"))
        self.tx(title="big", amount=Decimal("99"))
        self.assertEqual(self.titles(sort="-amount"), ["big", "small"])
        self.assertEqual(self.titles(sort="amount"), ["small", "big"])

    def test_sort_by_date(self):
        self.tx(title="old", date=self.today - timedelta(days=5))
        self.tx(title="new")
        self.assertEqual(self.titles(sort="date"), ["old", "new"])
        self.assertEqual(self.titles(sort="-date"), ["new", "old"])

    def test_invalid_sort_falls_back(self):
        self.tx(title="x")
        self.assertEqual(self.titles(sort="; DROP TABLE"), ["x"])

    def test_totals_respect_period(self):
        self.tx(amount=Decimal("5"))
        self.tx(amount=Decimal("500"), date=self.today - timedelta(days=200))
        resp = self.client.get(reverse("expenses:list"), {"period": "month"})
        self.assertEqual(resp.context["total_expense"], Decimal("5"))


class CategoryDesignTests(Base):
    def test_create_with_icon_and_color(self):
        self.client.post(reverse("expenses:category_list"),
                         {"name": "Pets", "icon": "🐶", "color": "#123abc"})
        c = Category.objects.get(name="Pets")
        self.assertEqual((c.icon, c.color), ("🐶", "#123abc"))

    def test_defaults_when_icon_and_color_blank(self):
        self.client.post(reverse("expenses:category_list"), {"name": "Misc", "icon": "", "color": ""})
        c = Category.objects.get(name="Misc")
        self.assertEqual(c.color, "#6366f1")
        self.assertTrue(c.icon)

    def test_invalid_color_rejected(self):
        resp = self.client.post(reverse("expenses:category_list"),
                                {"name": "Bad", "icon": "x", "color": "red"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Category.objects.filter(name="Bad").exists())

    def test_update_category(self):
        c = Category.objects.create(user=self.user, name="Old")
        resp = self.client.post(reverse("expenses:category_update", args=[c.pk]),
                                {"name": "New", "icon": "🔥", "color": "#000000"})
        self.assertRedirects(resp, reverse("expenses:category_list"))
        c.refresh_from_db()
        self.assertEqual((c.name, c.icon, c.color), ("New", "🔥", "#000000"))

    def test_update_keeping_same_name_allowed(self):
        c = Category.objects.create(user=self.user, name="Same")
        resp = self.client.post(reverse("expenses:category_update", args=[c.pk]),
                                {"name": "Same", "icon": "🔥", "color": "#000000"})
        self.assertEqual(resp.status_code, 302)

    def test_update_to_existing_name_rejected(self):
        Category.objects.create(user=self.user, name="A")
        b = Category.objects.create(user=self.user, name="B")
        resp = self.client.post(reverse("expenses:category_update", args=[b.pk]),
                                {"name": "A", "icon": "x", "color": "#000000"})
        self.assertEqual(resp.status_code, 200)

    def test_cannot_update_foreign_category(self):
        c = Category.objects.create(user=self.other, name="Theirs")
        resp = self.client.post(reverse("expenses:category_update", args=[c.pk]),
                                {"name": "Hacked", "icon": "x", "color": "#000000"})
        self.assertEqual(resp.status_code, 404)

    def test_category_card_shows_spent(self):
        c = Category.objects.create(user=self.user, name="Food")
        self.tx(category=c, amount=Decimal("12.50"))
        self.tx(category=c, amount=Decimal("7.50"))
        self.tx(category=c, amount=Decimal("100"), kind="income")
        resp = self.client.get(reverse("expenses:category_list"))
        self.assertContains(resp, "Spent $20.00")


class MessagesAndFormTests(Base):
    def test_success_message_after_create(self):
        resp = self.client.post(reverse("expenses:create"), {
            "title": "x", "amount": "5", "kind": "expense", "date": "2025-01-01"}, follow=True)
        self.assertContains(resp, "Transaction added.")

    def test_success_message_after_delete(self):
        t = self.tx()
        resp = self.client.post(reverse("expenses:delete", args=[t.pk]), follow=True)
        self.assertContains(resp, "Transaction deleted.")

    def test_message_translated(self):
        self.client.post(reverse("set_language"), {"language": "uk", "next": "/"})
        resp = self.client.post(reverse("expenses:create"), {
            "title": "x", "amount": "5", "kind": "expense", "date": "2025-01-01"}, follow=True)
        self.assertContains(resp, "Транзакцію додано.")

    def test_create_form_preselects_kind_from_query(self):
        resp = self.client.get(reverse("expenses:create"), {"kind": "income"})
        self.assertEqual(resp.context["form"].initial["kind"], "income")

    def test_create_form_ignores_bad_kind(self):
        resp = self.client.get(reverse("expenses:create"), {"kind": "zzz"})
        self.assertNotIn("kind", resp.context["form"].initial)

    def test_theme_toggle_present(self):
        self.assertContains(self.client.get(reverse("expenses:dashboard")), 'id="theme-toggle"')

    def test_guest_pages_have_theme_and_language_controls(self):
        self.client.logout()
        resp = self.client.get(reverse("login"))
        self.assertContains(resp, 'id="theme-toggle"')
        self.assertContains(resp, "Українська")


class SeedCommandTests(TestCase):
    def test_seed_creates_demo_data(self):
        call_command("seed_demo", stdout=StringIO())
        user = User.objects.get(username="demo")
        self.assertTrue(user.check_password("demo12345"))
        self.assertGreater(Transaction.objects.filter(user=user).count(), 20)
        self.assertEqual(Category.objects.filter(user=user).count(), 6)
        self.assertFalse(Transaction.objects.filter(user=user, date__gt=timezone.localdate()).exists())

    def test_seed_twice_errors(self):
        call_command("seed_demo", stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())

    def test_demo_user_can_open_every_page(self):
        call_command("seed_demo", stdout=StringIO())
        self.client.login(username="demo", password="demo12345")
        for name in ("dashboard", "list", "create", "category_list", "stats", "stats_api"):
            self.assertEqual(self.client.get(reverse(f"expenses:{name}")).status_code, 200, name)
