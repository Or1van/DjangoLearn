from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from .forms import CategoryForm, TransactionForm
from .models import DEFAULT_COLOR, Category, Transaction

PAGE_SIZE = 15
SORTS = {"-date": ("-date", "-id"), "date": ("date", "id"),
         "-amount": ("-amount", "-id"), "amount": ("amount", "id")}
PERIODS = ("month", "30d", "year")
ZERO = Decimal("0")


def signup(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        messages.success(request, _("Welcome! Your account has been created."))
        return redirect("expenses:dashboard")
    return render(request, "registration/signup.html", {"form": form})


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _month_start(d):
    return d.replace(day=1)


def _shift_month(d, delta):
    idx = d.year * 12 + d.month - 1 + delta
    return d.replace(year=idx // 12, month=idx % 12 + 1, day=1)


def _filtered(request):
    qs = Transaction.objects.filter(user=request.user).select_related("category")
    today = timezone.localdate()
    kind = request.GET.get("kind", "")
    if kind in (Transaction.EXPENSE, Transaction.INCOME):
        qs = qs.filter(kind=kind)
    else:
        kind = ""
    category = request.GET.get("category", "")
    if category.isdigit():
        qs = qs.filter(category_id=int(category))
    else:
        category = ""
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    period = request.GET.get("period", "")
    if period == "month":
        date_from, date_to = _month_start(today), None
    elif period == "30d":
        date_from, date_to = today - timedelta(days=30), None
    elif period == "year":
        date_from, date_to = today.replace(month=1, day=1), None
    else:
        period = ""
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(note__icontains=q))
    sort = request.GET.get("sort", "")
    if sort not in SORTS:
        sort = "-date"
    qs = qs.order_by(*SORTS[sort])
    return qs, {"kind": kind, "category": category, "q": q, "period": period, "sort": sort,
                "date_from": date_from.isoformat() if date_from and not period else "",
                "date_to": date_to.isoformat() if date_to else ""}


def _total(qs, kind):
    return qs.filter(kind=kind).aggregate(s=Sum("amount"))["s"] or ZERO


@login_required
def dashboard(request):
    today = timezone.localdate()
    start = _month_start(today)
    prev_start = _shift_month(start, -1)
    qs = Transaction.objects.filter(user=request.user)

    this_month = qs.filter(date__gte=start)
    income, expense = _total(this_month, "income"), _total(this_month, "expense")
    prev = qs.filter(date__gte=prev_start, date__lt=start)
    prev_expense = _total(prev, "expense")
    delta = None
    if prev_expense:
        delta = round(float((expense - prev_expense) / prev_expense * 100))

    cats = (this_month.filter(kind="expense")
            .values("category__name", "category__color", "category__icon")
            .annotate(total=Sum("amount")).order_by("-total"))
    by_category = [{"name": c["category__name"] or _("Uncategorized"),
                    "color": c["category__color"] or "#94a3b8",
                    "icon": c["category__icon"] or "❔",
                    "total": float(c["total"])} for c in cats]

    first = _shift_month(start, -5)
    rows = (qs.filter(date__gte=first).annotate(m=TruncMonth("date"))
            .values("m", "kind").annotate(total=Sum("amount")))
    trend = {_shift_month(first, i).strftime("%Y-%m"): {"income": 0.0, "expense": 0.0}
             for i in range(6)}
    for r in rows:
        trend[r["m"].strftime("%Y-%m")][r["kind"]] = float(r["total"])

    all_time = qs.aggregate(
        i=Sum("amount", filter=Q(kind="income")), e=Sum("amount", filter=Q(kind="expense")))
    return render(request, "expenses/dashboard.html", {
        "income": income, "expense": expense, "balance": income - expense,
        "delta": delta, "delta_abs": abs(delta) if delta is not None else None,
        "net_worth": (all_time["i"] or ZERO) - (all_time["e"] or ZERO),
        "top": by_category[0] if by_category else None,
        "recent": qs.select_related("category")[:6],
        "has_data": qs.exists(),
        "dash_data": {
            "by_category": by_category,
            "trend": [{"month": k, **v} for k, v in trend.items()],
        },
        "month_label": start,
    })


@login_required
def transaction_list(request):
    qs, filters = _filtered(request)
    income = _total(qs, Transaction.INCOME)
    expense = _total(qs, Transaction.EXPENSE)
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "expenses/transaction_list.html", {
        "transactions": page,
        "total_income": income,
        "total_expense": expense,
        "balance": income - expense,
        "filters": filters,
        "categories": Category.objects.filter(user=request.user),
        "querystring": query.urlencode(),
    })


@login_required
def transaction_create(request):
    initial = {}
    if request.GET.get("kind") in (Transaction.EXPENSE, Transaction.INCOME):
        initial["kind"] = request.GET["kind"]
    form = TransactionForm(request.POST or None, user=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Transaction added."))
        return redirect("expenses:list")
    return render(request, "expenses/transaction_form.html",
                  {"form": form, "title": _("Add transaction")})


@login_required
def transaction_update(request, pk):
    obj = get_object_or_404(Transaction, pk=pk, user=request.user)
    form = TransactionForm(request.POST or None, instance=obj, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Transaction updated."))
        return redirect("expenses:list")
    return render(request, "expenses/transaction_form.html",
                  {"form": form, "title": _("Edit transaction")})


@login_required
def transaction_delete(request, pk):
    obj = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == "POST":
        obj.delete()
        messages.success(request, _("Transaction deleted."))
        return redirect("expenses:list")
    return render(request, "expenses/confirm_delete.html",
                  {"object": obj, "cancel_url": "expenses:list"})


@login_required
def category_list(request):
    form = CategoryForm(request.POST or None, user=request.user,
                        initial={"color": DEFAULT_COLOR})
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Category added."))
        return redirect("expenses:category_list")
    cats = Category.objects.filter(user=request.user).annotate(
        spent=Sum("transactions__amount", filter=Q(transactions__kind="expense")))
    return render(request, "expenses/category_list.html", {"form": form, "categories": cats})


@login_required
def category_update(request, pk):
    obj = get_object_or_404(Category, pk=pk, user=request.user)
    form = CategoryForm(request.POST or None, instance=obj, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Category updated."))
        return redirect("expenses:category_list")
    return render(request, "expenses/category_form.html", {"form": form})


@login_required
def category_delete(request, pk):
    obj = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == "POST":
        obj.delete()
        messages.success(request, _("Category deleted."))
        return redirect("expenses:category_list")
    return render(request, "expenses/confirm_delete.html",
                  {"object": obj, "cancel_url": "expenses:category_list"})


@login_required
def stats(request):
    return render(request, "expenses/stats.html")


@login_required
def stats_api(request):
    qs = Transaction.objects.filter(user=request.user)
    by_category = (qs.filter(kind=Transaction.EXPENSE)
                   .values("category__name", "category__color")
                   .annotate(total=Sum("amount")).order_by("-total"))
    months = {}
    rows = (qs.annotate(month=TruncMonth("date")).values("month", "kind")
            .annotate(total=Sum("amount")).order_by("month"))
    for r in rows:
        key = r["month"].strftime("%Y-%m")
        entry = months.setdefault(key, {"month": key, "income": 0.0, "expense": 0.0})
        entry[r["kind"]] = float(r["total"])
    return JsonResponse({
        "by_category": [{"name": r["category__name"] or _("Uncategorized"),
                         "color": r["category__color"] or "#94a3b8",
                         "total": float(r["total"])} for r in by_category],
        "by_month": list(months.values()),
    })
