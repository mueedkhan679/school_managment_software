import os
import re
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.classrooms.models import SchoolClass
from apps.core.constants import MONTHS_MAP
from .models import SalaryStatus, Teacher, TeacherSalary

ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

CNIC_PATTERN = re.compile(r"^\d{5}-\d{7}-\d$")
PHONE_DIGITS_PATTERN = re.compile(r"^\d{10,13}$")


def validate_cnic_format(value):
    """Optional CNIC: when provided, must be 13 digits formatted 00000-0000000-0.

    Spaces are tolerated and stripped before validation so copy-pasted values
    fail loudly with a clear message instead of being stored in a bad shape.
    """
    if not value:
        return value
    normalized = re.sub(r"\s+", "", str(value))
    if not CNIC_PATTERN.match(normalized):
        raise ValidationError(
            "CNIC must contain exactly 13 digits formatted like 35201-1234567-1."
        )
    return normalized


def validate_phone_number(value):
    """Required phone: tolerate spaces/dashes/brackets but require 10-13 digits."""
    digits = re.sub(r"[\s\-()+]", "", str(value or ""))
    if not PHONE_DIGITS_PATTERN.match(digits):
        raise ValidationError(
            "Enter a valid phone number containing 10-13 digits (e.g. 0300-1234567)."
        )
    return str(value).strip()


def validate_uploaded_image(image_file):
    """Helper to validate image file extension and file size."""
    if image_file and hasattr(image_file, "size"):
        if image_file.size > MAX_IMAGE_SIZE_BYTES:
            raise ValidationError("File size must not exceed 5MB.")
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file format '{ext}'. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )
    return image_file


class TeacherForm(forms.ModelForm):
    """Form for adding and editing Teacher profiles."""

    class Meta:
        model = Teacher
        fields = [
            "name",
            "cnic",
            "phone",
            "address",
            "monthly_salary",
            "assigned_class",
            "assigned_classes",
            "picture",
            "cnic_front_pic",
            "cnic_back_pic",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Teacher's Full Name", "required": True}
            ),
            "cnic": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. 35201-1234567-1 (Optional)"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. 0300-1234567", "required": True}
            ),
            "address": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Residential Address (Optional)"}
            ),
            "monthly_salary": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Monthly base salary (Rs)",
                    "step": "0.01",
                    "min": "0.01",
                    "required": True,
                }
            ),
            "assigned_class": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
            "assigned_classes": forms.SelectMultiple(
                attrs={"class": "form-control", "size": "4"}
            ),
            "picture": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/jpeg,image/png,image/webp"}
            ),
            "cnic_front_pic": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/jpeg,image/png,image/webp"}
            ),
            "cnic_back_pic": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/jpeg,image/png,image/webp"}
            ),
        }
        labels = {
            "name": "Teacher Full Name *",
            "cnic": "CNIC Number (Optional)",
            "phone": "Phone Number *",
            "address": "Home Address (Optional)",
            "monthly_salary": "Monthly Salary (Rs) *",
            "assigned_class": "Assigned Class (Class Teacher) *",
            "assigned_classes": "Additional Assigned Classes (Optional)",
            "picture": "Teacher Photograph (Optional)",
            "cnic_front_pic": "CNIC Front Picture (Optional)",
            "cnic_back_pic": "CNIC Back Picture (Optional)",
        }
        help_texts = {
            "monthly_salary": "Annual salary will be automatically calculated as Monthly x 12.",
            "assigned_class": "Select the primary class managed by this teacher (mandatory).",
            "picture": "Supported formats: JPG, PNG, WEBP. Max size: 5MB.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_class"].queryset = SchoolClass.objects.order_by("order", "id")
        self.fields["assigned_class"].empty_label = "-- Select Assigned Class * --"
        self.fields["assigned_classes"].queryset = SchoolClass.objects.order_by("order", "id")
        self.fields["assigned_classes"].required = False

    def clean(self):
        cleaned_data = super().clean()
        assigned_class = cleaned_data.get("assigned_class")
        assigned_classes = cleaned_data.get("assigned_classes")

        if not assigned_class:
            if assigned_classes and assigned_classes.exists():
                cleaned_data["assigned_class"] = assigned_classes.first()
            else:
                self.add_error("assigned_class", "Please select an assigned class for this teacher.")

        return cleaned_data

    def clean_picture(self):
        return validate_uploaded_image(self.cleaned_data.get("picture"))

    def clean_cnic_front_pic(self):
        return validate_uploaded_image(self.cleaned_data.get("cnic_front_pic"))

    def clean_cnic_back_pic(self):
        return validate_uploaded_image(self.cleaned_data.get("cnic_back_pic"))

    def clean_monthly_salary(self):
        salary = self.cleaned_data.get("monthly_salary")
        if salary is not None and salary <= Decimal("0.00"):
            raise ValidationError("Monthly salary must be greater than zero.")
        return salary

    def clean_phone(self):
        return validate_phone_number(self.cleaned_data.get("phone"))

    def clean_cnic(self):
        return validate_cnic_format(self.cleaned_data.get("cnic"))

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            if instance.assigned_class:
                instance.assigned_classes.add(instance.assigned_class)
        else:
            old_save_m2m = self.save_m2m
            def new_save_m2m():
                old_save_m2m()
                if instance.assigned_class:
                    instance.assigned_classes.add(instance.assigned_class)
            self.save_m2m = new_save_m2m
        return instance


