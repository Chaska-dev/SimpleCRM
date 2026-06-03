"""Security-focused tests for the CRM project."""

from __future__ import annotations

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .models import Company, Contact, User, Workspace


def _make_image(name: str = "tiny.png", size=(10, 10), color="red") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def _make_workspace_and_user(username="alice", password="SecretP@ss123!"):
    ws = Workspace.objects.create(name="Acme")
    user = User.objects.create_user(
        username=username, email=f"{username}@x.com", password=password
    )
    user.workspace = ws
    user.role = "OWNER"
    user.save()
    return ws, user


class DeleteMethodTests(TestCase):
    def setUp(self):
        self.ws, self.user = _make_workspace_and_user()
        self.client.force_login(self.user)

    def test_contact_delete_requires_post(self):
        contact = Contact.objects.create(
            workspace=self.ws, first_name="Bob", created_by=self.user
        )
        url = reverse("contact-delete", args=[contact.uuid])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(Contact.objects.filter(is_deleted=True).count(), 0)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertTrue(
            Contact.objects.get(uuid=contact.uuid).is_deleted
        )

    def test_company_bulk_delete_requires_post(self):
        c = Company.objects.create(workspace=self.ws, name="X")
        url = reverse("company-bulk-delete")
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url, data={"uuids": [str(c.uuid)]})
        self.assertTrue(Company.objects.get(uuid=c.uuid).is_deleted)

    def test_logout_requires_post(self):
        url = reverse("logout")
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        resp = self.client.get(reverse("dashboard"))
        self.assertNotEqual(resp.status_code, 200)


class UploadValidationTests(TestCase):
    def setUp(self):
        self.ws, self.user = _make_workspace_and_user()
        self.client.force_login(self.user)

    def test_invalid_image_type_is_rejected(self):
        bad = SimpleUploadedFile(
            "evil.jpg", b"not an image", content_type="image/jpeg"
        )
        resp = self.client.post(
            reverse("company-create"),
            data={"name": "RegularCo", "logo": bad},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Company.objects.filter(name="RegularCo").exists())

    def test_valid_image_is_accepted(self):
        ok = _make_image()
        resp = self.client.post(
            reverse("company-create"),
            data={"name": "RegularCo", "logo": ok},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Company.objects.filter(name="RegularCo").exists())


class SearchApiTests(TestCase):
    def setUp(self):
        self.ws, self.user = _make_workspace_and_user()
        self.client.force_login(self.user)

    def test_company_search_only_returns_workspace_data(self):
        other_ws, _ = _make_workspace_and_user(username="bob", password="x")
        Company.objects.create(workspace=self.ws, name="Mine")
        Company.objects.create(workspace=other_ws, name="NotMine")
        resp = self.client.get(reverse("company-search"), {"q": ""})
        self.assertEqual(resp.status_code, 200)
        names = [c["name"] for c in resp.json()]
        self.assertIn("Mine", names)
        self.assertNotIn("NotMine", names)


class AxesLockoutTests(TestCase):
    """Make sure the brute-force protection kicks in."""

    def setUp(self):
        _make_workspace_and_user()

    def test_lockout_after_too_many_failures(self):
        url = reverse("login")
        for _ in range(5):
            self.client.post(url, {"username": "alice", "password": "wrong"})
        # Once locked out, even the correct password must not log the user in.
        resp = self.client.post(
            url, {"username": "alice", "password": "SecretP@ss123!"}
        )
        # axes may return 200 (lockout template), 302 (redirect) or 429
        self.assertIn(resp.status_code, (200, 302, 429))
        resp = self.client.get(reverse("dashboard"))
        self.assertNotEqual(resp.status_code, 200)


class RegisterTests(TestCase):
    def test_register_creates_user_workspace_and_logs_in(self):
        resp = self.client.post(
            reverse("register"),
            data={
                "username": "newbie",
                "email": "n@x.com",
                "first_name": "New",
                "last_name": "Bie",
                "password1": "StrongP@ssword42!",
                "password2": "StrongP@ssword42!",
                "workspace_name": "NewWS",
            },
        )
        # Should redirect to dashboard (logged in successfully)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("dashboard"))
        from crm.models import User, Workspace

        self.assertTrue(User.objects.filter(username="newbie").exists())
        self.assertTrue(Workspace.objects.filter(name="NewWS").exists())
        # Authenticated after register
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)


