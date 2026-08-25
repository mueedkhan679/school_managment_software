"""Regression tests: teacher form validation failures must be VISIBLE in HTML.

Bug fixed here: the template never rendered the required ``assigned_class``
field nor its errors, so a failed submission (e.g. no class chosen) re-rendered
silently — the user saw no explanation for why nothing was saved.
"""
import io
from decimal import Decimal

from PIL import Image

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.classrooms.models import SchoolClass
from apps.teachers.forms import validate_uploaded_image
from apps.teachers.models import Teacher

User = get_user_model()


def jpeg_bytes(color="red"):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color).save(buf, "jpeg")
    return buf.getvalue()


class TeacherFormErrorVisibilityTests(TestCase):
    """Every validation failure must show up in the re-rendered page."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="vis_admin", password="password123", role=Role.ADMIN,
        )
        self.cls = SchoolClass.objects.create(
            name="Vis Class", order=1, monthly_fee=Decimal("1500.00"),
        )
        self.base_data = {
            "name": "Visible Teacher",
            "phone": "03001234567",
            "monthly_salary": "30000.00",
        }

    def _post(self, data, files=None):
        self.client.force_login(self.admin)
        payload = {**self.base_data, **data}
        return self.client.post(reverse("teachers:create"), data=payload, files=files)

    # ---- Template coverage -------------------------------------------------

    def test_create_page_renders_primary_class_select_and_multiselect(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse("teachers:create"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'name="assigned_class"')
        self.assertContains(res, 'name="assigned_classes"')

    # ---- The reported silent failure ---------------------------------------

    def test_missing_class_error_is_visible_and_nothing_saved(self):
        res = self._post({"assigned_classes": []})
        self.assertEqual(res.status_code, 200)  # form re-rendered
        self.assertFalse(
            Teacher.objects.filter(name="Visible Teacher").exists(),
            "Nothing must be saved when validation fails.",
        )
        # Global alert banner + the specific reason are both on the page.
        self.assertContains(res, "was not saved")
        self.assertContains(res, "Please select an assigned class")

    # ---- New format rules surface clear messages ----------------------------

    def test_bad_cnic_format_error_is_visible(self):
        res = self._post({
            "cnic": "12-abcd",
            "assigned_class": str(self.cls.id),
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "35201-1234567-1")
        self.assertFalse(Teacher.objects.filter(name="Visible Teacher").exists())

    def test_bad_phone_error_is_visible(self):
        res = self._post({
            "phone": "abc-def",
            "assigned_class": str(self.cls.id),
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "valid phone number")
        self.assertFalse(Teacher.objects.filter(name="Visible Teacher").exists())

    def test_corrupt_image_error_is_visible_without_crashing(self):
        garbage = SimpleUploadedFile(
            "photo.jpg", b"this-is-not-an-image", content_type="image/jpeg",
        )
        res = self._post({
            "assigned_class": str(self.cls.id),
            "picture": garbage,   # uploaded inside data, multipart auto-detected
        })
        self.assertEqual(res.status_code, 200)  # re-rendered, never a 500
        self.assertContains(res, "Upload a valid image")
        self.assertFalse(Teacher.objects.filter(name="Visible Teacher").exists())

    def test_oversized_upload_rejected_by_size_validator(self):
        big = SimpleUploadedFile(
            "big.jpg", b"x" * (5 * 1024 * 1024 + 1), content_type="image/jpeg",
        )
        with self.assertRaises(ValidationError):
            validate_uploaded_image(big)


class TeacherFormValidSubmissionStillSavesTests(TestCase):
    """Guard against regressions: valid data (primary class picked) saves."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="save_admin", password="password123", role=Role.ADMIN,
        )
        self.cls = SchoolClass.objects.create(
            name="Save Class", order=1, monthly_fee=Decimal("1500.00"),
        )

    def test_valid_submission_redirects_and_saves_with_primary_class(self):
        self.client.force_login(self.admin)
        photo = SimpleUploadedFile(
            "t.jpg", jpeg_bytes(), content_type="image/jpeg",
        )
        res = self.client.post(reverse("teachers:create"), data={
            "name": "Saved Teacher",
            "phone": "0300-9876543",       # separators tolerated by validator
            "cnic": "35201-1234567-1",      # canonical CNIC format accepted
            "monthly_salary": "41000.00",
            "assigned_class": str(self.cls.id),
            "picture": photo,
        })
        self.assertEqual(res.status_code, 302)
        saved = Teacher.objects.get(name="Saved Teacher")
        self.assertEqual(saved.phone, "0300-9876543")
        self.assertEqual(saved.cnic, "35201-1234567-1")
        self.assertEqual(saved.assigned_class_id, self.cls.id)
        # Uploads must genuinely persist — guards against silent upload loss.
        self.assertTrue(bool(saved.picture), "Picture did not persist!")
        self.assertTrue(saved.picture.name.startswith("teachers/photos/"))
