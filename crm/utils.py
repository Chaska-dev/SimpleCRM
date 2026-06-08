"""Reusable helpers shared across CRM views."""

from __future__ import annotations

import io
from typing import Any, Iterable, Mapping

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from PIL import Image, UnidentifiedImageError


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_PIXELS = 50_000_000

# Pillow: protect against decompression bombs (also set in settings).
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


# ---------------------------------------------------------------------------
# Image upload helpers
# ---------------------------------------------------------------------------
def is_valid_image(uploaded_file) -> bool:
    """Reject anything that is not a real image (checks content_type + magic)."""
    if not uploaded_file:
        return False
    if (uploaded_file.content_type or "").lower() not in ALLOWED_IMAGE_MIME:
        return False
    name = (uploaded_file.name or "").lower()
    if not any(name.endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS):
        return False
    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        return False
    finally:
        try:
            uploaded_file.seek(0)
        except Exception:  # noqa: BLE001
            pass
    return True


def crop_and_save_image(
    uploaded_file,
    *,
    prefix: str = "image",
    target_size: tuple[int, int] = (400, 400),
    crop_x: str | int = "0",
    crop_y: str | int = "0",
    crop_size: str | int = "50",
) -> InMemoryUploadedFile | None:
    """Resize, center-crop and re-encode an uploaded image as PNG.

    Returns ``None`` when the file is not a valid image.
    """
    if not is_valid_image(uploaded_file):
        return None

    with Image.open(uploaded_file) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        tw, th = target_size
        ratio = img.width / img.height
        if ratio > 1:
            new_h = th
            new_w = int(new_h * ratio)
        else:
            new_w = tw
            new_h = int(new_w / ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        try:
            ox_pct = float(crop_x)
            oy_pct = float(crop_y)
            size_pct = float(crop_size)
            ox_px = int((ox_pct / 100) * new_w)
            oy_px = int((oy_pct / 100) * new_h)
            crop_px = int((size_pct / 100) * new_w)
            crop_px = max(50, min(crop_px, min(new_w, new_h)))
        except (ValueError, ZeroDivisionError):
            ox_px = oy_px = 0
            crop_px = tw

        left = max(0, ox_px)
        top = max(0, oy_px)
        right = min(new_w, left + crop_px)
        bottom = min(new_h, top + crop_px)
        if right - left < crop_px:
            left = max(0, right - crop_px)
        if bottom - top < crop_px:
            top = max(0, bottom - crop_px)
        img = img.crop((left, top, right, bottom))
        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=90)
        buffer.seek(0)
        return InMemoryUploadedFile(
            buffer,
            "file",
            f"{prefix}.png",
            "image/png",
            buffer.getbuffer().nbytes,
            None,
        )


# ---------------------------------------------------------------------------
# Locale / location helpers
# ---------------------------------------------------------------------------
def _model_has_field(model: type[models.Model], field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:  # noqa: BLE001
        return False


def get_or_create_locale(
    model: type[models.Model],
    name: str,
    *,
    parent: models.Model | None = None,
    parent_field: str = "country",
    name_field: str = "name",
    code_length: int = 3,
    extra_defaults: Mapping[str, Any] | None = None,
):
    """Generic ``get_or_create`` for Country/State/City (i18n) and Company.

    Country/State/City expose ``name_es`` and ``name_en``; Company only has
    ``name``. The helper auto-detects which fields the target model exposes.
    """
    if not name or not str(name).strip():
        return None
    clean = str(name).strip()
    lookup = {parent_field: parent} if parent is not None else {}

    has_i18n = _model_has_field(model, "name_es") and _model_has_field(
        model, "name_en"
    )

    if has_i18n:
        for f in ("name_es", "name_en"):
            obj = model.objects.filter(**{f"{f}__iexact": clean}, **lookup).first()
            if obj:
                return obj
        defaults: dict[str, Any] = {"name_es": clean, "name_en": clean}
        if code_length and _model_has_field(model, "code"):
            defaults["code"] = clean[:code_length].upper()
    else:
        obj = model.objects.filter(
            **{f"{name_field}__iexact": clean}, **lookup
        ).first()
        if obj:
            return obj
        defaults = {name_field: clean}

    if parent is not None:
        defaults[parent_field] = parent
    if extra_defaults:
        defaults.update(extra_defaults)
    return model.objects.create(**defaults)


def search_location(
    model: type[models.Model],
    *,
    query: str = "",
    lang: str = "es",
    parent: models.Model | None = None,
    parent_field: str = "country",
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Search Country/State/City by name and return ``[{id, name}, ...]``."""
    name_field = "name_en" if lang == "en" else "name_es"
    qs = model.objects.all()
    if parent is not None:
        qs = qs.filter(**{parent_field: parent})
    if query:
        qs = qs.filter(**{f"{name_field}__icontains": query})
    rows = qs.values("id", name_field)[:limit]
    return [{"id": r["id"], "name": r[name_field]} for r in rows]


def parse_uuids(values: Iterable[str]) -> list[str]:
    """Filter an iterable to a list of non-empty strings."""
    return [v for v in values if v]
