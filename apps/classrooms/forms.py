from decimal import Decimal
from django import forms
from .models import SchoolClass


class SchoolClassForm(forms.ModelForm):
    """Form for creating and updating SchoolClass records."""

    class Meta:
        model = SchoolClass
        fields = ["name", "order", "monthly_fee"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Class 1, Nursery, Grade 10-A",
                    "required": True,
                    "autofocus": True,
                }
            ),
            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Display order (e.g. 1, 2, 3)",
                    "min": "0",
                }
            ),
            "monthly_fee": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Standard monthly tuition fee (Rs)",
                    "step": "0.01",
                    "min": "0",
                    "required": True,
                }
            ),
        }
        labels = {
            "name": "Class Name",
            "order": "Display Order",
            "monthly_fee": "Monthly Tuition Fee (Rs)",
        }
        help_texts = {
            "name": "Unique name or grade level for the class.",
            "order": "Sorting order in lists and dropdowns.",
            "monthly_fee": "Default monthly tuition fee charged to students of this class.",
        }

    def clean_monthly_fee(self):
        fee = self.cleaned_data.get("monthly_fee")
        if fee is not None and fee < Decimal("0.00"):
            raise forms.ValidationError("Monthly fee cannot be negative.")
        return fee
