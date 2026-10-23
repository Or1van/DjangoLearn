from django import forms
from django.utils.translation import gettext as _

from .models import DEFAULT_COLOR, DEFAULT_ICON, Category, Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["kind", "title", "amount", "category", "date", "note"]
        widgets = {
            "kind": forms.RadioSelect,
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0.01",
                                               "inputmode": "decimal", "placeholder": "0.00"}),
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["category"].queryset = Category.objects.filter(user=user)

    def save(self, commit=True):
        self.instance.user = self.user
        return super().save(commit)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "icon", "color"]
        widgets = {
            "color": forms.TextInput(attrs={"type": "color"}),
            "icon": forms.TextInput(attrs={"placeholder": "🍕", "maxlength": 8}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["color"].required = False

    def clean_color(self):
        return self.cleaned_data.get("color") or DEFAULT_COLOR

    def clean_icon(self):
        return self.cleaned_data.get("icon", "").strip() or DEFAULT_ICON

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        clash = Category.objects.filter(user=self.user, name=name).exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError(_("You already have a category with this name."))
        return name

    def save(self, commit=True):
        self.instance.user = self.user
        return super().save(commit)
