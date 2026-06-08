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
from django.conf import settings
from django.shortcuts import redirect
from django.utils import translation
from django.views.decorators.http import require_POST
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
from . import import_export as ie


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
def custom_404(request, exception=None):
    """Custom 404 handler. Renders templates/404.html with status 404."""
    response = render(request, "404.html", status=404)
    return response

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
# Language switcher
# ---------------------------------------------------------------------------
@require_POST
def set_language(request):
    """Persist the user's language choice on their profile and the session.

    The LocaleMiddleware already activates the language for the current
    request; we just need to remember it across requests by writing to
    the User record (so it survives session expiry) and to the session
    (so it wins over the browser's Accept-Language header).
    """
    from django.conf import settings as dj_settings
    from django.utils.translation import gettext_lazy as _

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/dashboard/"
    lang = request.POST.get("language", "").strip()
    supported = {code for code, _ in dj_settings.LANGUAGES}
    if lang not in supported:
        messages.error(request, _("Invalid language."))
        return redirect(next_url)

    translation.activate(lang)
    request.session["django_language"] = lang
    response = redirect(next_url)
    # Set the language cookie so the LocaleMiddleware picks it up next request
    response.set_cookie(
        dj_settings.LANGUAGE_COOKIE_NAME,
        lang,
        max_age=dj_settings.LANGUAGE_COOKIE_AGE,
        path=dj_settings.LANGUAGE_COOKIE_PATH,
        samesite="Lax",
    )

    if request.user.is_authenticated:
        request.user.language = lang
        request.user.save(update_fields=["language", "updated_at"])
        # Make the just-saved language effective for this request too
        request.user.refresh_from_db()

    return response


# ---------------------------------------------------------------------------
# Dashboard / settings
# ---------------------------------------------------------------------------
@login_required
def _get_sort_param(request, default, allowed):
    """Get sort parameter from request, validated against allowed options."""
    sort = request.GET.get("sort", default)
    return sort if sort in allowed else default


def dashboard(request):
    workspace = request.user.workspace
    sort = _get_sort_param(request, "-created_at", ["first_name", "-first_name", "-created_at", "created_at"])
    contacts = (
        Contact.objects.filter(workspace=workspace, is_deleted=False)
        .select_related()
        .prefetch_related("company_relationships__company")
        .order_by(sort)
    )
    companies = Company.objects.filter(workspace=workspace, is_deleted=False)

    hour = translation.gettext_noop("Good morning,")
    greeting = f"{translation.gettext(hour)} {request.user.first_name or translation.gettext('User')}"

    context = {
        "contacts": contacts,
        "contacts_count": contacts.count(),
        "companies_count": companies.count(),
        "current_sort": sort,
        "navbar_title": greeting,
    }
    return render(request, "dashboard.html", context)


@login_required
def birthdays(request):
    import calendar as cal_mod
    from datetime import date

    workspace = request.user.workspace
    today = date.today()

    # Optional month nav via ?month=YYYY-MM
    try:
        month_str = request.GET.get("month", "")
        year, month = (int(p) for p in month_str.split("-")) if month_str else (today.year, today.month)
        if not (1 <= month <= 12) or year < 1900 or year > 2200:
            year, month = today.year, today.month
    except (ValueError, AttributeError):
        year, month = today.year, today.month

    # Optional day selection via ?day=YYYY-MM-DD
    selected_day = None
    day_str = request.GET.get("day", "")
    if day_str:
        try:
            selected_day = date.fromisoformat(day_str)
        except ValueError:
            selected_day = None
    # If the selected day is not in the displayed month, drop it
    if selected_day and (selected_day.month != month or selected_day.year != year):
        selected_day = None

    # Previous/next month strings for nav
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    is_current_month = (year == today.year and month == today.month)

    birthday_contacts = list(
        Contact.objects.filter(
            workspace=workspace,
            is_deleted=False,
            birthday__isnull=False,
        ).only("uuid", "first_name", "last_name", "avatar", "birthday")
    )

    def _next_bday(birthday):
        try:
            nxt = birthday.replace(year=today.year)
        except ValueError:
            nxt = birthday.replace(year=today.year, day=1, month=3)
        if nxt < today:
            try:
                nxt = birthday.replace(year=today.year + 1)
            except ValueError:
                nxt = birthday.replace(year=today.year + 1, day=1, month=3)
        return nxt

    enriched = []
    for c in birthday_contacts:
        nxt = _next_bday(c.birthday)
        turning = None
        if c.birthday.year > 1900:
            turning = nxt.year - c.birthday.year
        enriched.append({
            "contact": c,
            "next_date": nxt,
            "days_away": (nxt - today).days,
            "turning": turning,
        })
    enriched.sort(key=lambda x: x["days_away"])

    # Birthdays in the displayed month
    month_birthdays = [
        e for e in enriched
        if e["next_date"].month == month and e["next_date"].year == year
    ]

    # Birthdays on the selected day
    selected_day_birthdays = []
    if selected_day:
        selected_day_birthdays = [
            e for e in enriched
            if e["next_date"].month == selected_day.month
            and e["next_date"].day == selected_day.day
            and e["next_date"].year >= selected_day.year
        ][:6]

    cal = cal_mod.Calendar(firstweekday=0)
    calendar_weeks = []
    for week in cal.monthdayscalendar(year, month):
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({
                    "day": "", "is_today": False, "is_past": False,
                    "is_selected": False, "birthdays": [],
                })
                continue
            day_birthdays = [
                {"name": c.full_name, "uuid": str(c.uuid)}
                for c in birthday_contacts
                if c.birthday.month == month and c.birthday.day == day
            ]
            day_date = date(year, month, day)
            week_data.append({
                "day": day,
                "is_today": day_date == today,
                "is_past": day_date < today,
                "is_selected": bool(selected_day and selected_day == day_date),
                "birthdays": day_birthdays,
                "date": day_date,
            })
        calendar_weeks.append(week_data)

    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    context = {
        "calendar_month_name": month_names[month - 1],
        "calendar_year": year,
        "calendar_month_num": month,
        "calendar_weeks": calendar_weeks,
        "weekday_names": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "prev_month_link": f"?month={prev_year:04d}-{prev_month:02d}",
        "next_month_link": f"?month={next_year:04d}-{next_month:02d}",
        "current_month_link": f"?month={year:04d}-{month:02d}",
        "is_current_month": is_current_month,
        "today": today,
        "selected_day": selected_day,
        "selected_day_birthdays": selected_day_birthdays,
        "month_birthdays": month_birthdays,
        "all_upcoming": [e for e in enriched if 0 <= e["days_away"] <= 365],
    }
    return render(request, "birthdays.html", context)


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
    from .forms import LanguagePreferenceForm
    language_form = LanguagePreferenceForm(initial={"language": user.language or "en"})
    return render(
        request,
        "settings.html",
        {
            "form": form,
            "branding_form": branding_form,
            "language_form": language_form,
            "workspace": workspace,
        },
    )


