from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Workspace, User, Tag, Company, Contact,
    ContactCompanyRelationship, Note, Activity, AuditLog,
    CustomField, CustomFieldValue, CompanyAccess
)


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'company_name', 'is_active', 'created_at']
    search_fields = ['name', 'company_name']
    list_filter = ['is_active']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'workspace', 'role', 'is_active']
    list_filter = ['role', 'workspace', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Workspace', {'fields': ('workspace', 'role', 'avatar', 'phone')}),
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'workspace', 'color', 'created_at']
    list_filter = ['workspace']
    search_fields = ['name']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'workspace', 'industry', 'created_at']
    list_filter = ['workspace', 'industry']
    search_fields = ['name', 'website', 'email']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'workspace', 'job_title', 'created_at']
    list_filter = ['workspace', 'gender']
    search_fields = ['first_name', 'last_name', 'email', 'phone']


@admin.register(ContactCompanyRelationship)
class ContactCompanyRelationshipAdmin(admin.ModelAdmin):
    list_display = ['contact', 'company', 'position', 'department', 'is_current']
    list_filter = ['is_current', 'department']


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'contact', 'company', 'created_at']
    list_filter = ['workspace']
    search_fields = ['title', 'content']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'activity_type', 'contact', 'user', 'is_completed', 'due_date']
    list_filter = ['activity_type', 'is_completed', 'workspace']
    search_fields = ['title', 'description']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'created_at']
    list_filter = ['action', 'model_name']
    search_fields = ['user__username', 'action']


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'field_type', 'model', 'required', 'order']
    list_filter = ['field_type', 'model']


@admin.register(CustomFieldValue)
class CustomFieldValueAdmin(admin.ModelAdmin):
    list_display = ['custom_field', 'object_id', 'created_at']
    list_filter = ['custom_field']


@admin.register(CompanyAccess)
class CompanyAccessAdmin(admin.ModelAdmin):
    list_display = ['company', 'user', 'role', 'created_at']
    list_filter = ['role']
    search_fields = ['company__name', 'user__username']