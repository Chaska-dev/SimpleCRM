"""Template context processors for the CRM app."""


def i18n_flags(request):
    """Expose available languages and the active code to every template.

    Templates use this to render the language switcher in the settings
    page and to highlight the currently active language.
    """
    from django.conf import settings

    active = getattr(request, "LANGUAGE_CODE", None) or settings.LANGUAGE_CODE
    return {
        "AVAILABLE_LANGUAGES": settings.LANGUAGES,
        "ACTIVE_LANGUAGE_CODE": active,
    }