class TeacherSalaryForm(forms.ModelForm):
    """Form for recording teacher salary disbursements."""

    class Meta:
        model = TeacherSalary
        fields = [
            "teacher",
            "salary_month",
            "salary_year",
            "amount",
            "payment_date",
            "status",
            "reference",
        ]
        widgets = {
            "teacher": forms.Select(
                attrs={"class": "form-control", "required": True, "id": "id_teacher"}
            ),
            "salary_month": forms.Select(
                attrs={"class": "form-control", "required": True, "id": "id_salary_month"}
            ),
            "salary_year": forms.NumberInput(
                attrs={"class": "form-control", "required": True, "min": "2000", "max": "2100", "id": "id_salary_year"}
            ),
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "required": True, "step": "0.01", "min": "0.01", "id": "id_amount"}
            ),
            "payment_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "required": True}
            ),
            "status": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
            "reference": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Payment Reference / Receipt # (Leave empty to auto-generate)"}
            ),
        }
        labels = {
            "teacher": "Teacher *",
            "salary_month": "Salary Month *",
            "salary_year": "Salary Year *",
            "amount": "Disbursed Salary Amount (Rs) *",
            "payment_date": "Payment Date *",
            "status": "Payment Status *",
            "reference": "Payment Reference #",
        }
        help_texts = {
            "amount": "Pre-filled with the teacher's configured monthly base salary.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["teacher"].queryset = Teacher.objects.filter(is_active=True).order_by("name")
        self.fields["teacher"].label_from_instance = (
            lambda t: f"{t.name} ({t.teacher_id}) — Base Salary: Rs {t.monthly_salary:.0f}"
        )

        now = timezone.now()
        if not self.is_bound:
            if not self.initial.get("salary_month"):
                self.initial["salary_month"] = now.month
            if not self.initial.get("salary_year"):
                self.initial["salary_year"] = now.year
            if not self.initial.get("payment_date"):
                self.initial["payment_date"] = now.date().isoformat()
            if not self.initial.get("status"):
                self.initial["status"] = SalaryStatus.PAID

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= Decimal("0.00"):
            raise ValidationError("Salary amount must be greater than zero.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        teacher = cleaned_data.get("teacher")
        salary_month = cleaned_data.get("salary_month")
        salary_year = cleaned_data.get("salary_year")
        reference = cleaned_data.get("reference", "").strip()

        if teacher and salary_month and salary_year:
            # Check for duplicate salary payment in the same month + year
            query = TeacherSalary.objects.filter(
                teacher=teacher,
                salary_month=salary_month,
                salary_year=salary_year,
            )
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                month_name = MONTHS_MAP.get(int(salary_month), str(salary_month))
                raise ValidationError(
                    f"A salary payment for {teacher.name} ({teacher.teacher_id}) for {month_name} {salary_year} "
                    f"has already been disbursed/recorded."
                )

            # Auto-generate reference number if left blank
            if not reference:
                cleaned_data["reference"] = f"SAL-{salary_year}{int(salary_month):02d}-{teacher.id:04d}"

        return cleaned_data
