from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

DEFAULT_COLOR = "#6366f1"
DEFAULT_ICON = "🏷️"


class Category(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="categories")
    name = models.CharField(_("Name"), max_length=50)
    icon = models.CharField(_("Icon"), max_length=8, default=DEFAULT_ICON, blank=True)
    color = models.CharField(_("Color"), max_length=7, default=DEFAULT_COLOR,
                             validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$")])

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_category_per_user"),
        ]

    def __str__(self):
        return self.name


class Transaction(models.Model):
    EXPENSE = "expense"
    INCOME = "income"
    KIND_CHOICES = [(EXPENSE, _("Expense")), (INCOME, _("Income"))]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="transactions")
    title = models.CharField(_("Title"), max_length=100)
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2,
                                 validators=[MinValueValidator(Decimal("0.01"))])
    kind = models.CharField(_("Type"), max_length=7, choices=KIND_CHOICES, default=EXPENSE)
    category = models.ForeignKey(Category, verbose_name=_("Category"), null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="transactions")
    date = models.DateField(_("Date"))
    note = models.TextField(_("Note"), blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        sign = "+" if self.kind == self.INCOME else "-"
        return f"{self.title} ({sign}{self.amount})"
