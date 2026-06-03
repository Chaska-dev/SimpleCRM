"""Signals: keep a "system" Company in sync with each Workspace."""

from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Company, Workspace


@receiver(post_save, sender=Workspace)
def sync_workspace_company(sender, instance: Workspace, created, **kwargs):
    """Create or update the system Company that represents this workspace.

    The system company mirrors the workspace's primary name and logo so that
    the workspace appears in the Companies list as its own entry, but it
    cannot be deleted (see ``is_workspace`` flag and the delete views).
    """
    company_qs = Company.objects.filter(workspace=instance, is_workspace=True)
    company = company_qs.first()

    if company is None:
        Company.objects.create(
            workspace=instance,
            is_workspace=True,
            name=instance.name,
        )
        return

    # Keep branding in sync; don't touch other fields the user may have set
    # (phone, email, address, etc.) on the system company.
    updates: list[str] = []
    if company.name != instance.name:
        company.name = instance.name
        updates.append("name")
    if company.logo != instance.logo:
        company.logo = instance.logo
        updates.append("logo")
    if updates:
        company.save(update_fields=updates)
