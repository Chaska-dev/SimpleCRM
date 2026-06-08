from django.urls import path

from . import views

urlpatterns = [
    # Auth
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("set-language/", views.set_language, name="set_language"),

    # Dashboard / settings
    path("dashboard/", views.dashboard, name="dashboard"),
    path("birthdays/", views.birthdays, name="birthdays"),
    path("settings/", views.settings, name="settings"),
    path("import-export/", views.import_export, name="import-export"),
    path("import-export/template/<str:fmt>/", views.import_export_template, name="import-export-template"),
    path("buttons/", views.buttons, name="buttons"),

    # Contacts
    path("contacts/", views.contacts, name="contacts"),
    path(
        "contacts/create/",
        views.contact_create,
        name="contact-create",
    ),
    path(
        "contacts/<uuid:contact_uuid>/edit/",
        views.contact_edit,
        name="contact-edit",
    ),
    path(
        "contacts/<uuid:contact_uuid>/delete/",
        views.contact_delete,
        name="contact-delete",
    ),
    path(
        "contacts/bulk-delete/",
        views.contact_bulk_delete,
        name="contact-bulk-delete",
    ),

    # Companies
    path("companies/", views.companies, name="companies"),
    path(
        "companies/create/",
        views.company_create,
        name="company-create",
    ),
    path(
        "companies/<uuid:company_uuid>/edit/",
        views.company_edit,
        name="company-edit",
    ),
    path(
        "companies/<uuid:company_uuid>/delete/",
        views.company_delete,
        name="company-delete",
    ),
    path(
        "companies/bulk-delete/",
        views.company_bulk_delete,
        name="company-bulk-delete",
    ),

    # JSON search endpoints (versioned, throttled below)
    path(
        "api/v1/companies/search/",
        views.company_search,
        name="company-search",
    ),
    path(
        "api/v1/locations/countries/",
        views.country_search,
        name="country-search",
    ),
    path(
        "api/v1/locations/states/",
        views.state_search,
        name="state-search",
    ),
    path(
        "api/v1/locations/cities/",
        views.city_search,
        name="city-search",
    ),

    # Backwards-compatible aliases (deprecated, will be removed)
    path(
        "api/companies/search/",
        views.company_search,
        name="company-search-legacy",
    ),
    path(
        "api/locations/countries/",
        views.country_search,
        name="country-search-legacy",
    ),
    path(
        "api/locations/states/",
        views.state_search,
        name="state-search-legacy",
    ),
    path(
        "api/locations/cities/",
        views.city_search,
        name="city-search-legacy",
    ),
]