# ---------------------------------------------------------------------------
# Company views
# ---------------------------------------------------------------------------
@login_required
def companies(request):
    sort = _get_sort_param(request, "-created_at", ["name", "-name", "-created_at", "created_at"])
    qs = (
        Company.objects.filter(
            workspace=request.user.workspace, is_deleted=False
        )
        .order_by(sort)
    )
    return render(request, "companies/list.html", {"companies": qs, "current_sort": sort})


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
    sort = _get_sort_param(request, "-created_at", ["first_name", "-first_name", "-created_at", "created_at"])
    qs = (
        Contact.objects.filter(
            workspace=request.user.workspace, is_deleted=False
        )
        .order_by(sort)
    )
    return render(request, "contacts/list.html", {"contacts": qs, "current_sort": sort})


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
@require_http_methods(["GET", "POST"])
def import_export(request):
    workspace = request.user.workspace
    contacts = Contact.objects.filter(workspace=workspace, is_deleted=False)
    import_result = None

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "export":
            fmt = (request.POST.get("export_format") or "csv").lower()
            exporter = ie.EXPORTERS.get(fmt)
            if exporter is None:
                messages.error(request, "Unsupported export format.")
                return redirect("import-export")
            return exporter(contacts.order_by("first_name", "last_name"))

        if action == "import":
            fmt = (request.POST.get("file_format") or "").lower()
            upload = request.FILES.get("file")
            if not upload:
                messages.error(request, "Please choose a file to import.")
                return redirect("import-export")
            importer = ie.IMPORTERS.get(fmt)
            if importer is None:
                messages.error(
                    request,
                    f"Unsupported import format: {fmt!s}. "
                    "Use CSV, XLSX, VCF or JSON.",
                )
                return redirect("import-export")

            try:
                import_result = importer(
                    upload,
                    workspace=workspace,
                    user=request.user,
                )
            except Exception as exc:  # noqa: BLE001
                messages.error(request, f"Import failed: {exc}")
                return redirect("import-export")

            if import_result.get("created"):
                messages.success(
                    request,
                    f"Imported {import_result['created']} contact"
                    f"{'s' if import_result['created'] != 1 else ''} "
                    f"from {import_result.get('source', 'file')}.",
                )
            elif import_result.get("errors"):
                messages.warning(
                    request,
                    f"Import completed with issues. See the report below.",
                )

    contacts_count = contacts.count()
    fields_meta = [
        {
            "canonical": canonical,
            "label": label,
            "description": ie.FIELD_DESCRIPTIONS.get(canonical, ""),
        }
        for canonical, label in ie.CONTACT_FIELDS
    ]
    return render(
        request,
        "import_export.html",
        {
            "contacts_count": contacts_count,
            "import_result": import_result,
            "fields_meta": fields_meta,
        },
    )


@login_required
def import_export_template(request, fmt):
    fmt = (fmt or "").lower()
    generator = ie.TEMPLATES.get(fmt)
    if generator is None:
        messages.error(request, f"No template available for format: {fmt!s}.")
        return redirect("import-export")
    return generator()


def buttons(request):
    return render(request, "buttons.html")
