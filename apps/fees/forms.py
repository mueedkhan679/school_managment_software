from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.constants import MONTHS, MONTHS_MAP
from apps.students.models import Student
from .models import FeeStatus, StudentFee


class StudentFeeForm(forms.ModelForm):
    """Form for collecting and managing Student Fee payments."""

    fee_months = forms.MultipleChoiceField(
        choices=MONTHS,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Fee Months *",
        help_text="Select one or more months to collect fees for.",
    )

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
                attrs={"class": "form-control", "id": "id_fee_month"}
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
            if not self.initial.get("fee_months"):
                self.initial["fee_months"] = [str(now.month)]
            if not self.initial.get("fee_year"):
                self.initial["fee_year"] = now.year
            if not self.initial.get("payment_date"):
                self.initial["payment_date"] = now.date().isoformat()
            if not self.initial.get("status"):
                self.initial["status"] = FeeStatus.PAID

        if self.instance and self.instance.pk:
            self.fields["fee_month"].required = True
        else:
            self.fields["fee_month"].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= Decimal("0.00"):
            raise ValidationError("Payment amount must be greater than zero.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get("student")
        fee_month = cleaned_data.get("fee_month")
        fee_months = cleaned_data.get("fee_months")
        fee_year = cleaned_data.get("fee_year")
        is_extra = cleaned_data.get("is_extra", False)
        reference = cleaned_data.get("reference", "").strip()

        selected_months = []
        if fee_months:
            selected_months = [int(m) for m in fee_months if str(m).isdigit()]
        elif fee_month:
            selected_months = [int(fee_month)]

        if self.instance and self.instance.pk:
            if not fee_month:
                self.add_error("fee_month", "Fee month is required.")
                return cleaned_data
            selected_months = [int(fee_month)]
        else:
            if not selected_months:
                self.add_error("fee_months", "Please select at least one fee month to collect.")
                return cleaned_data
            cleaned_data["fee_month"] = selected_months[0]

        cleaned_data["selected_months"] = selected_months

        if student and fee_year and not is_extra:
            session_year = student.current_session or f"{int(fee_year)}-{int(fee_year) + 1}"

            # Check for existing fee for any selected month
            query = StudentFee.objects.filter(
                student=student,
                fee_month__in=selected_months,
                fee_year=fee_year,
                is_extra=False,
            )
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            already_paid_months = list(query.values_list("fee_month", flat=True))
            if already_paid_months:
                month_names = ", ".join(MONTHS_MAP.get(int(m), str(m)) for m in sorted(already_paid_months))
                raise ValidationError(
                    f"A standard fee payment for {student.name} ({student.student_id}) for {month_names} {fee_year} "
                    f"has already been recorded. To record an extra or separate fee for this same month, "
                    f"please check the 'Allow Extra / Additional Payment' checkbox."
                )

            # Strict 12-month block for current session
            if not (self.instance and self.instance.pk) and student.school_class_id:
                current_paid = student.paid_months_count_for(student.school_class, session_year)
                if current_paid >= 12:
                    raise ValidationError(
                        f"{student.name} ({student.student_id}) has already completed all "
                        f"12 months of fees for {student.school_class.name} "
                        f"(Session {session_year}). Monthly fee collection for this session "
                        "is locked — promote the student to a new class to begin a fresh "
                        "12-month cycle, or check 'Allow Extra / Additional Payment' for "
                        "non-monthly payments."
                    )
                if current_paid + len(selected_months) > 12:
                    remaining = 12 - current_paid
                    raise ValidationError(
                        f"Selecting {len(selected_months)} month(s) exceeds the 12-month session limit for {student.name}. "
                        f"Currently {current_paid}/12 months are paid for {student.school_class.name} (Session {session_year}). "
                        f"You can collect at most {remaining} more month(s)."
                    )

        # Auto-generate reference number if left blank
        if not reference and student and fee_year and selected_months:
            if len(selected_months) == 1:
                cleaned_data["reference"] = f"REC-{fee_year}{int(selected_months[0]):02d}-{student.id:04d}"
            else:
                cleaned_data["reference"] = f"REC-{fee_year}M{min(selected_months):02d}-{max(selected_months):02d}-{student.id:04d}"

        return cleaned_data
