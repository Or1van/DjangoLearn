import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from expenses.models import Category, Transaction

CATEGORIES = [
    ("Food", "🍕", "#f59e0b"), ("Transport", "🚌", "#0ea5e9"), ("Rent", "🏠", "#8b5cf6"),
    ("Fun", "🎮", "#ec4899"), ("Health", "💊", "#10b981"), ("Shopping", "🛍️", "#f43f5e"),
]
EXPENSES = {
    "Food": ["Groceries", "Lunch", "Coffee", "Pizza night"],
    "Transport": ["Metro card", "Taxi", "Fuel"],
    "Fun": ["Cinema", "Steam game", "Concert"],
    "Health": ["Pharmacy", "Gym"],
    "Shopping": ["Sneakers", "T-shirt", "Headphones"],
}


class Command(BaseCommand):
    help = "Create a demo user (demo / demo12345) with ~6 months of sample data."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--password", default="demo12345")

    def handle(self, *args, **opts):
        User = get_user_model()
        if User.objects.filter(username=opts["username"]).exists():
            raise CommandError(f"User '{opts['username']}' already exists.")
        user = User.objects.create_user(opts["username"], password=opts["password"])
        cats = {n: Category.objects.create(user=user, name=n, icon=i, color=c)
                for n, i, c in CATEGORIES}
        rng = random.Random(42)
        today = timezone.localdate()
        rows = []
        for months_ago in range(6):
            anchor = (today.replace(day=1) - timedelta(days=30 * months_ago)).replace(day=1)
            rows.append(Transaction(user=user, title="Salary", kind="income",
                                    amount=Decimal(rng.randint(2800, 3400)), date=anchor))
            rows.append(Transaction(user=user, title="Rent", kind="expense", category=cats["Rent"],
                                    amount=Decimal(900), date=anchor + timedelta(days=1)))
            for _ in range(rng.randint(14, 22)):
                name = rng.choice(list(EXPENSES))
                day = min(rng.randint(1, 28), 28)
                d = anchor.replace(day=day)
                if d > today:
                    continue
                rows.append(Transaction(
                    user=user, title=rng.choice(EXPENSES[name]), kind="expense",
                    category=cats[name], date=d,
                    amount=Decimal(rng.randint(300, 9000)) / 100))
        Transaction.objects.bulk_create([r for r in rows if r.date <= today])
        self.stdout.write(self.style.SUCCESS(
            f"Created user '{opts['username']}' with {len(rows)} transactions."))
