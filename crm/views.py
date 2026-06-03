"""CRM views.

All write actions (create/edit/delete/logout) require POST and CSRF.
The image upload pipeline is shared through :mod:`crm.utils`.
"""

from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from .forms import LoginForm, UserRegistrationForm, WorkspaceBrandingForm
from .models import City, Company, Contact, Country, State
from .utils import (
    crop_and_save_image,
    get_or_create_locale,
    parse_uuids,
    search_location,
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Multiple backends configured (axes + ModelBackend); tell login
            # which one to use.
            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            messages.success(request, "Account created successfully!")
            return redirect("dashboard")
    else:
        form = UserRegistrationForm()
    return render(request, "auth/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("dashboard")
            messages.error(request, "Invalid username or password")
    else:
        form = LoginForm()
    return render(request, "auth/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


# ---------------------------------------------------------------------------
# Dashboard / settings
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    workspace = request.user.workspace
    contacts = (
        Contact.objects.filter(workspace=workspace, is_deleted=False)
        .select_related()
        .prefetch_related("company_relationships__company")
    )
    companies = Company.objects.filter(workspace=workspace, is_deleted=False)
    context = {
        "contacts": contacts,
        "contacts_count": contacts.count(),
        "companies_count": companies.count(),
    }
    return render(request, "dashboard.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def settings(request):
    user = request.user
    workspace = user.workspace

    if request.method == "GET" and request.GET.get("remove_avatar") == "1" and user.avatar:
        user.avatar.delete(save=False)
        user.save()
        messages.success(request, "Profile picture removed.")
        return redirect("settings")

    if request.method == "POST" and request.FILES.get("avatar"):
        avatar_file = request.FILES["avatar"]
        processed = crop_and_save_image(
            avatar_file,
            prefix=f"{user.username}_avatar",
            crop_x=request.POST.get("crop_x", "0"),
            crop_y=request.POST.get("crop_y", "0"),
            crop_size=request.POST.get("crop_size", "50"),
        )
        if processed is None:
            messages.error(request, "Please upload a valid image file (jpg, png, webp).")
            return redirect("settings")
        if user.avatar:
            user.avatar.delete(save=False)
        user.avatar = processed
        user.save()
        messages.success(request, "Profile picture updated successfully!")
        return redirect("settings")

    if request.method == "POST":
        if request.POST.get("_action") == "branding":
            branding_form = WorkspaceBrandingForm(
                request.POST, request.FILES, instance=workspace
            )
            if branding_form.is_valid():
                branding_form.save()
                messages.success(request, "Branding updated successfully!")
            else:
                for error in branding_form.errors.get_json_data(escape_html=True).values():
                    messages.error(request, "; ".join(e["message"] for e in error))
            return redirect("settings")
        if request.POST.get("_action") == "remove_logo" and workspace.logo:
            workspace.logo.delete(save=False)
            workspace.save()
            messages.success(request, "Workspace logo removed.")
            return redirect("settings")

        from django.contrib.auth.forms import PasswordChangeForm

        form = PasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Password updated successfully!")
            return redirect("settings")
    else:
        from django.contrib.auth.forms import PasswordChangeForm

        form = PasswordChangeForm(user)

    branding_form = WorkspaceBrandingForm(instance=workspace)
    return render(
        request,
        "settings.html",
        {
            "form": form,
            "branding_form": branding_form,
            "workspace": workspace,
        },
    )


# ---------------------------------------------------------------------------
# Company views
# ---------------------------------------------------------------------------
@login_required
def companies(request):
    qs = Company.objects.filter(
        workspace=request.user.workspace, is_deleted=False
    )
    return render(request, "companies/list.html", {"companies": qs})


@login_required
@require_http_methods(["GET", "POST"])
def company_create(request):
    if request.method == "POST":
        logo_file = request.FILES.get("logo")
        cropped = None
        if logo_file:
            cropped = crop_and_save_image(
                logo_file,
                prefix="company_logo",
                crop_x=request.POST.get("crop_x", "0"),
                crop_y=request.POST.get("crop_y", "0"),
                crop_size=request.POST.get("crop_size", "50"),
            )
            if cropped is None:
                messages.error(request, "Invalid logo. Use jpg, png or webp.")
                return redirect("company-create")

        Company.objects.create(
            workspace=request.user.workspace,
            created_by=request.user,
            name=request.POST.get("name", "").strip(),
            legal_name=request.POST.get("legal_name", ""),
            website=request.POST.get("website", ""),
            industry=request.POST.get("industry", ""),
            phone=request.POST.get("phone", ""),
            email=request.POST.get("email", ""),
            address=request.POST.get("address", ""),
            description=request.POST.get("description", ""),
            logo=cropped,
        )
        messages.success(request, "Company created successfully!")
        return redirect("companies")
    return render(request, "companies/create.html")


@login_required
@require_http_methods(["GET", "POST"])
def company_edit(request, company_uuid):
    company = get_object_or_404(
        Company,
        uuid=company_uuid,
        workspace=request.user.workspace,
        is_deleted=False,
    )
    if request.method == "POST":
        company.name = request.POST.get("name", company.name)
        company.legal_name = request.POST.get("legal_name", "")
        company.website = request.POST.get("website", "")
        company.industry = request.POST.get("industry", "")
        company.phone = request.POST.get("phone", "")
        company.email = request.POST.get("email", "")
        company.address = request.POST.get("address", "")
        company.description = request.POST.get("description", "")

        logo_file = request.FILES.get("logo")
        if logo_file:
            processed = crop_and_save_image(
                logo_file,
                prefix="company_logo",
                crop_x=request.POST.get("crop_x", "0"),
                crop_y=request.POST.get("crop_y", "0"),
                crop_size=request.POST.get("crop_size", "50"),
            )
            if processed is None:
                messages.error(request, "Invalid logo. Use jpg, png or webp.")
                return redirect("company-edit", company_uuid=company.uuid)
            if company.logo:
                company.logo.delete(save=False)
            company.logo = processed
        company.save()
        messages.success(request, "Company updated successfully!")
        return redirect("companies")
    return render(request, "companies/edit.html", {"company": company})


@login_required
@require_POST
def company_delete(request, company_uuid):
    company = get_object_or_404(
        Company,
        uuid=company_uuid,
        workspace=request.user.workspace,
        is_deleted=False,
    )
    if company.is_workspace:
        messages.error(
            request,
            "The workspace company cannot be deleted. Edit it from Settings or Companies.",
        )
        return redirect("companies")
    company.is_deleted = True
    company.save()
    messages.success(request, "Company deleted successfully!")
    return redirect("companies")


@login_required
@require_POST
def company_bulk_delete(request):
    uuids = parse_uuids(request.POST.getlist("uuids"))
    if not uuids:
        messages.error(request, "No companies selected.")
        return redirect("companies")
    deleted = Company.objects.filter(
        uuid__in=uuids,
        workspace=request.user.workspace,
        is_deleted=False,
        is_workspace=False,
    ).update(is_deleted=True)
    skipped = len(uuids) - deleted
    if skipped:
        messages.warning(
            request,
            f"{deleted} company(s) deleted. {skipped} skipped (workspace company is protected).",
        )
    else:
        messages.success(
            request, f"{deleted} company(s) deleted successfully!"
        )
    return redirect("companies")


# ---------------------------------------------------------------------------
# Contact views
# ---------------------------------------------------------------------------
@login_required
def contacts(request):
    qs = Contact.objects.filter(
        workspace=request.user.workspace, is_deleted=False
    )
    return render(request, "contacts/list.html", {"contacts": qs})


def _resolve_location(request, *, country_field="country", state_field="state", city_field="city"):
    """Resolve Country/State/City from form payload, creating when missing."""
    country_id = request.POST.get(f"{country_field}_id", "")
    country_name = request.POST.get(country_field, "")
    if country_id.isdigit():
        country_obj = Country.objects.filter(id=int(country_id)).first()
    else:
        country_obj = get_or_create_locale(Country, country_name)

    state_id = request.POST.get(f"{state_field}_id", "")
    state_name = request.POST.get(state_field, "")
    if state_id.isdigit() and country_obj:
        state_obj = State.objects.filter(id=int(state_id), country=country_obj).first()
    else:
        state_obj = (
            get_or_create_locale(State, state_name, parent=country_obj)
            if country_obj
            else None
        )

    city_id = request.POST.get(f"{city_field}_id", "")
    city_name = request.POST.get(city_field, "")
    if city_id.isdigit() and state_obj:
        city_obj = City.objects.filter(id=int(city_id), state=state_obj).first()
    else:
        city_obj = (
            get_or_create_locale(City, city_name, parent=state_obj, code_length=0)
            if state_obj
            else None
        )
    return country_obj, state_obj, city_obj


def _parse_custom_socials(request):
    raw = request.POST.get("custom_social_profiles", "[]") or "[]"
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    cleaned = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        url = str(item.get("url", "")).strip()
        if name and url:
            cleaned.append({"name": name[:100], "url": url[:500]})
    return cleaned


@login_required
@require_http_methods(["GET", "POST"])
def contact_create(request):
    if request.method == "POST":
        workspace = request.user.workspace
        company = get_or_create_locale(
            Company,
            request.POST.get("company", ""),
            parent_field="workspace",
            extra_defaults={"workspace": workspace},
            code_length=0,
        )
        country, state, city = _resolve_location(request)

        avatar_file = request.FILES.get("avatar")
        cropped_avatar = None
        if avatar_file:
            cropped_avatar = crop_and_save_image(
                avatar_file,
                prefix="contact_avatar",
                crop_x=request.POST.get("crop_x", "0"),
                crop_y=request.POST.get("crop_y", "0"),
                crop_size=request.POST.get("crop_size", "50"),
            )
            if cropped_avatar is None:
                messages.error(request, "Invalid avatar. Use jpg, png or webp.")
                return redirect("contact-create")

        Contact.objects.create(
            workspace=workspace,
            created_by=request.user,
            first_name=request.POST.get("first_name", "").strip(),
            middle_name=request.POST.get("middle_name", ""),
            last_name=request.POST.get("last_name", ""),
            nickname=request.POST.get("nickname", ""),
            gender=request.POST.get("gender", ""),
            birthday=request.POST.get("birthday") or None,
            personal_email=request.POST.get("personal_email", ""),
            work_email=request.POST.get("work_email", ""),
            personal_phone=request.POST.get("personal_phone", ""),
            work_phone=request.POST.get("work_phone", ""),
            company=company,
            website=request.POST.get("website", ""),
            address=request.POST.get("address", ""),
            country=country,
            state=state,
            city=city,
            notes=request.POST.get("notes", ""),
            linkedin=request.POST.get("linkedin", ""),
            github=request.POST.get("github", ""),
            facebook=request.POST.get("facebook", ""),
            instagram=request.POST.get("instagram", ""),
            twitter=request.POST.get("twitter", ""),
            tiktok=request.POST.get("tiktok", ""),
            youtube=request.POST.get("youtube", ""),
            telegram=request.POST.get("telegram", ""),
            discord=request.POST.get("discord", ""),
            custom_social_profiles=_parse_custom_socials(request),
            avatar=cropped_avatar,
        )
        messages.success(request, "Contact created successfully!")
        return redirect("contacts")
    return render(request, "contacts/create.html")


@login_required
@require_http_methods(["GET", "POST"])
def contact_edit(request, contact_uuid):
    contact = get_object_or_404(
        Contact,
        uuid=contact_uuid,
        workspace=request.user.workspace,
        is_deleted=False,
    )
    if request.method == "POST":
        contact.first_name = request.POST.get("first_name", contact.first_name)
        contact.middle_name = request.POST.get("middle_name", "")
        contact.last_name = request.POST.get("last_name", "")
        contact.nickname = request.POST.get("nickname", "")
        contact.gender = request.POST.get("gender", "")
        contact.birthday = request.POST.get("birthday") or None
        contact.personal_email = request.POST.get("personal_email", "")
        contact.work_email = request.POST.get("work_email", "")
        contact.personal_phone = request.POST.get("personal_phone", "")
        contact.work_phone = request.POST.get("work_phone", "")
        contact.company = get_or_create_locale(
            Company,
            request.POST.get("company", ""),
            parent_field="workspace",
            extra_defaults={"workspace": request.user.workspace},
            code_length=0,
        )
        contact.country, contact.state, contact.city = _resolve_location(request)
        contact.website = request.POST.get("website", "")
        contact.address = request.POST.get("address", "")
        contact.notes = request.POST.get("notes", "")

        contact.linkedin = request.POST.get("linkedin", "")
        contact.github = request.POST.get("github", "")
        contact.facebook = request.POST.get("facebook", "")
        contact.instagram = request.POST.get("instagram", "")
        contact.twitter = request.POST.get("twitter", "")
        contact.tiktok = request.POST.get("tiktok", "")
        contact.youtube = request.POST.get("youtube", "")
        contact.telegram = request.POST.get("telegram", "")
        contact.discord = request.POST.get("discord", "")
        contact.custom_social_profiles = _parse_custom_socials(request)

        avatar_file = request.FILES.get("avatar")
        if avatar_file:
            processed = crop_and_save_image(
                avatar_file,
                prefix="contact_avatar",
                crop_x=request.POST.get("crop_x", "0"),
                crop_y=request.POST.get("crop_y", "0"),
                crop_size=request.POST.get("crop_size", "50"),
            )
            if processed is None:
                messages.error(request, "Invalid avatar. Use jpg, png or webp.")
                return redirect("contact-edit", contact_uuid=contact.uuid)
            if contact.avatar:
                contact.avatar.delete(save=False)
            contact.avatar = processed

        contact.save()
        messages.success(request, "Contact updated successfully!")
        if request.POST.get("from_dashboard"):
            return redirect("dashboard")
        return redirect("contacts")
    return render(
        request,
        "contacts/edit.html",
        {
            "contact": contact,
            "custom_social_profiles_json": contact.custom_social_profiles,
        },
    )


@login_required
@require_POST
def contact_delete(request, contact_uuid):
    contact = get_object_or_404(
        Contact,
        uuid=contact_uuid,
        workspace=request.user.workspace,
        is_deleted=False,
    )
    contact.is_deleted = True
    contact.save()
    messages.success(request, "Contact deleted successfully!")
    return redirect("contacts")


@login_required
@require_POST
def contact_bulk_delete(request):
    uuids = parse_uuids(request.POST.getlist("uuids"))
    if not uuids:
        messages.error(request, "No contacts selected.")
        return redirect("contacts")
    deleted = Contact.objects.filter(
        uuid__in=uuids,
        workspace=request.user.workspace,
        is_deleted=False,
    ).update(is_deleted=True)
    messages.success(
        request, f"{deleted} contact(s) deleted successfully!"
    )
    return redirect("contacts")


# ---------------------------------------------------------------------------
# JSON search endpoints (login_required, throttled)
# ---------------------------------------------------------------------------
def _throttle(key: str, limit: int = 30, window: int = 60):
    """Cache-backed throttle: at most ``limit`` calls per ``window`` seconds."""
    count = cache.get(key, 0)
    if count >= limit:
        return False
    cache.set(key, count + 1, window)
    return True


@login_required
def company_search(request):
    if not _throttle(f"search:company:{request.user.pk}"):
        return JsonResponse({"error": "rate_limited"}, status=429)
    query = request.GET.get("q", "")
    qs = Company.objects.filter(
        workspace=request.user.workspace, is_deleted=False
    )
    if query:
        qs = qs.filter(name__icontains=query)
    rows = qs.values("id", "name")[:10]
    return JsonResponse(list(rows), safe=False)


@login_required
def country_search(request):
    if not _throttle(f"search:country:{request.user.pk}"):
        return JsonResponse({"error": "rate_limited"}, status=429)
    return JsonResponse(
        search_location(
            Country,
            query=request.GET.get("q", ""),
            lang=request.GET.get("lang", "es"),
            code_length=None,
        ),
        safe=False,
    )


@login_required
def state_search(request):
    if not _throttle(f"search:state:{request.user.pk}"):
        return JsonResponse({"error": "rate_limited"}, status=429)
    country_obj = None
    country_id = request.GET.get("country", "")
    if country_id.isdigit():
        country_obj = Country.objects.filter(id=int(country_id)).first()
    return JsonResponse(
        search_location(
            State,
            query=request.GET.get("q", ""),
            lang=request.GET.get("lang", "es"),
            parent=country_obj,
        ),
        safe=False,
    )


@login_required
def city_search(request):
    if not _throttle(f"search:city:{request.user.pk}"):
        return JsonResponse({"error": "rate_limited"}, status=429)
    state_obj = None
    state_id = request.GET.get("state", "")
    if state_id.isdigit():
        state_obj = State.objects.filter(id=int(state_id)).first()
    return JsonResponse(
        search_location(
            City,
            query=request.GET.get("q", ""),
            lang=request.GET.get("lang", "es"),
            parent=state_obj,
            parent_field="state",
        ),
        safe=False,
    )


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
@login_required
def import_export(request):
    contacts_count = Contact.objects.filter(
        workspace=request.user.workspace, is_deleted=False
    ).count()
    return render(
        request, "import_export.html", {"contacts_count": contacts_count}
    )


def buttons(request):
    return render(request, "buttons.html")