class ContactCreateRegressionTest(TestCase):
    """Regression: contact_create should not try to set name_es/name_en on
    the Company model (which has only ``name``)."""

    def setUp(self):
        self.ws, self.user = _make_workspace_and_user()
        self.client.force_login(self.user)

    def test_create_contact_with_inline_company(self):
        from .models import Company, Contact

        resp = self.client.post(
            reverse("contact-create"),
            data={"first_name": "Alice", "company": "AcmeCorp"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Company.objects.filter(name="AcmeCorp").exists())
        self.assertTrue(
            Contact.objects.filter(first_name="Alice", company__name="AcmeCorp").exists()
        )


class WorkspaceBrandingTests(TestCase):
    def setUp(self):
        self.ws, self.user = _make_workspace_and_user()
        self.client.force_login(self.user)

    def test_branding_form_updates_company_name(self):
        resp = self.client.post(
            reverse("settings"),
            data={
                "_action": "branding",
                "name": self.ws.name,
                "company_name": "My Custom CRM",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.ws.refresh_from_db()
        self.assertEqual(self.ws.company_name, "My Custom CRM")

    def test_branding_form_accepts_blank_company_name(self):
        self.ws.company_name = "Something"
        self.ws.save()
        self.client.post(
            reverse("settings"),
            data={
                "_action": "branding",
                "name": self.ws.name,
                "company_name": "",
            },
        )
        self.ws.refresh_from_db()
        self.assertEqual(self.ws.company_name, "")

    def test_branding_form_renames_workspace_and_its_company(self):
        resp = self.client.post(
            reverse("settings"),
            data={
                "_action": "branding",
                "name": "Renamed Corp",
                "company_name": "",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.ws.refresh_from_db()
        self.assertEqual(self.ws.name, "Renamed Corp")
        sys_co = Company.objects.get(workspace=self.ws, is_workspace=True)
        self.assertEqual(sys_co.name, "Renamed Corp")

    def test_remove_logo_endpoint(self):
        # Upload a logo first
        img = _make_image("logo.png")
        self.client.post(
            reverse("settings"),
            data={
                "_action": "branding",
                "name": self.ws.name,
                "company_name": "",
                "logo": img,
            },
        )
        self.ws.refresh_from_db()
        self.assertTrue(bool(self.ws.logo))

        # Now remove it
        self.client.post(
            reverse("settings"),
            data={"_action": "remove_logo"},
        )
        self.ws.refresh_from_db()
        self.assertFalse(bool(self.ws.logo))

    def test_settings_page_renders_branding_form(self):
        resp = self.client.get(reverse("settings"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("branding_form", resp.context)
        self.assertIn("workspace", resp.context)


class WorkspaceCompanyTests(TestCase):
    """The system Company that mirrors the workspace should be created
    automatically and protected from deletion."""

    def setUp(self):
        self.ws, self.user = _make_workspace_and_user()
        self.client.force_login(self.user)

    def test_workspace_creates_a_system_company(self):
        sys_co = Company.objects.get(workspace=self.ws, is_workspace=True)
        self.assertEqual(sys_co.name, self.ws.name)

    def test_workspace_company_cannot_be_deleted_individually(self):
        sys_co = Company.objects.get(workspace=self.ws, is_workspace=True)
        resp = self.client.post(
            reverse("company-delete", args=[sys_co.uuid])
        )
        self.assertEqual(resp.status_code, 302)
        sys_co.refresh_from_db()
        self.assertFalse(sys_co.is_deleted, "Workspace company must not be soft-deleted")
        # The user should still be able to find it on the companies page
        self.assertTrue(
            Company.objects.filter(uuid=sys_co.uuid, is_deleted=False).exists()
        )

    def test_workspace_company_is_skipped_in_bulk_delete(self):
        sys_co = Company.objects.get(workspace=self.ws, is_workspace=True)
        regular = Company.objects.create(workspace=self.ws, name="Acme")
        self.client.post(
            reverse("company-bulk-delete"),
            data={"uuids": [str(sys_co.uuid), str(regular.uuid)]},
        )
        sys_co.refresh_from_db()
        regular.refresh_from_db()
        self.assertFalse(sys_co.is_deleted, "Workspace company must be skipped")
        self.assertTrue(regular.is_deleted, "Regular company should be deleted")

    def test_workspace_company_appears_in_companies_list(self):
        resp = self.client.get(reverse("companies"))
        self.assertEqual(resp.status_code, 200)
        # The list should contain the system company
        names = [c.name for c in resp.context["companies"]]
        self.assertIn(self.ws.name, names)
        # It should be flagged as the workspace company
        sys_co = Company.objects.get(workspace=self.ws, is_workspace=True)
        self.assertIn(sys_co, list(resp.context["companies"]))

    def test_workspace_company_can_be_edited(self):
        sys_co = Company.objects.get(workspace=self.ws, is_workspace=True)
        resp = self.client.post(
            reverse("company-edit", args=[sys_co.uuid]),
            data={
                "name": sys_co.name,
                "legal_name": "My Legal Name LLC",
                "phone": "+1 555 1234",
                "email": "hello@example.com",
            },
        )
        self.assertEqual(resp.status_code, 302)
        sys_co.refresh_from_db()
        self.assertEqual(sys_co.legal_name, "My Legal Name LLC")
        self.assertEqual(sys_co.phone, "+1 555 1234")
        self.assertEqual(sys_co.email, "hello@example.com")
