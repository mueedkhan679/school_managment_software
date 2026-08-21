from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.constants import MONTHS, MONTHS_MAP
from apps.students.models import Student
from .models import FeeStatus, StudentFee


class StudentFeeForm(forms.ModelForm):
    """Form for collecting and managing Student Fee payments."""

    class Meta:
        model = StudentFee
        fields = [
            "student",
            "fee_month",
            "fee_year",
            "amount",
            "payment_date",
            "status",
            "reference",
            "is_extra",
        ]
        widgets = {
            "student": forms.Select(
                attrs={"class": "form-control", "required": True, "id": "id_student"}
            ),
            "fee_month": forms.Select(
                attrs={"class": "form-control", "required": True, "id": "id_fee_month"}
            ),
            "fee_year": forms.NumberInput(
                attrs={"class": "form-control", "required": True, "min": "2000", "max": "2100", "id": "id_fee_year"}
            ),
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "required": True, "step": "0.01", "min": "0.01", "id": "id_amount"}
            ),
            "payment_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "required": True, "id": "id_payment_date"}
            ),
            "status": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
            "reference": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Receipt / Voucher # (Leave empty to auto-generate)"}
            ),
            "is_extra": forms.CheckboxInput(
                attrs={"class": "form-checkbox", "id": "id_is_extra"}
            ),
        }
        labels = {
            "student": "Student *",
            "fee_month": "Fee Month *",
            "fee_year": "Fee Year *",
            "amount": "Fee Amount (Rs) *",
            "payment_date": "Payment Date *",
            "status": "Payment Status *",
            "reference": "Receipt / Voucher Number",
            "is_extra": "Allow Extra / Additional Payment for this month",
        }
        help_texts = {
            "amount": "Standard amount is pre-filled according to class fee or custom student fee override.",
            "is_extra": "Check this box only if this is a secondary/extra payment (e.g. late fee, exam fee) for the same month.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only list active students, sorted by class and student ID
        self.fields["student"].queryset = (
            Student.objects.filter(is_active=True)
            .select_related("school_class")
            .order_by("school_class__order", "student_id")
        )
        self.fields["student"].label_from_instance = (
            lambda s: f"{s.name} ({s.student_id}) — {s.school_class.name} (Rs {s.effective_monthly_fee:.0f})"
        )

        now = timezone.now()
        if not self.is_bound:
            if not self.initial.get("fee_month"):
                self.initial["fee_month"] = now.month
            if not self.initial.get("fee_year"):
                self.initial["fee_year"] = now.year
            if not self.initial.get("payment_date"):
                self.initial["payment_date"] = now.date().isoformat()
            if not self.initial.get("status"):
                self.initial["status"] = FeeStatus.PAID

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= Decimal("0.00"):
            raise ValidationError("Payment amount must be greater than zero.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get("student")
        fee_month = cleaned_data.get("fee_month")
        fee_year = cleaned_data.get("fee_year")
        is_extra = cleaned_data.get("is_extra", False)
        reference = cleaned_data.get("reference", "").strip()

        if student and fee_month and fee_year and not is_extra:
            # Check for existing fee for the same student + month + year
            query = StudentFee.objects.filter(
                student=student,
                fee_month=fee_month,
                fee_year=fee_year,
                is_extra=False,
            )
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                month_name = MONTHS_MAP.get(int(fee_month), str(fee_month))
                raise ValidationError(
                    f"A standard fee payment for {student.name} ({student.student_id}) for {month_name} {fee_year} "
                    f"has already been recorded. To record an extra or separate fee for this same month, "
                    f"please check the 'Allow Extra / Additional Payment' checkbox."
                )

        # Auto-generate reference number if left blank
        if not reference and student and fee_year and fee_month:
            cleaned_data["reference"] = f"REC-{fee_year}{int(fee_month):02d}-{student.id:04d}"

        return cleaned_data
